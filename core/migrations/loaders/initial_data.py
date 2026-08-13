import json
import os
from pathlib import Path

from django.conf import settings

from .escola_xlsx import iter_escola_records


TOTAL_ESTADOS = 27
TOTAL_CIDADES = 5571
WORKBOOK_RELATIVE_PATH = (
    Path("staticfiles")
    / "base de dados das Escolas"
    / "br_bd_diretorios_brasil_escola.xlsx"
)


def popular_estados_cidades(apps, schema_editor):
    Estado = apps.get_model("core", "Estado")
    Cidade = apps.get_model("core", "Cidade")
    data_directory = Path(__file__).resolve().parent.parent.parent / "data"

    with (data_directory / "estados_cidades_ibge.json").open(encoding="utf-8") as arquivo:
        estados = json.load(arquivo)["estados"]
    with (data_directory / "codigos_municipios_ibge.json").open(encoding="utf-8") as arquivo:
        referencias_ibge = json.load(arquivo)

    total_cidades = sum(len(estado["cidades"]) for estado in estados)
    if len(estados) != TOTAL_ESTADOS or total_cidades != TOTAL_CIDADES:
        raise RuntimeError(
            "A base de estados e cidades do IBGE está incompleta: "
            f"esperados {TOTAL_ESTADOS} estados e {TOTAL_CIDADES} cidades; "
            f"encontrados {len(estados)} estados e {total_cidades} cidades."
        )
    if len(referencias_ibge) != TOTAL_CIDADES:
        raise RuntimeError(
            "A referência de códigos do IBGE está incompleta: "
            f"esperados {TOTAL_CIDADES}, encontrados {len(referencias_ibge)}."
        )

    codigos = {
        (item["sigla"], item["nome_cidade"]): item["codigo_ibge"]
        for item in referencias_ibge
    }
    cidades = []
    cidades_sem_codigo = []
    for dados_estado in estados:
        estado = Estado.objects.create(
            sigla=dados_estado["sigla"],
            nome_estado=dados_estado["nome_estado"],
        )
        for nome_cidade in dados_estado["cidades"]:
            codigo_ibge = codigos.get((estado.sigla, nome_cidade))
            if codigo_ibge is None:
                cidades_sem_codigo.append(f"{nome_cidade}/{estado.sigla}")
                continue
            cidades.append(
                Cidade(
                    estado=estado,
                    nome_cidade=nome_cidade,
                    codigo_ibge=codigo_ibge,
                )
            )

    if cidades_sem_codigo:
        raise RuntimeError(
            "Cidades sem código IBGE: " + ", ".join(cidades_sem_codigo[:10])
        )
    Cidade.objects.bulk_create(cidades, batch_size=1000)


def _workbook_path():
    configured = os.environ.get("ESCOLAS_XLSX_PATH")
    candidates = [Path(configured)] if configured else []
    candidates.extend(
        [
            Path(settings.BASE_DIR) / WORKBOOK_RELATIVE_PATH,
            Path(settings.BASE_DIR)
            / "static"
            / "base de dados das Escolas"
            / "br_bd_diretorios_brasil_escola.xlsx",
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    locations = "\n - ".join(str(path) for path in candidates)
    raise RuntimeError(
        "A base de escolas não foi encontrada. Informe ESCOLAS_XLSX_PATH "
        "ou coloque o arquivo em:\n - " + locations
    )


def importar_escolas(apps, schema_editor):
    database_name = str(schema_editor.connection.settings_dict.get("NAME", ""))
    if "memorydb_" in database_name or Path(database_name).name.startswith("test_"):
        return

    Escola = apps.get_model("core", "Escola")
    workbook_path = _workbook_path()
    batch = []
    source_rows = 0

    print(f"Importando escolas de {workbook_path}...", flush=True)
    for record in iter_escola_records(workbook_path):
        batch.append(Escola(**record))
        source_rows += 1
        if len(batch) >= 1000:
            Escola.objects.bulk_create(batch, batch_size=500, ignore_conflicts=True)
            batch.clear()
            if source_rows % 25000 == 0:
                print(f"  {source_rows:,} linhas processadas", flush=True)
    if batch:
        Escola.objects.bulk_create(batch, batch_size=500, ignore_conflicts=True)

    imported_rows = Escola.objects.count()
    if imported_rows != source_rows:
        raise RuntimeError(
            f"Importação incompleta: {source_rows} linhas no Excel e "
            f"{imported_rows} escolas no banco."
        )
    print(f"Importação concluída: {imported_rows:,} escolas cadastradas.", flush=True)

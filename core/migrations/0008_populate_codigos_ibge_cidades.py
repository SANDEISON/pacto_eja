import json
from pathlib import Path

from django.db import migrations


TOTAL_CIDADES_IBGE = 5571


def popular_codigos_ibge(apps, schema_editor):
    Cidade = apps.get_model("core", "Cidade")
    arquivo_dados = Path(__file__).resolve().parent.parent / "data" / "codigos_municipios_ibge.json"

    with arquivo_dados.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    if len(dados) != TOTAL_CIDADES_IBGE:
        raise RuntimeError(
            f"A referência de códigos do IBGE está incompleta: esperados {TOTAL_CIDADES_IBGE}, encontrados {len(dados)}."
        )

    codigos = {
        (item["sigla"], item["nome_cidade"]): item["codigo_ibge"]
        for item in dados
    }
    cidades = list(Cidade.objects.select_related("estado"))
    cidades_atualizadas = []
    cidades_sem_codigo = []
    for cidade in cidades:
        codigo = codigos.get((cidade.estado.sigla, cidade.nome_cidade))
        if codigo is None:
            cidades_sem_codigo.append(f"{cidade.nome_cidade}/{cidade.estado.sigla}")
            continue
        cidade.codigo_ibge = codigo
        cidades_atualizadas.append(cidade)

    if cidades_sem_codigo:
        raise RuntimeError("Cidades sem código IBGE: " + ", ".join(cidades_sem_codigo[:10]))

    Cidade.objects.bulk_update(cidades_atualizadas, ("codigo_ibge",), batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_cidade_codigo_ibge_cadastroeducador"),
    ]

    operations = [
        migrations.RunPython(popular_codigos_ibge, migrations.RunPython.noop),
    ]

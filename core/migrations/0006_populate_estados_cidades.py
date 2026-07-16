import json
from pathlib import Path

from django.db import migrations


TOTAL_ESTADOS = 27
TOTAL_CIDADES = 5571


def popular_estados_cidades(apps, schema_editor):
    Estado = apps.get_model("core", "Estado")
    Cidade = apps.get_model("core", "Cidade")
    arquivo_dados = Path(__file__).resolve().parent.parent / "data" / "estados_cidades_ibge.json"

    with arquivo_dados.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    estados = dados["estados"]
    total_cidades = sum(len(estado["cidades"]) for estado in estados)
    if len(estados) != TOTAL_ESTADOS or total_cidades != TOTAL_CIDADES:
        raise RuntimeError(
            "A base do IBGE está incompleta: "
            f"esperados {TOTAL_ESTADOS} estados e {TOTAL_CIDADES} cidades; "
            f"encontrados {len(estados)} estados e {total_cidades} cidades."
        )

    cidades_para_criar = []
    for dados_estado in estados:
        estado, _ = Estado.objects.update_or_create(
            sigla=dados_estado["sigla"],
            defaults={"nome_estado": dados_estado["nome_estado"]},
        )
        cidades_para_criar.extend(
            Cidade(estado=estado, nome_cidade=nome_cidade)
            for nome_cidade in dados_estado["cidades"]
        )

    Cidade.objects.bulk_create(
        cidades_para_criar,
        batch_size=1000,
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_estado_cidade"),
    ]

    operations = [
        migrations.RunPython(popular_estados_cidades, migrations.RunPython.noop),
    ]

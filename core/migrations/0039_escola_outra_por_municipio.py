from django.db import migrations


def criar_escolas_outra(apps, schema_editor):
    Cidade = apps.get_model("core", "Cidade")
    Escola = apps.get_model("core", "Escola")
    banco = schema_editor.connection.alias
    # IDs sintéticos fora da faixa dos códigos de escolas importados do INEP.
    cidades = Cidade.objects.using(banco).filter(codigo_ibge__gt=0).select_related("estado")
    escolas = [
        Escola(
            id_escola=9_000_000_000 + cidade.codigo_ibge,
            nome="Outra",
            id_municipio=cidade.codigo_ibge,
            sigla_uf=cidade.estado.sigla,
        )
        for cidade in cidades.iterator()
    ]
    Escola.objects.using(banco).bulk_create(escolas, batch_size=500, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("core", "0038_atividade_link")]

    # Preserva os registros em caso de reversão: podem ter vínculos de educadores.
    operations = [migrations.RunPython(criar_escolas_outra, migrations.RunPython.noop)]

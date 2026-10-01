from django.db import migrations


MAPS_LINK = "https://maps.app.goo.gl/nnyHA1yVHSxauqMU7"
LOCAL_COMPLETO = (
    "Littoral Hotel — Av. Cabo Branco, 2172 - Cabo Branco, "
    "João Pessoa - PB, 58045-010 " + MAPS_LINK
)


def incluir_endereco(apps, schema_editor):
    Atividade = apps.get_model("core", "Atividade")
    Atividade.objects.using(schema_editor.connection.alias).filter(local=MAPS_LINK).update(
        local=LOCAL_COMPLETO
    )


def remover_endereco(apps, schema_editor):
    Atividade = apps.get_model("core", "Atividade")
    Atividade.objects.using(schema_editor.connection.alias).filter(local=LOCAL_COMPLETO).update(
        local=MAPS_LINK
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0039_escola_outra_por_municipio")]

    operations = [migrations.RunPython(incluir_endereco, remover_endereco)]

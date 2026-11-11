from django.db import migrations


def liberar_operacoes_do_analista(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    analista = Group.objects.using(alias).get(name="Analista")
    permissoes = Permission.objects.using(alias).filter(
        content_type__app_label="core",
        codename__in=(
            "change_educador",
            "view_inscricao",
            "view_credenciamento",
            "add_credenciamento",
            "view_frequencia",
            "add_frequencia",
        ),
    )
    analista.permissions.add(*permissoes)


class Migration(migrations.Migration):
    dependencies = [("core", "0063_acesso_consulta_analista")]
    operations = [
        migrations.RunPython(liberar_operacoes_do_analista, migrations.RunPython.noop),
    ]

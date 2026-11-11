from django.db import migrations


def ajustar_permissoes_do_analista(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    analista = Group.objects.using(alias).get(name="Analista")
    permissoes = Permission.objects.using(alias).filter(content_type__app_label="core")
    analista.permissions.add(*permissoes.filter(codename__in=("view_educador", "view_atividade")))
    analista.permissions.remove(*permissoes.filter(codename__in=("delete_educador", "change_atividade")))


class Migration(migrations.Migration):
    dependencies = [("core", "0062_perfis_de_acesso")]
    operations = [
        migrations.RunPython(ajustar_permissoes_do_analista, migrations.RunPython.noop),
    ]

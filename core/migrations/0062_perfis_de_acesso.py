from django.apps import apps as installed_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations
from django.db.models import Q


def criar_perfis(apps, schema_editor):
    alias = schema_editor.connection.alias
    for app_label in ("auth", "core"):
        create_permissions(installed_apps.get_app_config(app_label), apps=apps, using=alias, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("auth", "User")
    permissions = Permission.objects.using(alias)
    coordenacao = (
        "add_atividade", "view_atividade", "change_atividade",
        "add_sala", "view_sala",
        "add_programacaosala", "view_programacaosala", "change_programacaosala",
        "delete_programacaosala", "view_inscricao", "change_inscricao",
        "view_credenciamento", "add_credenciamento", "view_frequencia", "add_frequencia",
        "view_relatorios",
    )
    perfis = {
        "Administrador": permissions.filter(
            Q(content_type__app_label="core")
            | Q(content_type__app_label="auth", content_type__model__in=("user", "group"))
        ),
        "Coordenador": permissions.filter(content_type__app_label="core", codename__in=coordenacao),
        "Analista": permissions.filter(content_type__app_label="core", codename="view_relatorios"),
        "Educador": permissions.none(),
    }
    for nome, permissoes in perfis.items():
        grupo, criado = Group.objects.using(alias).get_or_create(name=nome)
        if criado:
            grupo.permissions.set(permissoes)

    educador = Group.objects.using(alias).get(name="Educador")
    vinculos = User.groups.through.objects.using(alias)
    usuarios = User.objects.using(alias).filter(is_staff=False, is_superuser=False, groups=None)
    if not educador.permissions.exists():
        vinculos.bulk_create(
            (vinculos.model(user_id=usuario_id, group_id=educador.pk)
             for usuario_id in usuarios.values_list("pk", flat=True)),
            ignore_conflicts=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0061_programacaosala_horarios"),
    ]
    operations = [
        migrations.AlterModelOptions(
            name="atividade",
            options={
                "verbose_name": "atividade",
                "verbose_name_plural": "atividades",
                "ordering": ("data_inicio", "titulo"),
                "permissions": (("view_relatorios", "Pode consultar relatórios"),),
            },
        ),
        migrations.RunPython(criar_perfis, migrations.RunPython.noop),
    ]


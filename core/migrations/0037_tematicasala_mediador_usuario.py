from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def vincular_mediadores_existentes(apps, schema_editor):
    TematicaSala = apps.get_model("core", "TematicaSala")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split(".", 1))

    for tematica in TematicaSala.objects.exclude(mediador_legado=""):
        nome = tematica.mediador_legado.strip()
        candidatos = list(
            User.objects.filter(username__iexact=nome)
            | User.objects.filter(email__iexact=nome)
        )
        if not candidatos:
            candidatos = [
                usuario
                for usuario in User.objects.all()
                if f"{usuario.first_name} {usuario.last_name}".strip().casefold()
                == nome.casefold()
            ]
        candidatos_unicos = {usuario.pk: usuario for usuario in candidatos}
        if len(candidatos_unicos) == 1:
            tematica.mediador_id = next(iter(candidatos_unicos))
            tematica.save(update_fields=("mediador",))


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0036_educador_representante_estado_undime_consed"),
    ]

    operations = [
        migrations.RenameField(
            model_name="tematicasala",
            old_name="mediador",
            new_name="mediador_legado",
        ),
        migrations.AddField(
            model_name="tematicasala",
            name="mediador",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tematicas_salas_mediadas",
                to=settings.AUTH_USER_MODEL,
                verbose_name="mediador",
            ),
        ),
        migrations.RunPython(
            vincular_mediadores_existentes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="tematicasala",
            name="mediador_legado",
        ),
    ]

from django.db import migrations, models


def copiar_curso_existente(apps, schema_editor):
    Educador = apps.get_model("core", "Educador")
    for educador in Educador.objects.exclude(curso_certificado_anterior=None).iterator():
        educador.cursos_certificados.add(educador.curso_certificado_anterior_id)


def restaurar_um_curso(apps, schema_editor):
    Educador = apps.get_model("core", "Educador")
    for educador in Educador.objects.iterator():
        curso = educador.cursos_certificados.order_by("pk").first()
        if curso is not None:
            educador.curso_certificado_anterior_id = curso.pk
            educador.save(update_fields=("curso_certificado_anterior",))


class Migration(migrations.Migration):
    dependencies = [("core", "0010_curso_certificado")]

    operations = [
        migrations.RenameField(
            model_name="educador",
            old_name="curso_certificado",
            new_name="curso_certificado_anterior",
        ),
        migrations.AddField(
            model_name="educador",
            name="cursos_certificados",
            field=models.ManyToManyField(
                blank=True,
                related_name="educadores_solicitantes",
                to="core.cursocertificado",
                verbose_name="cursos solicitados para certificado",
            ),
        ),
        migrations.RunPython(copiar_curso_existente, restaurar_um_curso),
        migrations.RemoveField(
            model_name="educador",
            name="curso_certificado_anterior",
        ),
    ]

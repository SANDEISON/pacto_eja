from django.db import migrations, models
import django.db.models.deletion


CURSOS = (
    "Alfabetização de Jovens, Adultos e Idosos - 80 horas",
    "Formação em Serviço para Formadores Regionais - 360 horas",
)


def cadastrar_cursos(apps, schema_editor):
    CursoCertificado = apps.get_model("core", "CursoCertificado")
    for nome in CURSOS:
        CursoCertificado.objects.get_or_create(nome=nome)


def remover_cursos(apps, schema_editor):
    CursoCertificado = apps.get_model("core", "CursoCertificado")
    CursoCertificado.objects.filter(nome__in=CURSOS).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0009_opcoes_como_models")]

    operations = [
        migrations.CreateModel(
            name="CursoCertificado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150, unique=True, verbose_name="curso")),
            ],
            options={
                "verbose_name": "curso para certificado",
                "verbose_name_plural": "cursos para certificados",
                "db_table": "Curso_Certificado",
                "ordering": ("id",),
            },
        ),
        migrations.AddField(
            model_name="educador",
            name="curso_certificado",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="educadores_solicitantes",
                to="core.cursocertificado",
                verbose_name="curso solicitado para certificado",
            ),
        ),
        migrations.RunPython(cadastrar_cursos, remover_cursos),
    ]

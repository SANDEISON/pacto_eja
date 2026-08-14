import django.db.models.deletion
from django.db import migrations, models


CORES_RACAS_INICIAIS = ("Preto", "Pardo", "Branco", "Indígena", "Amarelo")


def popular_cores_racas(apps, schema_editor):
    CorRaca = apps.get_model("core", "CorRaca")
    CorRaca.objects.bulk_create(
        [CorRaca(nome=nome) for nome in CORES_RACAS_INICIAIS],
        ignore_conflicts=True,
    )


def remover_cores_racas(apps, schema_editor):
    CorRaca = apps.get_model("core", "CorRaca")
    Educador = apps.get_model("core", "Educador")
    Educador.objects.filter(cor_raca__nome__in=CORES_RACAS_INICIAIS).update(cor_raca=None)
    CorRaca.objects.filter(nome__in=CORES_RACAS_INICIAIS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CorRaca",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nome", models.CharField(max_length=30, unique=True, verbose_name="nome")),
            ],
            options={
                "verbose_name": "cor/raça",
                "verbose_name_plural": "cores/raças",
                "db_table": "core_cor_raca",
                "ordering": ("nome",),
            },
        ),
        migrations.AddField(
            model_name="educador",
            name="cor_raca",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="educadores",
                to="core.corraca",
                verbose_name="cor/raça",
            ),
        ),
        migrations.RunPython(popular_cores_racas, remover_cores_racas),
    ]

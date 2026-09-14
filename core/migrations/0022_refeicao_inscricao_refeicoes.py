import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0021_programacao_sala_modalidade_link")]

    operations = [
        migrations.CreateModel(
            name="Refeicao",
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
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("cafe_manha", "Café da manhã"),
                            ("almoco", "Almoço"),
                            ("lanche", "Lanche"),
                            ("jantar", "Jantar"),
                            ("ceia", "Ceia"),
                        ],
                        max_length=12,
                        verbose_name="tipo de refeição",
                    ),
                ),
                ("data", models.DateField(verbose_name="data")),
                ("horario", models.TimeField(verbose_name="horário")),
                (
                    "atividade",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refeicoes",
                        to="core.atividade",
                        verbose_name="atividade",
                    ),
                ),
            ],
            options={
                "verbose_name": "refeição",
                "verbose_name_plural": "refeições",
                "db_table": "core_refeicao",
                "ordering": ("data", "horario", "tipo"),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("atividade", "tipo", "data", "horario"),
                        name="refeicao_unica_por_atividade_data_horario",
                        violation_error_message=(
                            "Esta refeição já está cadastrada nesta data e horário."
                        ),
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="inscricao",
            name="refeicoes",
            field=models.ManyToManyField(
                blank=True,
                related_name="inscricoes",
                to="core.refeicao",
                verbose_name="refeições selecionadas",
            ),
        ),
    ]

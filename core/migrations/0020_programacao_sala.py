import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def migrar_programacoes_existentes(apps, schema_editor):
    """Move configurações completas da antiga Sala sem inventar dados ausentes."""
    Sala = apps.get_model("core", "Sala")
    ProgramacaoSala = apps.get_model("core", "ProgramacaoSala")

    campos_programacao = (
        "data",
        "turno",
        "modalidade",
        "tematica_sala_id",
        "descricao",
        "quantidade_max_participantes",
    )
    campos_obrigatorios = (
        "data",
        "turno",
        "modalidade",
        "tematica_sala_id",
        "quantidade_max_participantes",
    )

    for sala in Sala.objects.all():
        if not any(getattr(sala, campo) for campo in campos_programacao):
            continue
        ausentes = [campo for campo in campos_obrigatorios if not getattr(sala, campo)]
        if ausentes:
            raise RuntimeError(
                f"A sala {sala.pk} possui programação incompleta nos campos: "
                f"{', '.join(ausentes)}. Complete os dados antes de aplicar a migration."
            )
        ProgramacaoSala.objects.create(
            sala_id=sala.pk,
            data=sala.data,
            turno=sala.turno,
            modalidade=sala.modalidade,
            tematica_id=sala.tematica_sala_id,
            descricao=sala.descricao,
            quantidade_max_participantes=sala.quantidade_max_participantes,
        )


class Migration(migrations.Migration):
    dependencies = [("core", "0019_sala_tematicasala_initial_data")]

    operations = [
        migrations.AlterModelOptions(
            name="sala",
            options={
                "ordering": ("nome",),
                "verbose_name": "sala",
                "verbose_name_plural": "salas",
            },
        ),
        migrations.CreateModel(
            name="ProgramacaoSala",
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
                ("data", models.DateField(verbose_name="data")),
                (
                    "turno",
                    models.CharField(
                        choices=[
                            ("manha", "Manhã"),
                            ("tarde", "Tarde"),
                            ("noite", "Noite"),
                        ],
                        max_length=5,
                        verbose_name="turno",
                    ),
                ),
                (
                    "modalidade",
                    models.CharField(
                        choices=[("online", "On-line"), ("presencial", "Presencial")],
                        max_length=10,
                        verbose_name="modalidade",
                    ),
                ),
                ("descricao", models.TextField(blank=True, verbose_name="descrição")),
                (
                    "quantidade_max_participantes",
                    models.PositiveIntegerField(
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="quantidade máxima de participantes",
                    ),
                ),
                (
                    "sala",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="programacoes",
                        to="core.sala",
                        verbose_name="sala",
                    ),
                ),
                (
                    "tematica",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="programacoes",
                        to="core.tematicasala",
                        verbose_name="temática da sala",
                    ),
                ),
            ],
            options={
                "verbose_name": "programação da sala",
                "verbose_name_plural": "programações das salas",
                "db_table": "core_programacao_sala",
                "ordering": ("data", "turno", "sala__nome"),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("sala", "data", "turno"),
                        name="programacao_unica_por_sala_data_turno",
                        violation_error_message=(
                            "Esta sala já possui uma atividade cadastrada nesta data e turno."
                        ),
                    )
                ],
            },
        ),
        migrations.RunPython(
            migrar_programacoes_existentes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(model_name="sala", name="data"),
        migrations.RemoveField(model_name="sala", name="descricao"),
        migrations.RemoveField(model_name="sala", name="modalidade"),
        migrations.RemoveField(
            model_name="sala", name="quantidade_max_participantes"
        ),
        migrations.RemoveField(model_name="sala", name="tematica_sala"),
        migrations.RemoveField(model_name="sala", name="turno"),
    ]

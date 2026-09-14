import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


TEMATICAS_INICIAIS = (
    "EJA como direito",
    "Sujeitos da EJA",
    "Ambiente alfabetizador",
    "Planejamento na EJA",
    "Matemática",
    "Língua Portuguesa",
    "Tecnologias",
    "Projetos didáticos",
)

SALAS_INICIAIS = (
    "Beatriz Nascimento",
    "Maria Firmina dos Reis",
    "Lélia Gonzalez",
    "Carolina Maria de Jesus",
)


def criar_dados_iniciais(apps, schema_editor):
    TematicaSala = apps.get_model("core", "TematicaSala")
    Sala = apps.get_model("core", "Sala")

    for nome in TEMATICAS_INICIAIS:
        TematicaSala.objects.get_or_create(nome=nome)
    for nome in SALAS_INICIAIS:
        Sala.objects.get_or_create(nome=nome)


def remover_dados_iniciais(apps, schema_editor):
    TematicaSala = apps.get_model("core", "TematicaSala")
    Sala = apps.get_model("core", "Sala")

    Sala.objects.filter(nome__in=SALAS_INICIAIS).delete()
    TematicaSala.objects.filter(nome__in=TEMATICAS_INICIAIS, salas__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0018_atividade_modelo_submissao_and_more")]

    operations = [
        migrations.CreateModel(
            name="TematicaSala",
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
                    "nome",
                    models.CharField(
                        max_length=150, unique=True, verbose_name="nome da temática"
                    ),
                ),
                (
                    "mediador",
                    models.CharField(blank=True, max_length=150, verbose_name="mediador"),
                ),
            ],
            options={
                "verbose_name": "temática da sala",
                "verbose_name_plural": "temáticas das salas",
                "db_table": "core_tematica_sala",
                "ordering": ("nome",),
            },
        ),
        migrations.CreateModel(
            name="Sala",
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
                    "nome",
                    models.CharField(
                        max_length=150, unique=True, verbose_name="nome da sala"
                    ),
                ),
                (
                    "turno",
                    models.CharField(
                        blank=True,
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
                    "data",
                    models.DateField(blank=True, null=True, verbose_name="data"),
                ),
                (
                    "modalidade",
                    models.CharField(
                        blank=True,
                        choices=[("online", "On-line"), ("presencial", "Presencial")],
                        max_length=10,
                        verbose_name="modalidade",
                    ),
                ),
                ("descricao", models.TextField(blank=True, verbose_name="descrição")),
                (
                    "quantidade_max_participantes",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="quantidade máxima de participantes",
                    ),
                ),
                (
                    "tematica_sala",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="salas",
                        to="core.tematicasala",
                        verbose_name="temática da sala",
                    ),
                ),
            ],
            options={
                "verbose_name": "sala",
                "verbose_name_plural": "salas",
                "db_table": "core_sala",
                "ordering": ("data", "turno", "nome"),
            },
        ),
        migrations.RunPython(criar_dados_iniciais, remover_dados_iniciais),
    ]

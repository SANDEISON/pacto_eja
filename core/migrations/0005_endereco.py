import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_educador_nome_social"),
    ]

    operations = [
        migrations.CreateModel(
            name="Endereco",
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
                    "cep",
                    models.CharField(
                        blank=True,
                        max_length=8,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^\\d{8}$",
                                "Informe um CEP válido com 8 números.",
                            )
                        ],
                        verbose_name="CEP",
                    ),
                ),
                ("logradouro", models.CharField(blank=True, max_length=150, verbose_name="Rua/Av.")),
                ("numero", models.CharField(blank=True, max_length=20, verbose_name="número")),
                ("complemento", models.CharField(blank=True, max_length=100, verbose_name="complemento")),
                ("bairro", models.CharField(blank=True, max_length=100, verbose_name="bairro")),
                (
                    "cidade",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enderecos_educadores",
                        to="core.cidade",
                        verbose_name="município",
                    ),
                ),
                (
                    "educador",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="endereco",
                        to="core.educador",
                        verbose_name="educador",
                    ),
                ),
            ],
            options={
                "verbose_name": "endereço",
                "verbose_name_plural": "endereços",
                "db_table": "core_endereco",
            },
        ),
    ]

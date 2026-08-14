from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_cor_raca_educador_cor_raca"),
    ]

    operations = [
        migrations.AddField(
            model_name="educadorescola",
            name="tempo_atuacao",
            field=models.CharField(
                blank=True,
                choices=[
                    ("0_3_anos", "0-3 anos"),
                    ("4_6_anos", "4-6 anos"),
                    ("mais_6_anos", "Mais de 6 anos"),
                ],
                default="",
                max_length=11,
                verbose_name="tempo de atuação",
            ),
        ),
    ]

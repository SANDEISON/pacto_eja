from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0027_cadastropendente"),
    ]

    operations = [
        migrations.AddField(
            model_name="cadastropendente",
            name="senha_hash",
            field=models.CharField(blank=True, max_length=128, verbose_name="hash da senha"),
        ),
        migrations.AddField(
            model_name="cadastropendente",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("cadastro_publico", "Cadastro público"),
                    ("conta", "Conta de acesso"),
                ],
                db_index=True,
                default="cadastro_publico",
                max_length=20,
                verbose_name="tipo",
            ),
        ),
    ]

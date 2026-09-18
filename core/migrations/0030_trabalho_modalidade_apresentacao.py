from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_alter_trabalho_titulo_remove_palavras_chave"),
    ]

    operations = [
        migrations.AddField(
            model_name="trabalho",
            name="modalidade_apresentacao",
            field=models.CharField(
                choices=[("online", "On-line"), ("presencial", "Presencial")],
                blank=True,
                default="",
                max_length=10,
                verbose_name="Apresentação do trabalho",
            ),
            preserve_default=False,
        ),
    ]

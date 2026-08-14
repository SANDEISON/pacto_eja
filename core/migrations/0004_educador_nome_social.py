from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_educadorescola_tempo_atuacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="educador",
            name="nome_social",
            field=models.CharField(blank=True, max_length=150, verbose_name="nome social"),
        ),
    ]

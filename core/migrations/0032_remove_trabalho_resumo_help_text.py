from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_eixo_proposta"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trabalho",
            name="resumo",
            field=models.TextField(blank=True, verbose_name="Apresentação"),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_coautor_papel_ordem"),
    ]

    operations = [
        migrations.AddField(
            model_name="educador",
            name="representante_estado_undime_consed",
            field=models.BooleanField(
                blank=True,
                null=True,
                verbose_name="Você é representante do Estado pela Undime ou pelo Consed?",
            ),
        ),
    ]

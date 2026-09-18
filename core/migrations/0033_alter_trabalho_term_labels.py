from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_remove_trabalho_resumo_help_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trabalho",
            name="aceitou_originalidade",
            field=models.BooleanField(
                default=False,
                verbose_name="Declaro a originalidade da atividade",
            ),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="aceitou_termo_relato",
            field=models.BooleanField(
                default=False,
                verbose_name=(
                    "Declaro CIÊNCIA e CONCORDÂNCIA com os 3 (três) termos acima, sobre "
                    "uso de imagem, cessão de direitos autorais e declaração de originalidade."
                ),
            ),
        ),
    ]

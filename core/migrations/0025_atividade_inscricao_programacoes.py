from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0024_inscricao_refeicoes_multiplas")]

    operations = [
        migrations.AddField(
            model_name="atividade",
            name="programacoes",
            field=models.ManyToManyField(
                blank=True,
                related_name="atividades",
                to="core.programacaosala",
                verbose_name="programações disponíveis",
            ),
        ),
        migrations.AddField(
            model_name="inscricao",
            name="programacoes",
            field=models.ManyToManyField(
                blank=True,
                related_name="inscricoes",
                to="core.programacaosala",
                verbose_name="programações selecionadas",
            ),
        ),
    ]

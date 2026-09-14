from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0020_programacao_sala")]

    operations = [
        migrations.AddField(
            model_name="programacaosala",
            name="link",
            field=models.URLField(
                blank=True,
                help_text="Disponível somente para programações na modalidade on-line.",
                max_length=500,
                verbose_name="link da sala on-line",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="programacaosala",
            name="programacao_unica_por_sala_data_turno",
        ),
        migrations.AddConstraint(
            model_name="programacaosala",
            constraint=models.UniqueConstraint(
                fields=("sala", "data", "turno", "modalidade"),
                name="programacao_unica_por_sala_data_turno_modalidade",
                violation_error_message=(
                    "Esta sala já possui uma atividade cadastrada nesta data, turno e modalidade."
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name="programacaosala",
            constraint=models.CheckConstraint(
                condition=models.Q(("modalidade", "online"), ("link", ""), _connector="OR"),
                name="link_apenas_para_programacao_online",
                violation_error_message=(
                    "O link só pode ser informado para uma programação on-line."
                ),
            ),
        ),
    ]

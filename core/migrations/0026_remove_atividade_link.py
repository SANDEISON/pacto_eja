from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0025_atividade_inscricao_programacoes")]

    operations = [
        migrations.RemoveField(
            model_name="atividade",
            name="link",
        ),
    ]

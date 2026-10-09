from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0046_responsaveis_frequencia_legados")]

    operations = [
        migrations.RemoveField(model_name="atividade", name="vagas"),
    ]

from datetime import datetime, time

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def copiar_data(apps, schema_editor, para_data_hora):
    ProgramacaoSala = apps.get_model("core", "ProgramacaoSala")
    programacoes = ProgramacaoSala.objects.using(schema_editor.connection.alias)
    fuso = timezone.get_default_timezone()
    for programacao in programacoes.order_by("pk").iterator():
        if para_data_hora:
            data_hora = datetime.combine(programacao.data, time.min)
            if settings.USE_TZ:
                data_hora = timezone.make_aware(data_hora, fuso)
            programacoes.filter(pk=programacao.pk).update(data_hora=data_hora)
        else:
            data_hora = programacao.data_hora
            if timezone.is_aware(data_hora):
                data_hora = timezone.localtime(data_hora, fuso)
            programacoes.filter(pk=programacao.pk).update(data=data_hora.date())


def preencher_data_hora(apps, schema_editor):
    copiar_data(apps, schema_editor, para_data_hora=True)


def restaurar_data(apps, schema_editor):
    copiar_data(apps, schema_editor, para_data_hora=False)


class Migration(migrations.Migration):
    dependencies = [("core", "0059_programacaosala_publica")]

    operations = [
        migrations.AlterField(
            model_name="programacaosala",
            name="data",
            field=models.DateField("data", null=True),
        ),
        migrations.AddField(
            model_name="programacaosala",
            name="data_hora",
            field=models.DateTimeField("data e hora", null=True),
        ),
        migrations.RunPython(preencher_data_hora, restaurar_data),
        migrations.RemoveField(model_name="programacaosala", name="data"),
        migrations.RenameField(
            model_name="programacaosala", old_name="data_hora", new_name="data"
        ),
        migrations.AlterField(
            model_name="programacaosala",
            name="data",
            field=models.DateTimeField("data e hora"),
        ),
    ]

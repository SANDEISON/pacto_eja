from datetime import datetime, time

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def separar_data_e_hora(apps, schema_editor):
    programacoes = apps.get_model("core", "ProgramacaoSala").objects.using(schema_editor.connection.alias)
    fuso = timezone.get_default_timezone()
    for programacao in programacoes.order_by("pk").iterator():
        data_hora = programacao.data
        if timezone.is_aware(data_hora):
            data_hora = timezone.localtime(data_hora, fuso)
        programacoes.filter(pk=programacao.pk).update(
            dia=data_hora.date(), hora_inicio=data_hora.time(),
        )


def recompor_data_e_hora(apps, schema_editor):
    programacoes = apps.get_model("core", "ProgramacaoSala").objects.using(schema_editor.connection.alias)
    fuso = timezone.get_default_timezone()
    for programacao in programacoes.order_by("pk").iterator():
        data_hora = datetime.combine(programacao.dia, programacao.hora_inicio or time.min)
        if settings.USE_TZ:
            data_hora = timezone.make_aware(data_hora, fuso)
        programacoes.filter(pk=programacao.pk).update(data=data_hora)


class Migration(migrations.Migration):
    dependencies = [("core", "0060_programacaosala_data_hora")]

    operations = [
        migrations.AlterField(
            model_name="programacaosala", name="data",
            field=models.DateTimeField("data e hora", null=True),
        ),
        migrations.AddField(
            model_name="programacaosala", name="dia",
            field=models.DateField("data", null=True),
        ),
        migrations.AddField(
            model_name="programacaosala", name="hora_inicio",
            field=models.TimeField("hora de início", null=True, blank=True),
        ),
        migrations.AddField(
            model_name="programacaosala", name="hora_fim",
            field=models.TimeField("hora de fim", null=True, blank=True),
        ),
        migrations.RunPython(separar_data_e_hora, recompor_data_e_hora),
        migrations.RemoveField(model_name="programacaosala", name="data"),
        migrations.RenameField(model_name="programacaosala", old_name="dia", new_name="data"),
        migrations.AlterField(
            model_name="programacaosala", name="data", field=models.DateField("data"),
        ),
    ]

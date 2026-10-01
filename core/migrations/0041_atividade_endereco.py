import re
from urllib.parse import quote_plus

from django.db import migrations, models


def separar_endereco_e_link(apps, schema_editor):
    Atividade = apps.get_model("core", "Atividade")
    for atividade in Atividade.objects.using(schema_editor.connection.alias).exclude(local="").iterator():
        valor = atividade.local.strip()
        link = re.search(r"https?://[^\s]+", valor, flags=re.IGNORECASE)
        if link:
            atividade.endereco = (valor[:link.start()] + valor[link.end():]).strip(" \t\r\n-–—|:;,.()")
            atividade.local = link.group(0).rstrip(".,;)")
        else:
            atividade.endereco = valor
            atividade.local = f"https://www.google.com/maps/search/?api=1&query={quote_plus(valor)}"
            if len(atividade.local) > 255:
                atividade.local = ""
        atividade.save(update_fields=("endereco", "local"))


def reunir_endereco_e_link(apps, schema_editor):
    Atividade = apps.get_model("core", "Atividade")
    for atividade in Atividade.objects.using(schema_editor.connection.alias).exclude(endereco="").iterator():
        valor = f"{atividade.endereco} {atividade.local}".strip()
        atividade.local = valor if len(valor) <= 255 else atividade.endereco
        atividade.save(update_fields=("local",))


class Migration(migrations.Migration):
    dependencies = [("core", "0040_atividade_endereco_littoral")]

    operations = [
        migrations.AddField(
            model_name="atividade",
            name="endereco",
            field=models.CharField("endereço", max_length=255, blank=True),
        ),
        migrations.AlterField(
            model_name="atividade",
            name="local",
            field=models.CharField("link Local do evento", max_length=255, blank=True),
        ),
        migrations.RunPython(separar_endereco_e_link, reunir_endereco_e_link),
    ]

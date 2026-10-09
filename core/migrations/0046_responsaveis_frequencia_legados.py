from django.db import migrations


def aproveitar_mediadores(apps, schema_editor):
    Programacao = apps.get_model("core", "ProgramacaoSala")
    for programacao in Programacao.objects.using(schema_editor.connection.alias).filter(responsavel__isnull=True).select_related("tematica"):
        if programacao.tematica.mediador_id:
            programacao.responsavel_id = programacao.tematica.mediador_id
            programacao.save(using=schema_editor.connection.alias, update_fields=["responsavel"])


class Migration(migrations.Migration):
    dependencies = [("core", "0045_programacaosala_responsavel_chamadafrequencia_and_more")]
    operations = [migrations.RunPython(aproveitar_mediadores, migrations.RunPython.noop)]

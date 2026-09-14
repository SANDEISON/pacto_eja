import django.db.models.deletion
from django.db import migrations, models


def copiar_refeicao_para_refeicoes(apps, schema_editor):
    Inscricao = apps.get_model("core", "Inscricao")
    for inscricao in Inscricao.objects.exclude(refeicao_id=None).iterator():
        inscricao.refeicoes.add(inscricao.refeicao_id)


def preservar_primeira_refeicao(apps, schema_editor):
    Inscricao = apps.get_model("core", "Inscricao")
    for inscricao in Inscricao.objects.all().iterator():
        refeicao = inscricao.refeicoes.order_by("data", "horario", "pk").first()
        if refeicao:
            inscricao.refeicao_id = refeicao.pk
            inscricao.save(update_fields=("refeicao",))


class Migration(migrations.Migration):
    dependencies = [("core", "0023_inscricao_refeicao_unica")]

    operations = [
        migrations.AddField(
            model_name="inscricao",
            name="refeicoes",
            field=models.ManyToManyField(
                blank=True,
                related_name="inscricoes_multiplas",
                to="core.refeicao",
                verbose_name="refeições selecionadas",
            ),
        ),
        migrations.RunPython(
            copiar_refeicao_para_refeicoes,
            reverse_code=preservar_primeira_refeicao,
        ),
        migrations.RemoveField(model_name="inscricao", name="refeicao"),
        migrations.AlterField(
            model_name="inscricao",
            name="refeicoes",
            field=models.ManyToManyField(
                blank=True,
                related_name="inscricoes",
                to="core.refeicao",
                verbose_name="refeições selecionadas",
            ),
        ),
    ]

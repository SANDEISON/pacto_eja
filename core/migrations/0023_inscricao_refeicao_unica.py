import django.db.models.deletion
from django.db import migrations, models


def preservar_primeira_refeicao(apps, schema_editor):
    Inscricao = apps.get_model("core", "Inscricao")
    for inscricao in Inscricao.objects.all().iterator():
        refeicao = inscricao.refeicoes.order_by("data", "horario", "pk").first()
        if refeicao and inscricao.modalidade == "presencial":
            inscricao.refeicao_id = refeicao.pk
            inscricao.save(update_fields=("refeicao",))


class Migration(migrations.Migration):
    dependencies = [("core", "0022_refeicao_inscricao_refeicoes")]

    operations = [
        migrations.AddField(
            model_name="inscricao",
            name="refeicao",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inscricoes",
                to="core.refeicao",
                verbose_name="refeição selecionada",
            ),
        ),
        migrations.RunPython(
            preservar_primeira_refeicao,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(model_name="inscricao", name="refeicoes"),
    ]

from django.db import migrations, models


def preencher_modalidades(apps, schema_editor):
    Atividade = apps.get_model("core", "Atividade")
    Inscricao = apps.get_model("core", "Inscricao")

    for atividade in Atividade.objects.all().iterator():
        if atividade.local and atividade.link:
            modalidade = "ambas"
        elif atividade.link:
            modalidade = "online"
        else:
            modalidade = "presencial"
        Atividade.objects.filter(pk=atividade.pk).update(modalidade=modalidade)

    for inscricao in Inscricao.objects.select_related("atividade").all().iterator():
        modalidade = "online" if inscricao.atividade.modalidade == "online" else "presencial"
        Inscricao.objects.filter(pk=inscricao.pk).update(modalidade=modalidade)


class Migration(migrations.Migration):
    dependencies = [("core", "0015_avaliacao_workflow")]

    operations = [
        migrations.AddField(
            model_name="atividade",
            name="modalidade",
            field=models.CharField(
                choices=[
                    ("online", "On-line"),
                    ("presencial", "Presencial"),
                    ("ambas", "On-line e presencial"),
                ],
                default="presencial",
                max_length=10,
                verbose_name="modalidade",
            ),
        ),
        migrations.AddField(
            model_name="inscricao",
            name="modalidade",
            field=models.CharField(
                choices=[("online", "On-line"), ("presencial", "Presencial")],
                default="presencial",
                max_length=10,
                verbose_name="modalidade",
            ),
        ),
        migrations.RunPython(preencher_modalidades, migrations.RunPython.noop),
    ]

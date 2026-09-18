from django.db import migrations, models


def organizar_autorias_existentes(apps, schema_editor):
    Coautor = apps.get_model("core", "Coautor")
    Trabalho = apps.get_model("core", "Trabalho")

    for trabalho in Trabalho.objects.select_related("inscricao__usuario").iterator():
        usuario = trabalho.inscricao.usuario
        autoria_principal = Coautor.objects.filter(
            trabalho=trabalho, usuario_id=usuario.pk
        ).first()
        if autoria_principal is None:
            nome = f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username
            autoria_principal = Coautor.objects.create(
                trabalho=trabalho,
                usuario_id=usuario.pk,
                nome=nome,
                email=usuario.email,
                papel="autor",
                ordem=1,
            )
        else:
            autoria_principal.papel = "autor"
            autoria_principal.ordem = 1
            autoria_principal.save(update_fields=("papel", "ordem"))

        demais = Coautor.objects.filter(trabalho=trabalho).exclude(pk=autoria_principal.pk)
        for ordem, participante in enumerate(demais.order_by("nome", "pk"), start=2):
            participante.papel = "coautor"
            participante.ordem = ordem
            participante.save(update_fields=("papel", "ordem"))


class Migration(migrations.Migration):

    # The data migration writes rows with foreign keys to this table. PostgreSQL
    # defers the related constraint-trigger events until the transaction commits,
    # so the following ALTER TABLE operations cannot run in the same transaction.
    atomic = False

    dependencies = [
        ("core", "0034_trabalho_detalhamento_obrigatorio"),
    ]

    operations = [
        migrations.AddField(
            model_name="coautor",
            name="papel",
            field=models.CharField(
                choices=[("autor", "Autor"), ("coautor", "Coautor")],
                default="coautor",
                max_length=8,
                verbose_name="tipo de autoria",
            ),
        ),
        migrations.AddField(
            model_name="coautor",
            name="ordem",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="ordem de autoria"),
        ),
        migrations.RunPython(organizar_autorias_existentes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="coautor",
            name="ordem",
            field=models.PositiveSmallIntegerField(verbose_name="ordem de autoria"),
        ),
        migrations.AlterModelOptions(
            name="coautor",
            options={
                "ordering": ("ordem", "nome"),
                "verbose_name": "autor ou coautor",
                "verbose_name_plural": "autores e coautores",
            },
        ),
        migrations.AddConstraint(
            model_name="coautor",
            constraint=models.UniqueConstraint(
                fields=("trabalho", "usuario"), name="unique_usuario_por_trabalho"
            ),
        ),
        migrations.AddConstraint(
            model_name="coautor",
            constraint=models.UniqueConstraint(
                fields=("trabalho", "ordem"), name="unique_ordem_autoria_por_trabalho"
            ),
        ),
    ]

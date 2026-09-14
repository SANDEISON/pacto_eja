from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_atividade_inscricao_modalidade"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RascunhoInscricao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dados", models.JSONField(default=dict, verbose_name="dados do formulário")),
                ("etapa", models.CharField(choices=[("pessoal", "Dados pessoais"), ("modalidade", "Modalidade"), ("decisao", "Decisão sobre trabalho"), ("trabalho", "Trabalho")], default="pessoal", max_length=12, verbose_name="etapa atual")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("atividade", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rascunhos_inscricao", to="core.atividade", verbose_name="atividade")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rascunhos_inscricao", to=settings.AUTH_USER_MODEL, verbose_name="usuário")),
            ],
            options={
                "verbose_name": "rascunho de inscrição",
                "verbose_name_plural": "rascunhos de inscrição",
                "db_table": "core_rascunho_inscricao",
            },
        ),
        migrations.AddConstraint(
            model_name="rascunhoinscricao",
            constraint=models.UniqueConstraint(fields=("atividade", "usuario"), name="unique_rascunho_usuario_atividade"),
        ),
    ]

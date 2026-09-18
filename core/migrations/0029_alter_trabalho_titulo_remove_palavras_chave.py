from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_cadastropendente_senha_hash_cadastropendente_tipo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="atividade",
            name="modelo_submissao",
            field=models.CharField(
                choices=[
                    ("academico", "Trabalho acadêmico"),
                    ("relato", "Relato de experiência"),
                ],
                default="academico",
                help_text=(
                    "O trabalho acadêmico solicita eixo e apresentação. O relato de "
                    "experiência solicita a caracterização e a proposta detalhada."
                ),
                max_length=12,
                verbose_name="modelo para cadastro do trabalho",
            ),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="resumo",
            field=models.TextField(
                blank=True,
                help_text="(justificativa dos conteúdo(s) abordado(s) - 1100 caracteres)",
                verbose_name="Apresentação",
            ),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="titulo",
            field=models.CharField(max_length=200, verbose_name="Título da proposta/prática"),
        ),
        migrations.RemoveField(
            model_name="trabalho",
            name="palavras_chave",
        ),
    ]

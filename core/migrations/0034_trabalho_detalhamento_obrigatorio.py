import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_alter_trabalho_term_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="trabalho",
            name="caracterizacao_publico",
            field=models.TextField(
                blank=True,
                default="",
                max_length=500,
                verbose_name="Caracterização do Público",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="trabalho",
            name="duracao",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="Duração"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="apresentacao",
            field=models.TextField(blank=True, max_length=1100, verbose_name="Apresentação"),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="carga_horaria",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="Carga horária (em horas)",
            ),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="consideracoes",
            field=models.TextField(
                blank=True,
                max_length=2000,
                verbose_name="Considerações e avaliação do processo",
            ),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="desenvolvimento_metodologico",
            field=models.TextField(
                blank=True,
                max_length=6000,
                verbose_name="Desenvolvimento metodológico da ação de ensino",
            ),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="objetivo_geral",
            field=models.TextField(blank=True, max_length=300, verbose_name="Objetivo Geral"),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="objetivos_especificos",
            field=models.TextField(blank=True, max_length=500, verbose_name="Objetivos Específicos"),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="periodo_fim",
            field=models.DateField(blank=True, null=True, verbose_name="Data de término (dia/mês/ano)"),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="periodo_inicio",
            field=models.DateField(blank=True, null=True, verbose_name="Data de início (dia/mês/ano)"),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="referencias",
            field=models.TextField(blank=True, max_length=1000, verbose_name="Referências"),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="resumo",
            field=models.TextField(blank=True, max_length=1100, verbose_name="Apresentação"),
        ),
        migrations.AlterField(
            model_name="trabalho",
            name="turnos",
            field=models.JSONField(blank=True, default=list, verbose_name="Turno"),
        ),
    ]

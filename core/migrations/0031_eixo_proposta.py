import django.db.models.deletion
from django.db import migrations, models


EIXOS_INICIAIS = (
    (
        "Eixo 1: Planejamento com o Projeto Didático",
        "Experiências que promovam organização de projetos didáticos relacionados a "
        "contextualização local, considerando temas de problematização, reflexão crítica "
        "como conteúdo de estudo com as pessoas jovens, adultas e idosas.",
    ),
    (
        "Eixo 2: Apropriação do Sistema da Escrita Alfabética",
        "Experiências de alfabetização no desenvolvimento de atividades específicas da "
        "aprendizagem da língua escrita, considerando aulas contextualizadas e articuladas "
        "com temáticas sociais.",
    ),
    (
        "Eixo 3: Aprendendo com a Matemática",
        "Experiências de alfabetização no desenvolvimento de atividades específicas da "
        "aprendizagem da matemática, considerando aulas contextualizadas e articuladas "
        "com temáticas sociais.",
    ),
    (
        "Eixo 4: Conectado com as Tecnologias",
        "Experiências de alfabetização no desenvolvimento de atividades específicas na "
        "aprendizagem relacionadas as tecnologias, considerando aulas contextualizadas "
        "e articuladas com temáticas sociais.",
    ),
)


def criar_eixos_e_preservar_trabalhos(apps, schema_editor):
    EixoProposta = apps.get_model("core", "EixoProposta")
    Trabalho = apps.get_model("core", "Trabalho")

    for nome, descricao in EIXOS_INICIAIS:
        EixoProposta.objects.update_or_create(
            nome=nome,
            defaults={"descricao": descricao, "link_acesso": ""},
        )

    for trabalho in Trabalho.objects.exclude(eixo_tematico="").iterator():
        eixo, _ = EixoProposta.objects.get_or_create(
            nome=trabalho.eixo_tematico,
            defaults={
                "descricao": "Eixo preservado de um trabalho cadastrado anteriormente.",
                "link_acesso": "",
            },
        )
        trabalho.eixo_proposta_id = eixo.pk
        trabalho.save(update_fields=("eixo_proposta",))


def restaurar_eixo_textual(apps, schema_editor):
    Trabalho = apps.get_model("core", "Trabalho")
    for trabalho in Trabalho.objects.select_related("eixo_proposta").iterator():
        trabalho.eixo_tematico = (
            trabalho.eixo_proposta.nome if trabalho.eixo_proposta_id else ""
        )
        trabalho.save(update_fields=("eixo_tematico",))


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_trabalho_modalidade_apresentacao"),
    ]

    operations = [
        migrations.CreateModel(
            name="EixoProposta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=200, unique=True, verbose_name="nome")),
                ("descricao", models.TextField(verbose_name="descrição")),
                ("link_acesso", models.URLField(blank=True, max_length=500, verbose_name="link de acesso")),
            ],
            options={
                "verbose_name": "eixo da proposta",
                "verbose_name_plural": "eixos da proposta",
                "db_table": "core_eixo_proposta",
                "ordering": ("nome",),
            },
        ),
        migrations.AddField(
            model_name="trabalho",
            name="eixo_proposta",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="trabalhos",
                to="core.eixoproposta",
                verbose_name="Eixo da proposta",
            ),
        ),
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
                    "O trabalho acadêmico solicita modalidade, eixo da proposta e "
                    "apresentação. O relato de experiência solicita a caracterização e "
                    "a proposta detalhada."
                ),
                max_length=12,
                verbose_name="modelo para cadastro do trabalho",
            ),
        ),
        migrations.RunPython(criar_eixos_e_preservar_trabalhos, restaurar_eixo_textual),
        migrations.RemoveField(
            model_name="trabalho",
            name="eixo_tematico",
        ),
    ]

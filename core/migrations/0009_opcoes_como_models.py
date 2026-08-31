import django.db.models.deletion
from django.db import migrations, models


DADOS_INICIAIS = {
    "Nivel": (
        ("ensino_fundamental", "Ensino Fundamental"),
        ("ensino_medio", "Ensino Médio"),
        ("magisterio", "Magistério/Curso Normal"),
        ("curso_tecnico", "Curso Técnico"),
        ("tecnologo", "Tecnólogo"),
        ("graduacao_licenciatura", "Graduação — Licenciatura"),
        ("graduacao_bacharelado", "Graduação — Bacharelado"),
        ("especializacao", "Especialização"),
        ("mestrado", "Mestrado"),
        ("doutorado", "Doutorado"),
        ("pos_doutorado", "Pós-doutorado"),
    ),
    "Situacao": (
        ("cursando", "Cursando"),
        ("concluido", "Concluído"),
        ("trancado", "Trancado"),
        ("interrompido", "Interrompido"),
    ),
    "Modalidade": (
        ("presencial", "Presencial"),
        ("semipresencial", "Semipresencial"),
        ("ead", "Educação a distância"),
    ),
    "FuncaoCaracterizacaoTurma": (
        ("alfabetizacao_eja", "Alfabetização EJA"),
        ("anos_iniciais_eja", "Anos Iniciais EJA"),
        ("anos_finais_eja", "Anos Finais EJA"),
        ("nao_atuo_eja", "Não atuo no EJA"),
        ("ensino_medio", "Ensino Médio"),
        ("educacao_especial", "Educação Especial"),
        ("educacao_profissional", "Educação Profissional"),
    ),
    "EducadorGenero": (
        ("feminino", "Feminino"),
        ("masculino", "Masculino"),
        ("nao_binario", "Não binário"),
        ("outro", "Outro"),
        ("nao_informar", "Prefiro não informar"),
    ),
    "EducadorEstadoCivil": (
        ("solteiro", "Solteiro(a)"),
        ("casado", "Casado(a)"),
        ("uniao_estavel", "União estável"),
        ("separado", "Separado(a)"),
        ("divorciado", "Divorciado(a)"),
        ("viuvo", "Viúvo(a)"),
        ("outro", "Outro"),
    ),
    "Funcao": (
        ("formador_pacto_anos_iniciais", "Formador(a) do Pacto | Anos Iniciais"),
        ("formador_pacto_anos_finais", "Formador(a) do Pacto | Anos Finais"),
        ("formador_pacto_ensino_medio", "Formador(a) do Pacto | Ensino Médio"),
        ("professor_pacto_anos_iniciais", "Professor(a) do Pacto | Anos Iniciais"),
        ("professor_pacto_anos_finais", "Professor(a) do Pacto | Anos Finais"),
        ("professor_pacto_ensino_medio", "Professor(a) do Pacto | Ensino Médio"),
        ("coordenador_pacto_undime", "Coordenador(a) do Pacto - Undime"),
        ("coordenador_pacto_consed", "Coordenador(a) do Pacto - Consed"),
        ("outro_profissional_educacao_pacto", "Outro(a) profissional da Educação ligado(a) ao Pacto"),
        ("profissional_educacao_nao_pacto", "Profissional da Educação NÃO ligado(a) ao Pacto"),
        ("estudante_eja_anos_iniciais", "Estudante da EJA | Anos Iniciais"),
        ("estudante_eja_anos_finais", "Estudante da EJA | Anos Finais"),
        ("estudante_eja_ensino_medio", "Estudante da EJA | Ensino Médio"),
        ("estudante_graduacao", "Estudante de graduação"),
        ("estudante_pos_graduacao", "Estudante de pós-graduação"),
        ("educador_popular_pba", "Educador(a) Popular (PBA)"),
        ("professor_alfabetizador", "Professor (a) Alfabetizador (a)"),
        ("publico_geral", "Público em geral"),
        ("convidado_estrangeiro", "Convidado(a) estrangeiro(a)"),
        ("outro", "Outro"),
    ),
}


def popular_opcoes(apps, schema_editor):
    for model_name, opcoes in DADOS_INICIAIS.items():
        model = apps.get_model("core", model_name)
        model.objects.bulk_create(
            [model(codigo=codigo, nome=nome) for codigo, nome in opcoes]
        )


def remover_opcoes(apps, schema_editor):
    for model_name in DADOS_INICIAIS:
        apps.get_model("core", model_name).objects.all().delete()


def campos_opcao(nome_singular, nome_plural, tabela):
    return {
        "fields": [
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("codigo", models.SlugField(max_length=50, unique=True, verbose_name="código")),
            ("nome", models.CharField(max_length=100, unique=True, verbose_name="nome")),
        ],
        "options": {
            "db_table": tabela,
            "ordering": ("id",),
            "verbose_name": nome_singular,
            "verbose_name_plural": nome_plural,
        },
    }


class Migration(migrations.Migration):
    dependencies = [("core", "0008_formacao")]

    operations = [
        migrations.CreateModel(name="Nivel", **campos_opcao("nível de formação", "níveis de formação", "core_nivel")),
        migrations.CreateModel(name="Situacao", **campos_opcao("situação da formação", "situações das formações", "core_situacao")),
        migrations.CreateModel(name="Modalidade", **campos_opcao("modalidade da formação", "modalidades das formações", "core_modalidade")),
        migrations.CreateModel(name="FuncaoCaracterizacaoTurma", **campos_opcao("função e caracterização da turma", "funções e caracterizações das turmas", "core_funcao_caracterizacao_turma")),
        migrations.CreateModel(name="EducadorGenero", **campos_opcao("gênero do educador", "gêneros dos educadores", "core_educador_genero")),
        migrations.CreateModel(name="EducadorEstadoCivil", **campos_opcao("estado civil do educador", "estados civis dos educadores", "core_educador_estado_civil")),
        migrations.CreateModel(name="Funcao", **campos_opcao("função", "funções", "core_funcao")),
        migrations.RunPython(popular_opcoes, remover_opcoes),
        migrations.RemoveField(model_name="formacao", name="nivel"),
        migrations.RemoveField(model_name="formacao", name="situacao"),
        migrations.RemoveField(model_name="formacao", name="modalidade"),
        migrations.RemoveField(model_name="educador", name="genero"),
        migrations.RemoveField(model_name="educador", name="estado_civil"),
        migrations.RemoveField(model_name="educadorescola", name="funcao"),
        migrations.RemoveField(model_name="educadorescola", name="funcao_caracterizacao_turmas"),
        migrations.AddField(model_name="formacao", name="nivel", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="formacoes", to="core.nivel", verbose_name="nível")),
        migrations.AddField(model_name="formacao", name="situacao", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="formacoes", to="core.situacao", verbose_name="situação")),
        migrations.AddField(model_name="formacao", name="modalidade", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="formacoes", to="core.modalidade", verbose_name="modalidade")),
        migrations.AddField(model_name="educador", name="genero", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="educadores", to="core.educadorgenero", verbose_name="gênero")),
        migrations.AddField(model_name="educador", name="estado_civil", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="educadores", to="core.educadorestadocivil", verbose_name="estado civil")),
        migrations.AddField(model_name="educadorescola", name="funcao", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="vinculos_educador_escola", to="core.funcao", verbose_name="função")),
        migrations.AddField(model_name="educadorescola", name="funcao_caracterizacao_turmas", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vinculos_educador_escola", to="core.funcaocaracterizacaoturma", verbose_name="função e caracterização das turmas da EJA")),
    ]

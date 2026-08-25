from django.db import models


class Formacao(models.Model):
    class Nivel(models.TextChoices):
        ENSINO_FUNDAMENTAL = "ensino_fundamental", "Ensino Fundamental"
        ENSINO_MEDIO = "ensino_medio", "Ensino Médio"
        MAGISTERIO = "magisterio", "Magistério/Curso Normal"
        CURSO_TECNICO = "curso_tecnico", "Curso Técnico"
        TECNOLOGO = "tecnologo", "Tecnólogo"
        GRADUACAO_LICENCIATURA = "graduacao_licenciatura", "Graduação — Licenciatura"
        GRADUACAO_BACHARELADO = "graduacao_bacharelado", "Graduação — Bacharelado"
        ESPECIALIZACAO = "especializacao", "Especialização"
        MESTRADO = "mestrado", "Mestrado"
        DOUTORADO = "doutorado", "Doutorado"
        POS_DOUTORADO = "pos_doutorado", "Pós-doutorado"

    class Situacao(models.TextChoices):
        CURSANDO = "cursando", "Cursando"
        CONCLUIDO = "concluido", "Concluído"
        TRANCADO = "trancado", "Trancado"
        INTERROMPIDO = "interrompido", "Interrompido"

    class Modalidade(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        SEMIPRESENCIAL = "semipresencial", "Semipresencial"
        EAD = "ead", "Educação a distância"

    educador = models.ForeignKey(
        "Educador",
        on_delete=models.CASCADE,
        related_name="formacoes",
        verbose_name="educador",
    )
    nivel = models.CharField("nível", max_length=30, choices=Nivel.choices)
    nome_curso = models.CharField("curso", max_length=150)
    instituicao = models.CharField("instituição", max_length=150)
    situacao = models.CharField("situação", max_length=20, choices=Situacao.choices)
    modalidade = models.CharField(
        "modalidade",
        max_length=20,
        choices=Modalidade.choices,
        blank=True,
    )
    ano_inicio = models.PositiveSmallIntegerField("ano de início", null=True, blank=True)
    ano_conclusao = models.PositiveSmallIntegerField("ano de conclusão", null=True, blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        db_table = "core_formacao"
        verbose_name = "formação"
        verbose_name_plural = "formações"
        ordering = ("-ano_conclusao", "-ano_inicio", "nome_curso")

    def __str__(self):
        return f"{self.get_nivel_display()} — {self.nome_curso}"

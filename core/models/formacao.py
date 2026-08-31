from django.db import models


class Formacao(models.Model):
    educador = models.ForeignKey(
        "Educador",
        on_delete=models.CASCADE,
        related_name="formacoes",
        verbose_name="educador",
    )
    nivel = models.ForeignKey(
        "Nivel",
        on_delete=models.PROTECT,
        related_name="formacoes",
        verbose_name="nível",
    )
    nome_curso = models.CharField("curso", max_length=150)
    instituicao = models.CharField("instituição", max_length=150)
    situacao = models.ForeignKey(
        "Situacao",
        on_delete=models.PROTECT,
        related_name="formacoes",
        verbose_name="situação",
    )
    modalidade = models.ForeignKey(
        "Modalidade",
        on_delete=models.PROTECT,
        related_name="formacoes",
        verbose_name="modalidade",
        null=True,
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
        return f"{self.nivel} — {self.nome_curso}"

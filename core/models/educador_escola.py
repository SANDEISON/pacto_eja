from django.db import models

from .cidade import Cidade
from .escola import Escola


class EducadorEscola(models.Model):
    class TempoAtuacao(models.TextChoices):
        ZERO_A_TRES_ANOS = "0_3_anos", "0-3 anos"
        QUATRO_A_SEIS_ANOS = "4_6_anos", "4-6 anos"
        MAIS_DE_SEIS_ANOS = "mais_6_anos", "Mais de 6 anos"

    cidade = models.ForeignKey(
        Cidade,
        on_delete=models.PROTECT,
        related_name="vinculos_educador_escola",
        verbose_name="cidade de atuação",
    )
    escola = models.ForeignKey(
        Escola,
        on_delete=models.PROTECT,
        related_name="vinculos_educador_escola",
        verbose_name="escola",
    )
    funcao = models.ForeignKey(
        "Funcao",
        on_delete=models.PROTECT,
        related_name="vinculos_educador_escola",
        verbose_name="função",
        null=True,
        blank=True,
    )
    funcao_caracterizacao_turmas = models.ForeignKey(
        "FuncaoCaracterizacaoTurma",
        on_delete=models.PROTECT,
        related_name="vinculos_educador_escola",
        verbose_name="função e caracterização das turmas da EJA",
    )
    tempo_atuacao = models.CharField(
        "tempo de atuação",
        max_length=11,
        choices=TempoAtuacao.choices,
        blank=True,
        default="",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        db_table = "core_educadorescola"
        verbose_name = "vínculo entre educador e escola"
        verbose_name_plural = "vínculos entre educadores e escolas"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"{self.escola} — {self.funcao_caracterizacao_turmas}"

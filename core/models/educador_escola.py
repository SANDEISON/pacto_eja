from django.db import models

from .cidade import Cidade
from .escola import Escola
from .funcao_caracterizacao_turma import FuncaoCaracterizacaoTurma


class EducadorEscola(models.Model):
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
    funcao_caracterizacao_turmas = models.CharField(
        "função e caracterização das turmas da EJA",
        max_length=30,
        choices=FuncaoCaracterizacaoTurma.choices,
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        db_table = "core_educadorescola"
        verbose_name = "vínculo entre educador e escola"
        verbose_name_plural = "vínculos entre educadores e escolas"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"{self.escola} — {self.get_funcao_caracterizacao_turmas_display()}"

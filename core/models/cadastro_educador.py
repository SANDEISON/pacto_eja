from django.db import models

from .cidade import Cidade
from .escola import Escola
from .estado import Estado
from .funcao_caracterizacao_turma import FuncaoCaracterizacaoTurma
from .pessoa import Pessoa


class CadastroEducador(models.Model):
    id_pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name="cadastros_educador",
        verbose_name="pessoa",
    )
    estado = models.ForeignKey(
        Estado,
        on_delete=models.PROTECT,
        related_name="cadastros_educador",
        verbose_name="estado",
    )
    cidade = models.ForeignKey(
        Cidade,
        on_delete=models.PROTECT,
        related_name="cadastros_educador",
        verbose_name="cidade de atuação",
    )
    escola = models.ForeignKey(
        Escola,
        on_delete=models.PROTECT,
        related_name="cadastros_educador",
        verbose_name="escola",
    )
    funcao_caracterizacao_turmas = models.CharField(
        "função e caracterização das turmas da EJA",
        max_length=30,
        choices=FuncaoCaracterizacaoTurma.choices,
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "cadastro de educador"
        verbose_name_plural = "cadastros de educadores"
        ordering = ("-criado_em",)
        constraints = [
            models.UniqueConstraint(
                fields=("id_pessoa",),
                name="cadastro_educador_pessoa_uniq",
            )
        ]

    def __str__(self):
        return f"{self.id_pessoa} — {self.get_funcao_caracterizacao_turmas_display()}"

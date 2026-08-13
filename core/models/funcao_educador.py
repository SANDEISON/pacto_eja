from django.db import models

from .educador import Educador
from .educador_escola import EducadorEscola


class FuncaoEducador(models.Model):
    educador = models.ForeignKey(
        Educador,
        on_delete=models.PROTECT,
        related_name="funcoes",
        verbose_name="educador",
    )
    educador_escola = models.OneToOneField(
        EducadorEscola,
        on_delete=models.CASCADE,
        related_name="funcao_educador",
        verbose_name="atuação do educador na escola",
    )

    class Meta:
        db_table = "core_funcaoeducador"
        verbose_name = "função do educador"
        verbose_name_plural = "funções dos educadores"
        ordering = ("educador", "educador_escola")

    def __str__(self):
        return f"{self.educador} — {self.educador_escola}"

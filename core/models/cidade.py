from django.db import models

from .estado import Estado


class Cidade(models.Model):
    codigo_ibge = models.PositiveIntegerField("código IBGE", unique=True, null=True, blank=True)
    estado = models.ForeignKey(
        Estado,
        on_delete=models.PROTECT,
        related_name="cidades",
        verbose_name="estado",
    )
    nome_cidade = models.CharField("nome da cidade", max_length=150)

    class Meta:
        verbose_name = "cidade"
        verbose_name_plural = "cidades"
        ordering = ("nome_cidade",)
        constraints = [
            models.UniqueConstraint(
                fields=("estado", "nome_cidade"),
                name="cidade_estado_nome_uniq",
            )
        ]
        indexes = [
            models.Index(fields=("estado", "nome_cidade"), name="cidade_estado_nome_idx")
        ]

    def __str__(self):
        return f"{self.nome_cidade} - {self.estado.sigla}"

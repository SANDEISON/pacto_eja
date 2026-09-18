from django.db import models


class EixoProposta(models.Model):
    """Eixo cadastrado pela administração para propostas apresentadas on-line."""

    nome = models.CharField("nome", max_length=200, unique=True)
    descricao = models.TextField("descrição")
    link_acesso = models.URLField("link de acesso", max_length=500, blank=True)

    class Meta:
        db_table = "core_eixo_proposta"
        verbose_name = "eixo da proposta"
        verbose_name_plural = "eixos da proposta"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

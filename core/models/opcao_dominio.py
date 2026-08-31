from django.db import models


class OpcaoDominio(models.Model):
    """Base para opções administráveis que substituem listas fixas de choices."""

    codigo = models.SlugField("código", max_length=50, unique=True)
    nome = models.CharField("nome", max_length=100, unique=True)

    class Meta:
        abstract = True
        ordering = ("id",)

    def __str__(self):
        return self.nome

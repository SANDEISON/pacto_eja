from django.db import models


class Estado(models.Model):
    nome_estado = models.CharField("nome do estado", max_length=100, unique=True)
    sigla = models.CharField("sigla", max_length=2, unique=True)

    class Meta:
        verbose_name = "estado"
        verbose_name_plural = "estados"
        ordering = ("nome_estado",)

    def __str__(self):
        return f"{self.nome_estado} ({self.sigla})"

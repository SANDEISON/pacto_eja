from django.db import models


class CorRaca(models.Model):
    nome = models.CharField("nome", max_length=30, unique=True)

    class Meta:
        db_table = "core_cor_raca"
        verbose_name = "cor/raça"
        verbose_name_plural = "cores/raças"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

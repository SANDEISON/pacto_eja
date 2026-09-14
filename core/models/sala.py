from django.db import models


class Sala(models.Model):
    """Espaço que pode receber diferentes programações ao longo do evento."""

    nome = models.CharField("nome da sala", max_length=150, unique=True)

    class Meta:
        db_table = "core_sala"
        verbose_name = "sala"
        verbose_name_plural = "salas"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

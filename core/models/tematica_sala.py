from django.db import models


class TematicaSala(models.Model):
    """Tema que organiza uma ou mais salas do evento."""

    nome = models.CharField("nome da temática", max_length=150, unique=True)
    mediador = models.CharField("mediador", max_length=150, blank=True)

    class Meta:
        db_table = "core_tematica_sala"
        verbose_name = "temática da sala"
        verbose_name_plural = "temáticas das salas"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

from django.conf import settings
from django.db import models


class TematicaSala(models.Model):
    """Tema que organiza uma ou mais salas do evento."""

    nome = models.CharField("nome da temática", max_length=150, unique=True)
    mediador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="mediador",
        related_name="tematicas_salas_mediadas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "core_tematica_sala"
        verbose_name = "temática da sala"
        verbose_name_plural = "temáticas das salas"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

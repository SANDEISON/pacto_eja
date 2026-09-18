from django.conf import settings
from django.db import models

class Coautor(models.Model):
    """Participante cadastrado e sua posição na autoria de um trabalho."""

    class Papel(models.TextChoices):
        AUTOR = "autor", "Autor"
        COAUTOR = "coautor", "Coautor"

    trabalho = models.ForeignKey(
        "Trabalho", on_delete=models.CASCADE, related_name="coautores", verbose_name="trabalho"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coautorias",
        verbose_name="usuário cadastrado",
        null=True,
        blank=True,
    )
    nome = models.CharField("nome completo", max_length=150)
    email = models.EmailField("e-mail", blank=True)
    papel = models.CharField(
        "tipo de autoria", max_length=8, choices=Papel.choices, default=Papel.COAUTOR
    )
    ordem = models.PositiveSmallIntegerField("ordem de autoria")

    class Meta:
        db_table = "core_coautor"
        verbose_name = "autor ou coautor"
        verbose_name_plural = "autores e coautores"
        ordering = ("ordem", "nome")
        constraints = [
            models.UniqueConstraint(
                fields=("trabalho", "usuario"), name="unique_usuario_por_trabalho"
            ),
            models.UniqueConstraint(
                fields=("trabalho", "ordem"), name="unique_ordem_autoria_por_trabalho"
            ),
        ]

    def __str__(self):
        return f"{self.ordem}. {self.nome} ({self.get_papel_display()})"

    def save(self, *args, **kwargs):
        """Sincroniza a cópia de nome e e-mail com o usuário selecionado."""
        if self.usuario_id:
            self.nome = self.usuario.get_full_name() or self.usuario.get_username()
            self.email = self.usuario.email
        super().save(*args, **kwargs)

from django.conf import settings
from django.db import models

class Coautor(models.Model):
    """Participante cadastrado que compartilha a autoria de um trabalho."""
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

    class Meta:
        db_table = "core_coautor"
        verbose_name = "coautor"
        verbose_name_plural = "coautores"
        ordering = ("nome",)

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        """Sincroniza a cópia de nome e e-mail com o usuário selecionado."""
        if self.usuario_id:
            self.nome = self.usuario.get_full_name() or self.usuario.get_username()
            self.email = self.usuario.email
        super().save(*args, **kwargs)

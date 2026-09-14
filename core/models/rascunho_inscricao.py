from django.conf import settings
from django.db import models


class RascunhoInscricao(models.Model):
    """Guarda temporariamente os campos de uma inscrição ainda não finalizada."""

    class Etapa(models.TextChoices):
        PESSOAL = "pessoal", "Dados pessoais"
        MODALIDADE = "modalidade", "Modalidade"
        DECISAO = "decisao", "Decisão sobre trabalho"
        TRABALHO = "trabalho", "Trabalho"

    atividade = models.ForeignKey(
        "Atividade",
        on_delete=models.CASCADE,
        related_name="rascunhos_inscricao",
        verbose_name="atividade",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rascunhos_inscricao",
        verbose_name="usuário",
    )
    dados = models.JSONField("dados do formulário", default=dict)
    etapa = models.CharField(
        "etapa atual",
        max_length=12,
        choices=Etapa.choices,
        default=Etapa.PESSOAL,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_rascunho_inscricao"
        verbose_name = "rascunho de inscrição"
        verbose_name_plural = "rascunhos de inscrição"
        constraints = [
            models.UniqueConstraint(
                fields=("atividade", "usuario"),
                name="unique_rascunho_usuario_atividade",
            )
        ]

    def __str__(self):
        return f"Rascunho de {self.usuario} — {self.atividade}"

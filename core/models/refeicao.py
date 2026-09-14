from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Refeicao(models.Model):
    """Oferta de refeição disponibilizada durante uma atividade."""

    class Tipo(models.TextChoices):
        CAFE_DA_MANHA = "cafe_manha", "Café da manhã"
        ALMOCO = "almoco", "Almoço"
        LANCHE = "lanche", "Lanche"
        JANTAR = "jantar", "Jantar"
        CEIA = "ceia", "Ceia"

    atividade = models.ForeignKey(
        "Atividade",
        verbose_name="atividade",
        related_name="refeicoes",
        on_delete=models.CASCADE,
    )
    tipo = models.CharField("tipo de refeição", max_length=12, choices=Tipo.choices)
    data = models.DateField("data")
    horario = models.TimeField("horário")

    class Meta:
        db_table = "core_refeicao"
        verbose_name = "refeição"
        verbose_name_plural = "refeições"
        ordering = ("data", "horario", "tipo")
        constraints = [
            models.UniqueConstraint(
                fields=("atividade", "tipo", "data", "horario"),
                name="refeicao_unica_por_atividade_data_horario",
                violation_error_message=(
                    "Esta refeição já está cadastrada nesta data e horário."
                ),
            )
        ]

    def clean(self):
        """Garante que a refeição aconteça durante o período da atividade."""
        super().clean()
        if not self.atividade_id or not self.data:
            return
        inicio = timezone.localtime(self.atividade.data_inicio).date()
        fim = timezone.localtime(self.atividade.data_fim).date()
        if not inicio <= self.data <= fim:
            raise ValidationError(
                {"data": "A data da refeição deve estar dentro do período da atividade."}
            )

    def __str__(self):
        """Apresenta tipo, data e horário da refeição nos formulários."""
        return f"{self.get_tipo_display()} — {self.data:%d/%m/%Y} às {self.horario:%H:%M}"

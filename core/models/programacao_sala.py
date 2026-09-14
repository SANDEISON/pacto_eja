from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .sala import Sala
from .tematica_sala import TematicaSala


class ProgramacaoSala(models.Model):
    """Atividade atribuída a uma sala em uma data e um turno específicos."""

    class Turno(models.TextChoices):
        MANHA = "manha", "Manhã"
        TARDE = "tarde", "Tarde"
        NOITE = "noite", "Noite"

    class Modalidade(models.TextChoices):
        ONLINE = "online", "On-line"
        PRESENCIAL = "presencial", "Presencial"

    sala = models.ForeignKey(
        Sala,
        verbose_name="sala",
        related_name="programacoes",
        on_delete=models.CASCADE,
    )
    data = models.DateField("data")
    turno = models.CharField("turno", max_length=5, choices=Turno.choices)
    modalidade = models.CharField(
        "modalidade", max_length=10, choices=Modalidade.choices
    )
    link = models.URLField(
        "link da sala on-line",
        max_length=500,
        blank=True,
        help_text="Disponível somente para programações na modalidade on-line.",
    )
    tematica = models.ForeignKey(
        TematicaSala,
        verbose_name="temática da sala",
        related_name="programacoes",
        on_delete=models.PROTECT,
    )
    descricao = models.TextField("descrição", blank=True)
    quantidade_max_participantes = models.PositiveIntegerField(
        "quantidade máxima de participantes",
        validators=[MinValueValidator(1)],
    )

    class Meta:
        db_table = "core_programacao_sala"
        verbose_name = "programação da sala"
        verbose_name_plural = "programações das salas"
        ordering = ("data", "turno", "sala__nome")
        constraints = [
            models.UniqueConstraint(
                fields=("sala", "data", "turno", "modalidade"),
                name="programacao_unica_por_sala_data_turno_modalidade",
                violation_error_message=(
                    "Esta sala já possui uma atividade cadastrada nesta data, turno e modalidade."
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(modalidade="online") | models.Q(link=""),
                name="link_apenas_para_programacao_online",
                violation_error_message=(
                    "O link só pode ser informado para uma programação on-line."
                ),
            ),
        ]

    def clean(self):
        """Impede que programações presenciais armazenem link de acesso remoto."""
        super().clean()
        if self.modalidade != self.Modalidade.ONLINE and self.link:
            raise ValidationError(
                {"link": "O link só pode ser informado para uma programação on-line."}
            )

    def __str__(self):
        """Resume sala, turno, data e modalidade em seletores e relatórios."""
        return (
            f"{self.sala} — {self.get_turno_display()} de {self.data:%d/%m/%Y} "
            f"({self.get_modalidade_display()})"
        )

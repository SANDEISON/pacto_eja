from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


TAMANHO_MAXIMO_PDF = 10 * 1024 * 1024


def trabalho_upload_path(instance, filename):
    """Organiza PDFs por atividade e usuário, sem expor o nome original no caminho."""
    extension = Path(filename).suffix.lower()
    return f"trabalhos/atividade-{instance.inscricao.atividade_id}/usuario-{instance.inscricao.usuario_id}/{instance.pk or 'novo'}{extension}"


def validate_pdf_size(file):
    """Limita cada trabalho a 10 MB para proteger armazenamento e requisições."""
    if file.size > TAMANHO_MAXIMO_PDF:
        raise ValidationError("O arquivo PDF deve ter no máximo 10 MB.")


class Inscricao(models.Model):
    """Relaciona um usuário a uma atividade, permitindo somente um vínculo por par."""
    class Modalidade(models.TextChoices):
        ONLINE = "online", "On-line"
        PRESENCIAL = "presencial", "Presencial"

    atividade = models.ForeignKey(
        "Atividade", on_delete=models.PROTECT, related_name="inscricoes", verbose_name="atividade"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inscricoes_atividades", verbose_name="usuário"
    )
    modalidade = models.CharField(
        "modalidade",
        max_length=10,
        choices=Modalidade.choices,
        default=Modalidade.PRESENCIAL,
    )
    refeicoes = models.ManyToManyField(
        "Refeicao",
        verbose_name="refeições selecionadas",
        related_name="inscricoes",
        blank=True,
    )
    programacoes = models.ManyToManyField(
        "ProgramacaoSala",
        verbose_name="programações selecionadas",
        related_name="inscricoes",
        blank=True,
    )
    inscrito_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_inscricao"
        verbose_name = "inscrição"
        verbose_name_plural = "inscrições"
        ordering = ("-inscrito_em",)
        constraints = [
            models.UniqueConstraint(fields=("atividade", "usuario"), name="unique_usuario_atividade")
        ]

    def __str__(self):
        return f"{self.usuario} — {self.atividade}"

    def clean(self):
        """Impede uma modalidade incompatível com a configuração da atividade."""
        super().clean()
        if self.atividade_id and not self.atividade.aceita_modalidade(self.modalidade):
            raise ValidationError(
                {"modalidade": "Esta modalidade não está disponível para a atividade."}
            )

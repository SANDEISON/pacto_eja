from django.core.validators import FileExtensionValidator
from django.db import models

from .inscricao import trabalho_upload_path, validate_pdf_size


class Trabalho(models.Model):
    """Trabalho acadêmico em PDF submetido junto a uma inscrição."""
    inscricao = models.OneToOneField(
        "Inscricao", on_delete=models.CASCADE, related_name="trabalho", verbose_name="inscrição"
    )
    titulo = models.CharField("título do trabalho", max_length=250)
    arquivo = models.FileField(
        "arquivo em PDF",
        upload_to=trabalho_upload_path,
        validators=[FileExtensionValidator(("pdf",), "Envie um arquivo no formato PDF."), validate_pdf_size],
    )
    submetido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_trabalho"
        verbose_name = "trabalho"
        verbose_name_plural = "trabalhos"
        ordering = ("-submetido_em",)

    def __str__(self):
        return self.titulo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Credenciamento(models.Model):
    class Metodo(models.TextChoices):
        MANUAL = "manual", "Manual"
        QR = "qr", "QR Code"

    inscricao = models.OneToOneField(
        "Inscricao", on_delete=models.PROTECT, related_name="credenciamento",
    )
    registrado_em = models.DateTimeField(default=timezone.now)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    metodo = models.CharField(max_length=10, choices=Metodo.choices, default=Metodo.MANUAL)

    class Meta:
        verbose_name = "credenciamento"
        verbose_name_plural = "credenciamentos"
        ordering = ("-registrado_em",)
        default_permissions = ("add", "view")

    def clean(self):
        super().clean()
        if self.inscricao_id and self.inscricao.modalidade != "presencial":
            raise ValidationError("Somente inscrições presenciais podem ser credenciadas.")

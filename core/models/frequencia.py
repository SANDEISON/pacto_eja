from django.conf import settings
from django.db import models
from django.utils import timezone


class ChamadaFrequencia(models.Model):
    atividade = models.ForeignKey("Atividade", on_delete=models.PROTECT)
    programacao = models.ForeignKey("ProgramacaoSala", on_delete=models.PROTECT)
    aberta_em = models.DateTimeField(default=timezone.now)
    expira_em = models.DateTimeField()
    encerrada_em = models.DateTimeField(null=True, blank=True)
    codigo = models.CharField(max_length=16, blank=True)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    @property
    def aberta(self):
        return self.encerrada_em is None and self.aberta_em <= timezone.now() < self.expira_em


class Frequencia(models.Model):
    class Metodo(models.TextChoices):
        QR = "qr", "QR Code presencial"
        MANUAL = "manual", "Chamada presencial manual"
        ONLINE = "online", "Código on-line"

    inscricao = models.ForeignKey("Inscricao", on_delete=models.PROTECT, related_name="frequencias")
    programacao = models.ForeignKey("ProgramacaoSala", on_delete=models.PROTECT, related_name="frequencias")
    chamada = models.ForeignKey(ChamadaFrequencia, on_delete=models.PROTECT)
    registrada_em = models.DateTimeField(default=timezone.now)
    metodo = models.CharField(max_length=10, choices=Metodo.choices)
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "frequência"
        verbose_name_plural = "frequências"
        constraints = [models.UniqueConstraint(fields=("inscricao", "programacao"), name="frequencia_unica_inscricao_programacao")]

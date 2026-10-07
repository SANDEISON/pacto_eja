import uuid

from django.db import models
from django.utils import timezone


class EnvioCadastroEducador(models.Model):
    """Distingue envios concluídos de referências aos cadastros antigos."""

    class Operacao(models.TextChoices):
        CADASTRO = "cadastro", "Cadastro inicial"
        EDICAO = "edicao", "Edição"
        LEGADO = "legado", "Registro legado"

    id = models.UUIDField("UUID", primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.PositiveBigIntegerField(
        "ID", unique=True, editable=False,
        db_default=models.expressions.RawSQL("nextval('core_envio_cadastro_numero_seq')", ()),
    )
    educador = models.ForeignKey(
        "Educador",
        on_delete=models.CASCADE,
        related_name="envios_cadastro",
        verbose_name="educador",
    )
    operacao = models.CharField("operação", max_length=10, choices=Operacao.choices)
    concluido_em = models.DateTimeField(
        "envio concluído em", default=timezone.now, null=True, blank=True, editable=False, db_index=True,
        help_text="Preenchido somente para envios registrados pelo formulário.",
    )
    data_referencia = models.DateTimeField(
        "primeira atuação do cadastro antigo", null=True, blank=True,
        help_text="Data de criação da primeira atuação; não comprova a data nem a quantidade de envios antigos.",
    )
    total_atuacoes = models.PositiveIntegerField("total de atuações registradas")

    class Meta:
        db_table = "core_envio_cadastro_educador"
        verbose_name = "envio do cadastro de educador"
        verbose_name_plural = "envios do cadastro de educadores"
        ordering = ("-concluido_em",)
        constraints = [
            models.UniqueConstraint(
                fields=("educador",), condition=models.Q(operacao="legado"),
                name="unique_legado_cadastro_educador",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(operacao="legado", concluido_em__isnull=True, data_referencia__isnull=False)
                    | models.Q(
                        operacao__in=("cadastro", "edicao"),
                        concluido_em__isnull=False, data_referencia__isnull=True,
                    )
                ),
                name="envio_cadastro_datas_por_operacao",
            ),
        ]

    def __str__(self):
        return f"{self.educador} — {self.get_operacao_display()}"

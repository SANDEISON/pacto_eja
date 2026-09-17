import uuid

from django.db import models


class CadastroPendente(models.Model):
    """Guarda um cadastro público até que o endereço de e-mail seja confirmado."""

    class Tipo(models.TextChoices):
        CADASTRO_PUBLICO = "cadastro_publico", "Cadastro público"
        CONTA = "conta", "Conta de acesso"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(
        "tipo",
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.CADASTRO_PUBLICO,
        db_index=True,
    )
    cpf = models.CharField("CPF", max_length=11, db_index=True)
    email = models.EmailField("e-mail", db_index=True)
    dados = models.JSONField("dados do cadastro")
    senha_hash = models.CharField("hash da senha", max_length=128, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "core_cadastro_pendente"
        verbose_name = "cadastro pendente"
        verbose_name_plural = "cadastros pendentes"

    def __str__(self):
        return f"Cadastro pendente de {self.cpf}"

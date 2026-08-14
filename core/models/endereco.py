from django.core.validators import RegexValidator
from django.db import models


class Endereco(models.Model):
    educador = models.OneToOneField(
        "Educador",
        on_delete=models.CASCADE,
        related_name="endereco",
        verbose_name="educador",
    )
    cep = models.CharField(
        "CEP",
        max_length=8,
        blank=True,
        validators=(RegexValidator(r"^\d{8}$", "Informe um CEP válido com 8 números."),),
    )
    logradouro = models.CharField("Rua/Av.", max_length=150, blank=True)
    numero = models.CharField("número", max_length=20, blank=True)
    complemento = models.CharField("complemento", max_length=100, blank=True)
    bairro = models.CharField("bairro", max_length=100, blank=True)
    cidade = models.ForeignKey(
        "Cidade",
        on_delete=models.PROTECT,
        related_name="enderecos_educadores",
        verbose_name="município",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "core_endereco"
        verbose_name = "endereço"
        verbose_name_plural = "endereços"

    @property
    def uf(self):
        return self.cidade.estado.sigla if self.cidade_id else ""

    def __str__(self):
        if not self.logradouro:
            return f"Endereço de {self.educador}"
        localidade = f" — {self.cidade.nome_cidade}/{self.uf}" if self.cidade_id else ""
        return f"{self.logradouro}, {self.numero}{localidade}"

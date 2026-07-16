from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from ..validators import validate_birth_date, validate_cpf
from .pessoa_estado_civil import PessoaEstadoCivil
from .pessoa_genero import PessoaGenero


class Pessoa(models.Model):
    Genero = PessoaGenero
    EstadoCivil = PessoaEstadoCivil

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pessoa",
        verbose_name="usuário",
    )
    cpf = models.CharField("CPF", max_length=11, unique=True, null=True, blank=True, validators=[validate_cpf])
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True, validators=[validate_birth_date])
    genero = models.CharField("gênero", max_length=2, choices=PessoaGenero.choices, blank=True)
    telefone = models.CharField(
        "telefone",
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^\+?[0-9()\s.-]{8,20}$", "Informe um telefone válido.")],
    )
    estado_civil = models.CharField("estado civil", max_length=20, choices=PessoaEstadoCivil.choices, blank=True)

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        ordering = ("usuario__first_name", "usuario__username")

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.get_username()

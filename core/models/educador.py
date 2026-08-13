from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from ..validators import validate_birth_date, validate_cpf
from .educador_estado_civil import EducadorEstadoCivil
from .educador_genero import EducadorGenero


class Educador(models.Model):
    Genero = EducadorGenero
    EstadoCivil = EducadorEstadoCivil

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="educador",
        verbose_name="usuário",
    )
    nome_completo = models.CharField("nome completo", max_length=150, blank=True)
    cpf = models.CharField("CPF", max_length=11, unique=True, null=True, blank=True, validators=[validate_cpf])
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True, validators=[validate_birth_date])
    genero = models.CharField("gênero", max_length=2, choices=EducadorGenero.choices, blank=True)
    telefone = models.CharField(
        "telefone",
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^\+?[0-9()\s.-]{8,20}$", "Informe um telefone válido.")],
    )
    estado_civil = models.CharField("estado civil", max_length=20, choices=EducadorEstadoCivil.choices, blank=True)

    class Meta:
        db_table = "core_educador"
        verbose_name = "educador"
        verbose_name_plural = "educadores"
        ordering = ("nome_completo", "usuario__username")

    def __str__(self):
        return self.nome_completo or self.usuario.get_full_name() or self.usuario.get_username()

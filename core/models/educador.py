from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from ..validators import validate_birth_date, validate_cpf
class Educador(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="educador",
        verbose_name="usuário",
    )
    nome_completo = models.CharField("nome completo", max_length=150, blank=True)
    nome_social = models.CharField("nome social", max_length=150, blank=True)
    cpf = models.CharField("CPF", max_length=11, unique=True, null=True, blank=True, validators=[validate_cpf])
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True, validators=[validate_birth_date])
    genero = models.ForeignKey(
        "EducadorGenero",
        on_delete=models.PROTECT,
        related_name="educadores",
        verbose_name="gênero",
        null=True,
        blank=True,
    )
    telefone = models.CharField(
        "telefone",
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^\+?[0-9()\s.-]{8,20}$", "Informe um telefone válido.")],
    )
    estado_civil = models.ForeignKey(
        "EducadorEstadoCivil",
        on_delete=models.PROTECT,
        related_name="educadores",
        verbose_name="estado civil",
        null=True,
        blank=True,
    )
    cor_raca = models.ForeignKey(
        "CorRaca",
        on_delete=models.PROTECT,
        related_name="educadores",
        verbose_name="cor/raça",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "core_educador"
        verbose_name = "educador"
        verbose_name_plural = "educadores"
        ordering = ("nome_completo", "usuario__username")

    def __str__(self):
        return self.nome_completo or self.usuario.get_full_name() or self.usuario.get_username()

from django.db import models


class PessoaEstadoCivil(models.TextChoices):
    SOLTEIRO = "SOLTEIRO", "Solteiro(a)"
    CASADO = "CASADO", "Casado(a)"
    UNIAO_ESTAVEL = "UNIAO_ESTAVEL", "União estável"
    SEPARADO = "SEPARADO", "Separado(a)"
    DIVORCIADO = "DIVORCIADO", "Divorciado(a)"
    VIUVO = "VIUVO", "Viúvo(a)"
    OUTRO = "OUTRO", "Outro"

from django.db import models


class FuncaoCaracterizacaoTurma(models.TextChoices):
    ALFABETIZACAO_EJA = "alfabetizacao_eja", "Alfabetização EJA"
    ANOS_INICIAIS_EJA = "anos_iniciais_eja", "Anos Iniciais EJA"
    ANOS_FINAIS_EJA = "anos_finais_eja", "Anos Finais EJA"
    ENSINO_MEDIO = "ensino_medio", "Ensino Médio"
    EDUCACAO_ESPECIAL = "educacao_especial", "Educação Especial"
    EDUCACAO_PROFISSIONAL = "educacao_profissional", "Educação Profissional"

from django.db import models


class PessoaGenero(models.TextChoices):
    FEMININO = "F", "Feminino"
    MASCULINO = "M", "Masculino"
    NAO_BINARIO = "NB", "Não binário"
    OUTRO = "O", "Outro"
    NAO_INFORMAR = "NI", "Prefiro não informar"

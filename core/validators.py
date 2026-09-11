import re

from django.core.exceptions import ValidationError
from django.utils import timezone


def somente_digitos(valor):
    """Remove a formatação de documentos e telefones, preservando apenas dígitos."""
    return re.sub(r"\D", "", valor or "")


def validate_cpf(value):
    """Valida os dígitos verificadores de um CPF, com ou sem pontuação."""
    if not value:
        return
    digits = somente_digitos(value)
    if len(digits) != 11 or digits == digits[0] * 11:
        raise ValidationError("Informe um CPF válido.")
    for size in (9, 10):
        total = sum(int(digit) * weight for digit, weight in zip(digits[:size], range(size + 1, 1, -1)))
        check_digit = (total * 10 % 11) % 10
        if check_digit != int(digits[size]):
            raise ValidationError("Informe um CPF válido.")


def validate_birth_date(value):
    """Impede o cadastro de datas de nascimento futuras."""
    if value and value > timezone.localdate():
        raise ValidationError("A data de nascimento não pode estar no futuro.")

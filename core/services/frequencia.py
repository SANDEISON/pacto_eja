import secrets

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from ..models import ChamadaFrequencia, Frequencia


def token_inscricao(inscricao):
    # Assinatura estável: funciona também para inscrições anteriores à implantação.
    return signing.Signer(salt="frequencia.inscricao").sign(str(inscricao.pk))


def url_validacao(inscricao):
    return reverse("frequencia_validar", args=[token_inscricao(inscricao)])


def pode_operar(usuario, programacao):
    return usuario.is_active and (
        usuario.pk == programacao.responsavel_id
        or usuario.has_perm("core.add_frequencia")
    )


@transaction.atomic
def registrar(inscricao, chamada, usuario, metodo, codigo=None):
    chamada = ChamadaFrequencia.objects.select_for_update().select_related("programacao").get(pk=chamada.pk)
    programacao = chamada.programacao
    if not chamada.aberta:
        raise ValidationError("A chamada está encerrada ou expirou.")
    if not chamada.atividade.ativo:
        raise ValidationError("O evento está inativo.")
    if not chamada.atividade.programacoes.filter(pk=programacao.pk).exists():
        raise ValidationError("Esta programação não pertence mais ao evento.")
    if inscricao.atividade_id != chamada.atividade_id or not inscricao.programacoes.filter(pk=programacao.pk).exists():
        raise ValidationError("O participante não está inscrito nesta programação.")
    if inscricao.modalidade != programacao.modalidade:
        raise ValidationError("A modalidade da inscrição não corresponde à sala.")
    if metodo == Frequencia.Metodo.ONLINE:
        if programacao.modalidade != "online" or usuario.pk != inscricao.usuario_id:
            raise ValidationError("Confirmação on-line inválida.")
        if not codigo or not chamada.codigo or not secrets.compare_digest(chamada.codigo, codigo):
            raise ValidationError("Código de presença inválido.")
    elif metodo not in (Frequencia.Metodo.QR, Frequencia.Metodo.MANUAL) or programacao.modalidade != "presencial" or not pode_operar(usuario, programacao):
        raise ValidationError("Você não pode registrar presença nesta sala.")
    return Frequencia.objects.get_or_create(
        inscricao=inscricao, programacao=programacao,
        defaults={"chamada": chamada, "metodo": metodo, "registrada_por": usuario, "registrada_em": timezone.now()},
    )

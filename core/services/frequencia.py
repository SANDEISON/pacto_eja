import secrets
from datetime import datetime, time, timedelta

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Prefetch
from django.urls import reverse
from django.utils import timezone

from ..models import ChamadaFrequencia, Frequencia, ProgramacaoSala


def inscricoes_com_presencas(inscricoes):
    programacoes = ProgramacaoSala.objects.select_related("sala").annotate(
        _total_inscritos=Count("inscricoes", distinct=True)
    )
    inscricoes = inscricoes.select_related("atividade").prefetch_related(
        Prefetch("programacoes", queryset=programacoes),
        "frequencias__programacao__sala",
    )
    for inscricao in inscricoes:
        confirmadas = {frequencia.programacao_id for frequencia in inscricao.frequencias.all()}
        for programacao in inscricao.programacoes.all():
            programacao.presenca_confirmada = programacao.pk in confirmadas
    return inscricoes


@transaction.atomic
def registrar_direto(inscricao, programacao, usuario, metodo):
    """Registra presença sem exigir abertura prévia ou código de transmissão."""
    ProgramacaoSala.objects.select_for_update().get(pk=programacao.pk)
    chamada = ChamadaFrequencia.objects.create(
        atividade=inscricao.atividade, programacao=programacao, responsavel=usuario,
        expira_em=timezone.make_aware(datetime.combine(timezone.localdate() + timedelta(days=1), time.min)),
    )
    registro, criada = registrar(inscricao, chamada, usuario, metodo)
    if not criada:
        chamada.delete()
    return registro, criada


@transaction.atomic
def cancelar_presenca(inscricao, programacao, usuario):
    """Desfaz apenas a presença desta inscrição e programação."""
    ProgramacaoSala.objects.select_for_update().get(pk=programacao.pk)
    if not pode_operar(usuario, programacao):
        raise ValidationError("Você não pode cancelar presença nesta sala.")
    if not inscricao.atividade.ativo:
        raise ValidationError("O evento está inativo.")
    if not inscricao.atividade.programacoes.filter(pk=programacao.pk).exists():
        raise ValidationError("Esta programação não pertence mais ao evento.")
    excluidas, _ = Frequencia.objects.filter(inscricao=inscricao, programacao=programacao).delete()
    return bool(excluidas)


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
    acesso_online_publico = (
        metodo == Frequencia.Metodo.ONLINE and programacao.modalidade == "online" and programacao.publica
    )
    if inscricao.modalidade != programacao.modalidade and not acesso_online_publico:
        raise ValidationError("A modalidade da inscrição não corresponde à sala.")
    if metodo == Frequencia.Metodo.ONLINE:
        if programacao.modalidade != "online" or usuario.pk != inscricao.usuario_id:
            raise ValidationError("Confirmação on-line inválida.")
        if chamada.codigo and (not codigo or not secrets.compare_digest(chamada.codigo, codigo)):
            raise ValidationError("Código de presença inválido.")
    elif metodo == Frequencia.Metodo.QR_PROPRIO:
        # Validação de data desativada temporariamente para testes no servidor.
        # agora = timezone.now()
        if programacao.modalidade != "presencial" or usuario.pk != inscricao.usuario_id:
            raise ValidationError("Somente o próprio inscrito presencial pode confirmar sua presença.")
        # if (timezone.localdate(agora) != programacao.data
        #         or not chamada.atividade.data_inicio <= agora <= chamada.atividade.data_fim):
        #     raise ValidationError("A confirmação está disponível somente na data da programação e durante o evento.")
    elif (
        metodo not in (Frequencia.Metodo.QR, Frequencia.Metodo.MANUAL)
        or (metodo == Frequencia.Metodo.QR and programacao.modalidade != "presencial")
        or not pode_operar(usuario, programacao)
    ):
        raise ValidationError("Você não pode registrar presença nesta sala.")
    return Frequencia.objects.get_or_create(
        inscricao=inscricao, programacao=programacao,
        defaults={"chamada": chamada, "metodo": metodo, "registrada_por": usuario, "registrada_em": timezone.now()},
    )

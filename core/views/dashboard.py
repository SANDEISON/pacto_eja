from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from ..models import Atividade, ChamadaAvaliadores, RascunhoInscricao


@login_required
def dashboard(request):
    """Monta o painel com atividades abertas ou já vinculadas ao usuário."""
    horario_atual = timezone.now()
    atividades_disponiveis = (
        Atividade.objects.filter(ativo=True, data_fim__gte=horario_atual)
        .filter(
            Q(inscricoes_fim__gte=horario_atual)
            & (
                Q(inscricoes_inicio__isnull=True)
                | Q(inscricoes_inicio__lte=horario_atual)
            )
            | Q(inscricoes__usuario=request.user)
        )
        .prefetch_related("inscricoes")
        .distinct()
        .order_by("data_inicio")
    )
    inscricoes_usuario = {
        inscricao.atividade_id: inscricao
        for inscricao in request.user.inscricoes_atividades.filter(
            atividade__in=atividades_disponiveis
        ).select_related("trabalho")
    }
    rascunhos_usuario = {
        rascunho.atividade_id: rascunho
        for rascunho in RascunhoInscricao.objects.filter(
            usuario=request.user,
            atividade__in=atividades_disponiveis,
        )
    }
    # A anotação em memória simplifica o template sem introduzir regra de negócio nele.
    for atividade in atividades_disponiveis:
        atividade.inscricao_usuario = inscricoes_usuario.get(atividade.pk)
        atividade.rascunho_usuario = rascunhos_usuario.get(atividade.pk)

    chamadas_avaliadores = []
    if not request.user.is_staff:
        chamadas_avaliadores = list(
            ChamadaAvaliadores.objects.filter(ativa=True)
            .filter(
                Q(inscricoes_fim__gte=horario_atual)
                | Q(candidaturas__usuario=request.user)
            )
            .select_related("atividade")
            .distinct()
            .order_by("inscricoes_fim", "titulo")
        )
        candidaturas_usuario = {
            candidatura.chamada_id: candidatura
            for candidatura in request.user.candidaturas_avaliador.filter(
                chamada__in=chamadas_avaliadores
            )
        }
        for chamada in chamadas_avaliadores:
            chamada.candidatura_usuario = candidaturas_usuario.get(chamada.pk)
    context = {
        "atividades_disponiveis": atividades_disponiveis,
        "chamadas_avaliadores": chamadas_avaliadores,
    }
    return render(request, "index.html", context)

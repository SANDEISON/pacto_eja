from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from ..models import Atividade, ChamadaAvaliadores


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
    # A anotação em memória simplifica o template sem introduzir regra de negócio nele.
    for atividade in atividades_disponiveis:
        atividade.inscricao_usuario = inscricoes_usuario.get(atividade.pk)

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
        "year": date.today().year,
        "stats": [
            {"value": 806, "label": "Educadores em formação", "icon": "bi-people-fill", "color": "info"},
            {"value": 7, "label": "Formações em andamento", "icon": "bi-mortarboard-fill", "color": "success"},
            {"value": 11441, "label": "Participações registradas", "icon": "bi-journal-check", "color": "danger"},
        ],
        "atividades_disponiveis": atividades_disponiveis,
        "chamadas_avaliadores": chamadas_avaliadores,
    }
    return render(request, "index.html", context)

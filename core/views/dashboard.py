from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render
from django.utils import timezone

from ..models import Atividade, ProgramacaoSala, RascunhoInscricao


@login_required
def dashboard(request):
    """Monta o painel com atividades abertas, inscrições e chamadas atribuídas."""
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
            | Q(programacoes__responsavel=request.user)
        )
        .prefetch_related(
            "inscricoes",
            Prefetch("programacoes", queryset=ProgramacaoSala.objects.select_related("sala").annotate(_total_inscritos=Count("inscricoes", distinct=True))),
        )
        .distinct()
        .order_by("data_inicio")
    )
    inscricoes_usuario = {
        inscricao.atividade_id: inscricao
        for inscricao in request.user.inscricoes_atividades.filter(
            atividade__in=atividades_disponiveis
        ).select_related("trabalho").prefetch_related("programacoes__sala")
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
        atividade.programacoes_responsavel = [
            programacao for programacao in atividade.programacoes.all()
            if programacao.responsavel_id == request.user.pk
        ]
        atividade.programacoes_frequencia = []
        inscricao = atividade.inscricao_usuario
        if (
            inscricao
            and inscricao.modalidade == "online"
            and atividade.aceita_modalidade("online")
            and atividade.data_inicio <= horario_atual <= atividade.data_fim
        ):
            programacoes_atividade = {p.pk for p in atividade.programacoes.all()}
            atividade.programacoes_frequencia = [
                programacao for programacao in inscricao.programacoes.all()
                if programacao.modalidade == "online" and programacao.pk in programacoes_atividade
            ]

    context = {"atividades_disponiveis": atividades_disponiveis}
    return render(request, "index.html", context)

from urllib.parse import unquote

from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, Signer
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Atividade, Frequencia, Inscricao, ProgramacaoSala, RascunhoInscricao
from ..services.frequencia import inscricoes_com_presencas, registrar_direto


CANAL_YOUTUBE_CATEDRA = "https://www.youtube.com/@cátedraunescodeeja"


def atividades_visiveis_no_painel(usuario, horario_atual):
    return (
        Atividade.objects.filter(ativo=True, data_fim__gte=horario_atual)
        .filter(
            Q(inscricoes_fim__gte=horario_atual)
            & (
                Q(inscricoes_inicio__isnull=True)
                | Q(inscricoes_inicio__lte=horario_atual)
            )
            | Q(inscricoes__usuario=usuario)
            | Q(programacoes__responsavel=usuario)
            | Q(programacoes__publica=True, programacoes__modalidade=ProgramacaoSala.Modalidade.ONLINE)
        )
        .distinct()
    )


@login_required
def baixar_programacao_atividade(request, pk):
    atividades = Atividade.objects.all()
    if not request.user.has_perm("core.change_atividade"):
        atividades = atividades_visiveis_no_painel(request.user, timezone.now())
    atividade = get_object_or_404(atividades.exclude(arquivo_programacao=""), pk=pk)
    return _resposta_programacao(atividade)


def baixar_programacao_publica(request, token):
    """Entrega a programação a quem tem o link público assinado."""
    try:
        pk = Signer(salt=Atividade.SALT_PROGRAMACAO_PUBLICA).unsign(token)
    except BadSignature as exc:
        raise Http404 from exc
    atividade = get_object_or_404(Atividade.objects.exclude(arquivo_programacao=""), pk=pk)
    return _resposta_programacao(atividade)


def _resposta_programacao(atividade):
    try:
        arquivo = atividade.arquivo_programacao.open("rb")
    except FileNotFoundError as exc:
        raise Http404 from exc
    return FileResponse(arquivo, as_attachment=True)


def _ocultar_link_publico(link):
    return unquote(link).rstrip("/").casefold() == CANAL_YOUTUBE_CATEDRA


@login_required
def salas_online_publicas(request, pk):
    agora = timezone.now()
    atividade = get_object_or_404(
        atividades_visiveis_no_painel(request.user, agora), pk=pk
    )
    programacoes = list(
        atividade.programacoes.filter(publica=True, modalidade=ProgramacaoSala.Modalidade.ONLINE)
        .select_related("sala", "tematica").order_by("data", "hora_inicio", "sala__nome")
    )
    datas = {programacao.dia.isoformat(): programacao.dia for programacao in programacoes}
    data_selecionada = datas.get(request.GET.get("data"))
    if data_selecionada:
        programacoes = [programacao for programacao in programacoes if programacao.dia == data_selecionada]
    inscricoes = inscricoes_com_presencas(
        atividade.inscricoes.filter(usuario=request.user).filter(
            Q(modalidade=Inscricao.Modalidade.ONLINE)
            | Q(frequencias__programacao__publica=True, frequencias__programacao__modalidade=ProgramacaoSala.Modalidade.ONLINE)
        ).distinct()
    )
    presencas = {
        registro.programacao_id for inscricao in inscricoes for registro in inscricao.frequencias.all()
    }
    for programacao in programacoes:
        programacao.acesso_liberado = programacao.acesso_online_liberado(agora)
        programacao.ocultar_link_publico = _ocultar_link_publico(programacao.link)
        programacao.presenca_confirmada = programacao.pk in presencas
    return render(request, "atividades/salas_online_publicas.html", {
        "atividade": atividade,
        "programacoes": programacoes,
        "inscricoes": inscricoes,
        "datas": datas.values(),
        "data_selecionada": data_selecionada,
        "exibir_horarios_online": True,
    })


@login_required
@require_POST
@transaction.atomic
def acessar_sala_online_publica(request, pk, programacao_pk):
    agora = timezone.now()
    atividade = get_object_or_404(
        Atividade.objects.select_for_update(), pk=pk, ativo=True, data_fim__gte=agora,
    )
    programacao = get_object_or_404(
        atividade.programacoes.select_for_update(),
        pk=programacao_pk, publica=True, modalidade=ProgramacaoSala.Modalidade.ONLINE,
    )
    if not programacao.link or _ocultar_link_publico(programacao.link) or not programacao.acesso_online_liberado(agora):
        raise Http404

    inscricao, _ = Inscricao.objects.get_or_create(
        atividade=atividade,
        usuario=request.user,
        defaults={"modalidade": Inscricao.Modalidade.ONLINE},
    )
    inscricao.programacoes.add(programacao)
    registrar_direto(inscricao, programacao, request.user, Frequencia.Metodo.ONLINE)
    return redirect(programacao.link)


@login_required
def dashboard(request):
    """Monta o painel com atividades abertas, inscrições e chamadas atribuídas."""
    horario_atual = timezone.now()
    atividades_disponiveis = (
        atividades_visiveis_no_painel(request.user, horario_atual)
        .prefetch_related(
            "inscricoes",
            Prefetch("programacoes", queryset=ProgramacaoSala.objects.select_related("sala").annotate(_total_inscritos=Count("inscricoes", distinct=True))),
        )
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

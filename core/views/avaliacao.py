from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView

from ..forms import AvaliacaoForm, CandidaturaAvaliadorForm, ChamadaAvaliadoresForm
from ..models import (
    Avaliacao,
    CandidaturaAvaliador,
    ChamadaAvaliadores,
    DesignacaoAvaliacao,
    Trabalho,
)
from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


@login_required
def chamadas_avaliadores(request):
    """Apresenta chamadas publicadas e o estado da candidatura do usuário."""
    chamadas = (
        ChamadaAvaliadores.objects.filter(ativa=True)
        .filter(Q(inscricoes_fim__gte=timezone.now()) | Q(candidaturas__usuario=request.user))
        .select_related("atividade")
        .prefetch_related("candidaturas")
        .distinct()
    )
    candidaturas = {
        candidatura.chamada_id: candidatura
        for candidatura in request.user.candidaturas_avaliador.filter(chamada__in=chamadas)
    }
    for chamada in chamadas:
        chamada.candidatura_usuario = candidaturas.get(chamada.pk)
    return render(request, "avaliadores/chamadas.html", {"chamadas": chamadas})


@login_required
def candidatar_avaliador(request, pk):
    """Cria uma única candidatura enquanto a chamada estiver aberta."""
    chamada = get_object_or_404(ChamadaAvaliadores.objects.select_related("atividade"), pk=pk, ativa=True)
    existente = CandidaturaAvaliador.objects.filter(chamada=chamada, usuario=request.user).first()
    if existente:
        messages.info(request, "Você já enviou uma candidatura para esta chamada.")
        return redirect("chamadas_avaliadores")
    if not chamada.candidaturas_abertas:
        messages.error(request, "O período de candidaturas desta chamada está encerrado.")
        return redirect("chamadas_avaliadores")

    form = CandidaturaAvaliadorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        candidatura = form.save(commit=False)
        candidatura.chamada = chamada
        candidatura.usuario = request.user
        try:
            candidatura.save()
        except IntegrityError:
            messages.info(request, "Você já enviou uma candidatura para esta chamada.")
        else:
            messages.success(request, "Candidatura enviada. A coordenação fará a análise.")
        return redirect("chamadas_avaliadores")
    return render(request, "avaliadores/candidatura_form.html", {"chamada": chamada, "form": form})


@login_required
def minhas_avaliacoes(request):
    """Lista apenas os trabalhos que foram explicitamente liberados ao avaliador."""
    designacoes = (
        DesignacaoAvaliacao.objects.filter(avaliador=request.user)
        .select_related("trabalho__inscricao__atividade", "avaliacao")
        .order_by("prazo", "trabalho__titulo")
    )
    agora = timezone.now()
    for designacao in designacoes:
        chamada = designacao.trabalho.inscricao.atividade.chamada_avaliadores
        designacao.prazo_efetivo = designacao.prazo or chamada.avaliacoes_fim
        designacao.atrasada = not designacao.concluida and designacao.prazo_efetivo < agora
    return render(request, "avaliadores/minhas_avaliacoes.html", {"designacoes": designacoes})


@login_required
def preencher_avaliacao(request, pk):
    """Permite salvar rascunho e concluir o parecer de uma designação própria."""
    designacao = get_object_or_404(
        DesignacaoAvaliacao.objects.select_related("trabalho__inscricao__atividade", "avaliacao"),
        pk=pk,
        avaliador=request.user,
    )
    avaliacao, _ = Avaliacao.objects.get_or_create(designacao=designacao)
    prazo = designacao.prazo or designacao.trabalho.inscricao.atividade.chamada_avaliadores.avaliacoes_fim
    finalizada = avaliacao.status == Avaliacao.Status.CONCLUIDA
    fora_do_prazo = prazo < timezone.now()

    if request.method == "POST":
        if finalizada:
            messages.info(request, "Esta avaliação já foi concluída e está disponível somente para consulta.")
            return redirect("preencher_avaliacao", pk=designacao.pk)
        if fora_do_prazo:
            messages.error(request, "O prazo desta avaliação foi encerrado. Procure a coordenação do evento.")
            return redirect("minhas_avaliacoes")
        finalizar = request.POST.get("acao") == "concluir"
        form = AvaliacaoForm(request.POST, instance=avaliacao, finalizar=finalizar)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.status = Avaliacao.Status.CONCLUIDA if finalizar else Avaliacao.Status.RASCUNHO
            avaliacao.concluida_em = timezone.now() if finalizar else None
            avaliacao.save()
            messages.success(request, "Avaliação concluída com sucesso." if finalizar else "Rascunho salvo.")
            if finalizar:
                return redirect("minhas_avaliacoes")
            return redirect("preencher_avaliacao", pk=designacao.pk)
    else:
        form = AvaliacaoForm(instance=avaliacao)
    if finalizada or fora_do_prazo:
        for field in form.fields.values():
            field.disabled = True
    return render(
        request,
        "avaliadores/avaliacao_form.html",
        {"designacao": designacao, "avaliacao": avaliacao, "form": form, "prazo": prazo,
         "finalizada": finalizada, "fora_do_prazo": fora_do_prazo},
    )


class ChamadaAvaliadoresListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = ChamadaAvaliadores
    permission_required = "core.view_chamadaavaliadores"
    template_name = "management/chamada_list.html"
    context_object_name = "chamadas"
    search_fields = ("titulo", "atividade__titulo", "descricao", "requisitos")

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("atividade")
            .annotate(
                total_candidaturas=Count("candidaturas", distinct=True),
                total_aprovadas=Count("candidaturas", filter=Q(candidaturas__status="aprovada"), distinct=True),
            )
            .order_by("inscricoes_inicio", "titulo")
        )


class ChamadaAvaliadoresFormMixin(ManagementPermissionMixin):
    model = ChamadaAvaliadores
    form_class = ChamadaAvaliadoresForm
    template_name = "management/chamada_form.html"
    success_url = reverse_lazy("chamada_avaliadores_list")

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("atividade", "").isdigit():
            initial["atividade"] = self.request.GET["atividade"]
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Chamada de avaliadores salva com sucesso.")
        return super().form_valid(form)


class ChamadaAvaliadoresCreateView(ChamadaAvaliadoresFormMixin, CreateView):
    permission_required = "core.add_chamadaavaliadores"


class ChamadaAvaliadoresUpdateView(ChamadaAvaliadoresFormMixin, UpdateView):
    permission_required = "core.change_chamadaavaliadores"


class CandidaturaManagementListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = CandidaturaAvaliador
    permission_required = "core.view_candidaturaavaliador"
    template_name = "management/candidatura_list.html"
    context_object_name = "candidaturas"
    search_fields = ("usuario__first_name", "usuario__last_name", "usuario__email", "area_atuacao", "temas_interesse")

    def dispatch(self, request, *args, **kwargs):
        self.chamada = get_object_or_404(ChamadaAvaliadores.objects.select_related("atividade"), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset().filter(chamada=self.chamada).select_related("usuario", "analisada_por")
        status = self.request.GET.get("status")
        return queryset.filter(status=status) if status in CandidaturaAvaliador.Status.values else queryset

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, chamada=self.chamada, status_filtro=self.request.GET.get("status", ""))


@permission_required("core.change_candidaturaavaliador", raise_exception=True)
@transaction.atomic
def decidir_candidatura(request, pk):
    if request.method != "POST":
        raise PermissionDenied
    candidatura = get_object_or_404(CandidaturaAvaliador.objects.select_for_update(), pk=pk)
    acao = request.POST.get("acao")
    if acao not in {CandidaturaAvaliador.Status.APROVADA, CandidaturaAvaliador.Status.REJEITADA}:
        raise PermissionDenied
    candidatura.status = acao
    candidatura.justificativa_decisao = request.POST.get("justificativa_decisao", "").strip()
    candidatura.analisada_por = request.user
    candidatura.analisada_em = timezone.now()
    candidatura.save(update_fields=("status", "justificativa_decisao", "analisada_por", "analisada_em", "atualizada_em"))
    messages.success(request, f"Candidatura marcada como {candidatura.get_status_display().lower()}.")
    return redirect("candidatura_avaliador_list", pk=candidatura.chamada_id)


@permission_required("core.view_designacaoavaliacao", raise_exception=True)
def gerenciar_designacoes(request, pk):
    chamada = get_object_or_404(ChamadaAvaliadores.objects.select_related("atividade"), pk=pk)
    atividade = chamada.atividade
    if request.method == "POST":
        acao = request.POST.get("acao", "designar")
        if acao == "remover":
            if not request.user.has_perm("core.delete_designacaoavaliacao"):
                raise PermissionDenied
            designacao = get_object_or_404(DesignacaoAvaliacao, pk=request.POST.get("designacao"), trabalho__inscricao__atividade=atividade)
            if designacao.concluida:
                messages.error(request, "Uma avaliação concluída não pode ter sua designação removida.")
            else:
                designacao.delete()
                messages.success(request, "Designação removida.")
            return redirect("designacao_avaliacao_manage", pk=chamada.pk)

        if not request.user.has_perm("core.add_designacaoavaliacao"):
            raise PermissionDenied

        trabalho = get_object_or_404(Trabalho, pk=request.POST.get("trabalho"), inscricao__atividade=atividade)
        candidatura = get_object_or_404(
            CandidaturaAvaliador,
            pk=request.POST.get("candidatura"),
            chamada=chamada,
            status=CandidaturaAvaliador.Status.APROVADA,
        )
        designacao = DesignacaoAvaliacao(
            trabalho=trabalho,
            avaliador=candidatura.usuario,
            prazo=chamada.avaliacoes_fim,
            liberada_por=request.user,
        )
        try:
            designacao.full_clean()
            designacao.save()
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        except IntegrityError:
            messages.info(request, "Este avaliador já está designado para o trabalho.")
        else:
            messages.success(request, "Trabalho liberado para o avaliador.")
        return redirect("designacao_avaliacao_manage", pk=chamada.pk)

    trabalhos = (
        Trabalho.objects.filter(inscricao__atividade=atividade)
        .select_related("inscricao__usuario")
        .prefetch_related("designacoes_avaliacao__avaliador", "designacoes_avaliacao__avaliacao", "coautores")
    )
    candidaturas = chamada.candidaturas.filter(status=CandidaturaAvaliador.Status.APROVADA).select_related("usuario")
    return render(
        request,
        "management/designacao_list.html",
        {"chamada": chamada, "trabalhos": trabalhos, "candidaturas": candidaturas},
    )


@permission_required("core.view_avaliacao", raise_exception=True)
def consultar_avaliacao_management(request, pk):
    """Exibe à coordenação o parecer e a identificação completa do trabalho."""
    avaliacao = get_object_or_404(
        Avaliacao.objects.select_related(
            "designacao__avaliador",
            "designacao__trabalho__inscricao__usuario",
            "designacao__trabalho__inscricao__atividade",
        ),
        pk=pk,
    )
    return render(request, "management/avaliacao_detail.html", {"avaliacao": avaliacao})

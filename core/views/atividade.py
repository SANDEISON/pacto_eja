from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..forms import (
    AtividadeForm,
    CoautorFormSet,
    DadosPessoaisInscricaoForm,
    ProfileUserForm,
    TrabalhoForm,
)
from ..models import Atividade, Educador, Inscricao, Trabalho
from ..validators import somente_digitos
from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


class AtividadeListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    """Lista atividades para usuários com acesso à gestão."""
    model = Atividade
    permission_required = "core.view_atividade"
    template_name = "management/atividade_list.html"
    context_object_name = "atividades"
    search_fields = ("titulo", "descricao", "local", "link", "tipo")

    def has_permission(self):
        """Permite a consulta a quem pode visualizar ou editar atividades."""
        return self.request.user.has_perm("core.view_atividade") or self.request.user.has_perm("core.change_atividade")

    def get_queryset(self):
        """Inclui a quantidade de inscrições sem executar uma consulta por linha."""
        return super().get_queryset().annotate(total_inscricoes=Count("inscricoes")).order_by("data_inicio", "titulo")


class AtividadeFormMixin(ManagementPermissionMixin):
    """Compartilha a configuração das telas de criação e edição de atividades."""
    model = Atividade
    form_class = AtividadeForm
    template_name = "management/atividade_form.html"
    success_url = reverse_lazy("atividade_list")

    def form_valid(self, form):
        messages.success(self.request, "Atividade salva com sucesso.")
        return super().form_valid(form)


class AtividadeCreateView(AtividadeFormMixin, CreateView):
    """Cria uma atividade por meio do painel administrativo."""
    permission_required = "core.add_atividade"


class AtividadeUpdateView(AtividadeFormMixin, UpdateView):
    """Atualiza uma atividade existente no painel administrativo."""
    permission_required = "core.change_atividade"


class AtividadeDeleteView(ManagementPermissionMixin, DeleteView):
    """Exclui atividades que ainda não possuem inscrições protegidas."""
    model = Atividade
    permission_required = "core.delete_atividade"
    template_name = "management/confirm_delete.html"
    success_url = reverse_lazy("atividade_list")

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs, object_label="atividade", cancel_url_name="atividade_list"
        )

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "A atividade não pode ser excluída porque já possui inscrições.")
            return redirect("atividade_list")
        messages.success(self.request, "Atividade excluída com sucesso.")
        return response


class InscricaoListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    """Lista participantes e trabalhos de uma atividade específica."""
    model = Inscricao
    permission_required = "core.view_inscricao"
    template_name = "management/inscricao_list.html"
    context_object_name = "inscricoes"
    search_fields = (
        "usuario__first_name", "usuario__last_name", "usuario__email",
        "usuario__educador__cpf", "trabalho__titulo",
    )

    def dispatch(self, request, *args, **kwargs):
        """Carrega a atividade uma vez para reutilização nos demais métodos da view."""
        self.atividade = get_object_or_404(Atividade, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Busca inscrições com os relacionamentos usados pela tabela já carregados."""
        return (
            super().get_queryset()
            .filter(atividade=self.atividade)
            .select_related("usuario", "usuario__educador", "trabalho")
            .prefetch_related("trabalho__coautores")
        )

    def get_context_data(self, **kwargs):
        """Disponibiliza a atividade para o cabeçalho da página."""
        return super().get_context_data(**kwargs, atividade=self.atividade)


ACOES_INSCRICAO = {"inscrever", "submeter"}


def _carregar_atividade(atividade_id, bloquear=False):
    """Obtém uma atividade ativa e, no POST, bloqueia a linha durante a inscrição."""
    atividades = Atividade.objects.select_for_update() if bloquear else Atividade.objects.all()
    return get_object_or_404(atividades, pk=atividade_id, ativo=True)


def _criar_formularios_inscricao(request, educador, trabalho, acao):
    """Monta todos os formulários do fluxo com instâncias e prefixos consistentes."""
    dados_post = request.POST or None
    enviando_trabalho = acao == "submeter"
    formulario_usuario = ProfileUserForm(dados_post, instance=request.user, prefix="usuario")
    formulario_dados = DadosPessoaisInscricaoForm(dados_post, instance=educador, prefix="dados")
    formulario_trabalho = TrabalhoForm(
        request.POST if enviando_trabalho else None,
        request.FILES if enviando_trabalho else None,
        instance=trabalho or Trabalho(),
        prefix="trabalho",
        required=enviando_trabalho,
    )
    formulario_coautores = CoautorFormSet(
        request.POST if enviando_trabalho else None,
        instance=trabalho or formulario_trabalho.instance,
        prefix="coautor",
        form_kwargs={"autor": request.user},
    )
    return formulario_usuario, formulario_dados, formulario_trabalho, formulario_coautores


def _formularios_sao_validos(acao, formulario_usuario, formulario_dados, formulario_trabalho, formulario_coautores):
    """Valida sempre os dados pessoais e, quando solicitado, também o trabalho."""
    dados_pessoais_validos = formulario_usuario.is_valid() and formulario_dados.is_valid()
    if acao == "submeter":
        trabalho_valido = formulario_trabalho.is_valid() and formulario_coautores.is_valid()
        return trabalho_valido and dados_pessoais_validos
    return dados_pessoais_validos


def _salvar_inscricao(atividade, formulario_usuario, formulario_dados):
    """Atualiza o perfil e garante uma única inscrição por usuário e atividade."""
    usuario = formulario_usuario.save()
    educador = formulario_dados.save(commit=False)
    educador.usuario = usuario
    educador.nome_completo = usuario.get_full_name()
    educador.save()

    try:
        # O savepoint permite recuperar uma disputa entre duas requisições simultâneas.
        with transaction.atomic():
            inscricao, foi_criada = Inscricao.objects.get_or_create(
                atividade=atividade,
                usuario=usuario,
            )
    except IntegrityError:
        inscricao = Inscricao.objects.get(atividade=atividade, usuario=usuario)
        foi_criada = False
    return inscricao, foi_criada


def _salvar_trabalho(inscricao, formulario_trabalho, formulario_coautores):
    """Vincula o trabalho à inscrição antes de persistir seus coautores."""
    trabalho = formulario_trabalho.save(commit=False)
    trabalho.inscricao = inscricao
    trabalho.save()
    formulario_coautores.instance = trabalho
    formulario_coautores.save()


@login_required
@transaction.atomic
def inscricao_atividade(request, pk):
    """Exibe e processa a inscrição simples ou acompanhada de um trabalho."""
    atividade = _carregar_atividade(pk, bloquear=request.method == "POST")
    educador, _ = Educador.objects.get_or_create(usuario=request.user)
    inscricao = Inscricao.objects.filter(atividade=atividade, usuario=request.user).first()
    trabalho = Trabalho.objects.filter(inscricao=inscricao).first() if inscricao else None
    acao = request.POST.get("acao") if request.method == "POST" else None

    (
        formulario_usuario,
        formulario_dados,
        formulario_trabalho,
        formulario_coautores,
    ) = _criar_formularios_inscricao(
        request,
        educador,
        trabalho,
        acao,
    )

    if request.method == "POST":
        if acao not in ACOES_INSCRICAO:
            raise Http404("Ação de inscrição inválida.")
        inscricao_disponivel = inscricao is not None or atividade.inscricoes_abertas
        submissao_disponivel = acao != "submeter" or atividade.submissoes_abertas
        formularios_validos = _formularios_sao_validos(
            acao,
            formulario_usuario,
            formulario_dados,
            formulario_trabalho,
            formulario_coautores,
        )

        if not inscricao_disponivel:
            messages.error(request, "As inscrições para esta atividade estão encerradas ou não há mais vagas.")
        elif not submissao_disponivel:
            messages.error(request, "O prazo para submissão de trabalhos está encerrado.")
        elif formularios_validos:
            inscricao, inscricao_criada = _salvar_inscricao(
                atividade,
                formulario_usuario,
                formulario_dados,
            )

            if acao == "submeter":
                _salvar_trabalho(inscricao, formulario_trabalho, formulario_coautores)
                messages.success(request, "Inscrição finalizada e trabalho submetido com sucesso.")
            elif inscricao_criada:
                messages.success(request, "Sua inscrição foi finalizada com sucesso.")
            else:
                messages.info(request, "Você já está inscrito nesta atividade. Seus dados foram atualizados.")
            return redirect("dashboard")

    return render(
        request,
        "atividades/inscricao.html",
        {
            "atividade": atividade,
            "inscricao": inscricao,
            "trabalho": trabalho,
            # As chaves permanecem curtas porque já fazem parte do contrato com o template.
            "user_form": formulario_usuario,
            "dados_form": formulario_dados,
            "trabalho_form": formulario_trabalho,
            "coautor_formset": formulario_coautores,
            "active_tab": (
                "trabalho"
                if acao == "submeter" and not formulario_usuario.errors and not formulario_dados.errors
                else "pessoal"
            ),
        },
    )


@login_required
def baixar_trabalho(request, pk):
    """Entrega o PDF somente ao autor ou a quem possui permissão de consulta."""
    trabalho = get_object_or_404(Trabalho.objects.select_related("inscricao__usuario"), pk=pk)
    autorizado = trabalho.inscricao.usuario_id == request.user.pk or request.user.has_perm("core.view_trabalho")
    if not autorizado:
        raise Http404
    return FileResponse(
        trabalho.arquivo.open("rb"),
        as_attachment=True,
        filename=trabalho.arquivo.name.rsplit("/", 1)[-1],
        content_type="application/pdf",
    )


@login_required
def buscar_coautores(request):
    """Retorna até oito usuários ativos para o campo de busca de coautores."""
    termo = request.GET.get("q", "").strip()
    if len(termo) < 3:
        return JsonResponse({"results": [], "message": "Digite ao menos 3 caracteres."})

    digitos = somente_digitos(termo)
    cpf_autor = getattr(getattr(request.user, "educador", None), "cpf", "") or ""
    cpf_autor = somente_digitos(cpf_autor)
    if digitos and len(digitos) == 11 and digitos == cpf_autor:
        return JsonResponse(
            {
                "results": [],
                "message": "Você já é o autor principal do trabalho e não precisa ser incluído como coautor.",
            }
        )

    filtros = (
        Q(first_name__icontains=termo)
        | Q(last_name__icontains=termo)
        | Q(email__icontains=termo)
        | Q(username__icontains=termo)
        | Q(educador__nome_completo__icontains=termo)
    )
    if digitos:
        filtros |= Q(educador__cpf__icontains=digitos) | Q(username__icontains=digitos)

    usuarios = (
        get_user_model().objects.filter(filtros, is_active=True)
        .exclude(pk=request.user.pk)
        .distinct()
        .order_by("first_name", "last_name", "email")[:8]
    )
    return JsonResponse(
        {
            "results": [
                {
                    "id": usuario.pk,
                    "name": usuario.get_full_name() or usuario.get_username(),
                    "email": usuario.email,
                }
                for usuario in usuarios
            ]
        }
    )

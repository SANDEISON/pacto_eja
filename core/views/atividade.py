from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..forms import (
    AtividadeForm,
    AtividadeRefeicaoFormSet,
    AtividadeSalaProgramacaoFormSet,
    CoautorFormSet,
    DadosPessoaisInscricaoForm,
    EnderecoForm,
    EvidenciaTrabalhoFormSet,
    FormacaoFormSet,
    ProfileUserForm,
    ProgramacaoSalaInlineForm,
    SalaAtividadeForm,
    TrabalhoForm,
    TrabalhoMunicipioFormSet,
)
from ..models import (
    Atividade,
    DesignacaoAvaliacao,
    Educador,
    Endereco,
    Inscricao,
    ProgramacaoSala,
    RascunhoInscricao,
    Sala,
    Trabalho,
)
from ..validators import somente_digitos
from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


class AtividadeListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    """Lista atividades para usuários com acesso à gestão."""
    model = Atividade
    permission_required = "core.view_atividade"
    template_name = "management/atividade_list.html"
    context_object_name = "atividades"
    search_fields = ("titulo", "descricao", "local", "tipo")

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

    def get_refeicao_formset(self, instance=None):
        """Monta o formset de refeições para a atividade atual ou ainda não salva."""
        kwargs = {
            "instance": instance or self.object or Atividade(),
            "prefix": "refeicoes",
        }
        if self.request.method == "POST" and "refeicoes-TOTAL_FORMS" in self.request.POST:
            kwargs["data"] = self.request.POST
        return AtividadeRefeicaoFormSet(**kwargs)

    def get_context_data(self, **kwargs):
        """Inclui refeições e o cadastro rápido de sala no contexto da página."""
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        context["refeicao_formset"] = kwargs.get("refeicao_formset") or self.get_refeicao_formset(
            instance=form.instance if form else None
        )
        context["can_create_activity_room"] = self.request.user.has_perms(
            ("core.add_sala", "core.add_programacaosala")
        )
        context["can_add_room_schedule"] = self.request.user.has_perm(
            "core.add_programacaosala"
        )
        context["can_change_room_schedule"] = self.request.user.has_perm(
            "core.change_programacaosala"
        )
        context["can_delete_room_schedule"] = self.request.user.has_perm(
            "core.delete_programacaosala"
        )
        context["can_add_activity_room"] = bool(
            self.object and context["can_create_activity_room"]
        )
        context["programacoes_vinculadas"] = (
            self.object.programacoes.select_related("sala", "tematica").order_by(
                "sala__nome", "data", "turno", "modalidade"
            )
            if self.object
            else ()
        )
        if context["can_add_activity_room"]:
            nova_sala = SalaAtividadeForm(prefix="nova_sala")
            context["nova_sala_form"] = nova_sala
            context["nova_programacao_formset"] = AtividadeSalaProgramacaoFormSet(
                instance=nova_sala.instance,
                prefix="nova_programacoes",
            )
        if self.object and (
            context["can_add_room_schedule"] or context["can_change_room_schedule"]
        ):
            context["programacao_atividade_form"] = ProgramacaoSalaInlineForm(
                prefix="programacao"
            )
        return context

    def form_valid(self, form):
        """Persiste atividade e refeições juntas para evitar gravação parcial."""
        formset = self.get_refeicao_formset(instance=form.instance)
        if formset.is_bound and not formset.is_valid():
            return self.render_to_response(
                self.get_context_data(form=form, refeicao_formset=formset)
            )
        with transaction.atomic():
            self.object = form.save()
            if formset.is_bound:
                formset.instance = self.object
                formset.save()
        messages.success(self.request, "Atividade e refeições salvas com sucesso.")
        return redirect(self.success_url)


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
        """Configura os rótulos usados pela confirmação de exclusão."""
        return super().get_context_data(
            **kwargs, object_label="atividade", cancel_url_name="atividade_list"
        )

    def form_valid(self, form):
        """Impede a exclusão quando inscrições existentes protegem a atividade."""
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "A atividade não pode ser excluída porque já possui inscrições.")
            return redirect("atividade_list")
        messages.success(self.request, "Atividade excluída com sucesso.")
        return response


@login_required
@permission_required(
    ("core.change_atividade", "core.add_sala", "core.add_programacaosala"),
    raise_exception=True,
)
def adicionar_sala_atividade(request, pk):
    """Cria uma sala com programações e as vincula à atividade informada."""
    if request.method != "POST":
        raise Http404
    atividade = get_object_or_404(Atividade, pk=pk)
    sala_form = SalaAtividadeForm(request.POST, prefix="nova_sala")
    programacao_formset = AtividadeSalaProgramacaoFormSet(
        request.POST,
        instance=sala_form.instance,
        prefix="nova_programacoes",
    )
    if not sala_form.is_valid() or not programacao_formset.is_valid():
        errors = []
        for field_errors in sala_form.errors.values():
            errors.extend(str(error) for error in field_errors)
        errors.extend(str(error) for error in programacao_formset.non_form_errors())
        for schedule_form in programacao_formset.forms:
            for field_errors in schedule_form.errors.values():
                errors.extend(str(error) for error in field_errors)
        return JsonResponse({"errors": errors}, status=400)

    programacoes_novas = [
        form.cleaned_data
        for form in programacao_formset.forms
        if form.cleaned_data and not form.cleaned_data.get("DELETE")
    ]
    modalidades_atividade = {
        valor for valor, _ in atividade.modalidades_disponiveis
    }
    if any(
        programacao.get("modalidade") not in modalidades_atividade
        for programacao in programacoes_novas
    ):
        return JsonResponse(
            {"errors": ["As programações devem usar uma modalidade disponível nesta atividade."]},
            status=400,
        )

    with transaction.atomic():
        sala = sala_form.save()
        programacao_formset.instance = sala
        programacoes = programacao_formset.save()
        atividade.programacoes.add(*programacoes)

    return JsonResponse(
        {
            "message": "Sala e programações adicionadas e vinculadas com sucesso.",
            "sala": _serializar_sala_atividade(atividade, sala),
            "programacoes": [
                _serializar_programacao_atividade(atividade, programacao)
                for programacao in programacoes
            ],
        },
        status=201,
    )


def _serializar_sala_atividade(atividade, sala):
    """Converte uma sala nos dados necessários para atualizar a interface."""
    return {
        "id": sala.pk,
        "nome": sala.nome,
        "add_schedule_url": reverse(
            "atividade_add_room_schedule",
            kwargs={"pk": atividade.pk, "sala_pk": sala.pk},
        ),
    }


def _serializar_programacao_atividade(atividade, programacao):
    """Converte uma programação e suas URLs no contrato JSON da interface."""
    return {
        "id": programacao.pk,
        "label": str(programacao),
        "data": programacao.data.strftime("%d/%m/%Y"),
        "data_iso": programacao.data.isoformat(),
        "turno": programacao.get_turno_display(),
        "turno_value": programacao.turno,
        "modalidade": programacao.get_modalidade_display(),
        "modalidade_value": programacao.modalidade,
        "link": programacao.link,
        "tematica": str(programacao.tematica),
        "tematica_id": programacao.tematica_id,
        "descricao": programacao.descricao,
        "capacidade": programacao.quantidade_max_participantes,
        "edit_url": reverse(
            "atividade_edit_room_schedule",
            kwargs={"pk": atividade.pk, "programacao_pk": programacao.pk},
        ),
        "delete_url": reverse(
            "atividade_delete_room_schedule",
            kwargs={"pk": atividade.pk, "programacao_pk": programacao.pk},
        ),
    }


def _programacao_atividade_json(atividade, programacao, status=200):
    """Cria a resposta usada depois da inclusão ou edição de uma programação."""
    return JsonResponse(
        {
            "message": "Programação salva e vinculada com sucesso.",
            "sala": _serializar_sala_atividade(atividade, programacao.sala),
            "programacao": _serializar_programacao_atividade(
                atividade, programacao
            ),
        },
        status=status,
    )


def _validar_modalidade_programacao(atividade, form):
    """Confere se a programação usa uma modalidade aceita pela atividade."""
    modalidade = form.cleaned_data.get("modalidade")
    if modalidade not in {valor for valor, _ in atividade.modalidades_disponiveis}:
        form.add_error(
            "modalidade", "A modalidade não está disponível nesta atividade."
        )
        return False
    return True


def _form_errors_json(form):
    """Converte todos os erros de um formulário em uma resposta JSON uniforme."""
    errors = [
        str(error)
        for field_errors in form.errors.values()
        for error in field_errors
    ]
    return JsonResponse({"errors": errors}, status=400)


@login_required
@permission_required(
    ("core.change_atividade", "core.add_programacaosala"), raise_exception=True
)
def adicionar_programacao_sala_atividade(request, pk, sala_pk):
    """Adiciona uma programação a uma sala já vinculada à atividade."""
    if request.method != "POST":
        raise Http404
    atividade = get_object_or_404(Atividade, pk=pk)
    sala = get_object_or_404(
        Sala, pk=sala_pk, programacoes__atividades=atividade
    )
    programacao = ProgramacaoSala(sala=sala)
    form = ProgramacaoSalaInlineForm(
        request.POST, instance=programacao, prefix="programacao"
    )
    if not form.is_valid() or not _validar_modalidade_programacao(atividade, form):
        return _form_errors_json(form)
    with transaction.atomic():
        programacao = form.save()
        atividade.programacoes.add(programacao)
    return _programacao_atividade_json(atividade, programacao, status=201)


@login_required
@permission_required(
    ("core.change_atividade", "core.change_programacaosala"), raise_exception=True
)
def editar_programacao_sala_atividade(request, pk, programacao_pk):
    """Edita uma programação vinculada à atividade."""
    if request.method != "POST":
        raise Http404
    atividade = get_object_or_404(Atividade, pk=pk)
    programacao = get_object_or_404(
        ProgramacaoSala.objects.select_related("sala", "tematica"),
        pk=programacao_pk,
        atividades=atividade,
    )
    form = ProgramacaoSalaInlineForm(
        request.POST, instance=programacao, prefix="programacao"
    )
    if not form.is_valid() or not _validar_modalidade_programacao(atividade, form):
        return _form_errors_json(form)
    programacao = form.save()
    return _programacao_atividade_json(atividade, programacao)


@login_required
@permission_required(
    ("core.change_atividade", "core.delete_programacaosala"), raise_exception=True
)
def excluir_programacao_sala_atividade(request, pk, programacao_pk):
    """Remove uma programação da atividade e exclui o registro quando órfão."""
    if request.method != "POST":
        raise Http404
    atividade = get_object_or_404(Atividade, pk=pk)
    programacao = get_object_or_404(
        ProgramacaoSala, pk=programacao_pk, atividades=atividade
    )
    sala_id = programacao.sala_id
    with transaction.atomic():
        atividade.programacoes.remove(programacao)
        if not programacao.atividades.exists():
            programacao.delete()
    sala_sem_programacoes = not atividade.programacoes.filter(sala_id=sala_id).exists()
    return JsonResponse(
        {
            "message": "Programação excluída da atividade.",
            "programacao_id": programacao_pk,
            "sala_id": sala_id,
            "room_empty": sala_sem_programacoes,
        }
    )


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
            .prefetch_related("trabalho__coautores", "refeicoes")
        )

    def get_context_data(self, **kwargs):
        """Disponibiliza a atividade para o cabeçalho da página."""
        return super().get_context_data(**kwargs, atividade=self.atividade)


ACOES_INSCRICAO = {"inscrever", "atualizar", "submeter", "salvar_rascunho"}
PREFIXOS_RASCUNHO = (
    "usuario-", "dados-", "endereco-", "formacao-", "trabalho-", "coautor-",
    "municipio-", "evidencia-",
)


@dataclass
class FormulariosInscricao:
    """Agrupa os formulários que compõem as etapas de uma inscrição."""

    usuario: ProfileUserForm
    dados_pessoais: DadosPessoaisInscricaoForm
    endereco: EnderecoForm
    formacoes: object
    trabalho: TrabalhoForm
    coautores: object
    municipios: object
    evidencias: object

    def validar(self, acao):
        """Valida o perfil e inclui os formulários de trabalho somente na submissão."""
        perfil_valido = all(
            [
                self.usuario.is_valid(),
                self.dados_pessoais.is_valid(),
                not self.endereco.is_bound or self.endereco.is_valid(),
                not self.formacoes.is_bound or self.formacoes.is_valid(),
            ]
        )
        if acao != "submeter":
            return perfil_valido

        trabalho_valido = all(
            [self.trabalho.is_valid(), self.coautores.is_valid(), self.evidencias.is_valid()]
        )
        if self.trabalho.modelo_submissao == Atividade.ModeloSubmissao.RELATO_EXPERIENCIA:
            trabalho_valido = all([self.municipios.is_valid(), trabalho_valido])
        return perfil_valido and trabalho_valido

    def perfil_sem_erros(self):
        """Informa se os erros atuais permitem direcionar o usuário à etapa seguinte."""
        erros_fora_da_modalidade = {
            campo
            for campo in self.dados_pessoais.errors
            if campo not in ("modalidade_inscricao", "programacoes", "refeicoes")
        }
        return (
            not self.usuario.errors
            and not erros_fora_da_modalidade
            and not self.endereco.errors
            and not any(self.formacoes.errors)
            and not self.formacoes.non_form_errors()
        )

    def contexto_template(self):
        """Converte os nomes internos descritivos nas chaves esperadas pelo template."""
        return {
            "user_form": self.usuario,
            "dados_form": self.dados_pessoais,
            "endereco_form": self.endereco,
            "formacao_formset": self.formacoes,
            "trabalho_form": self.trabalho,
            "coautor_formset": self.coautores,
            "municipio_formset": self.municipios,
            "evidencia_formset": self.evidencias,
        }


def _carregar_atividade(atividade_id, bloquear=False):
    """Obtém uma atividade ativa e, no POST, bloqueia a linha durante a inscrição."""
    atividades = Atividade.objects.select_for_update() if bloquear else Atividade.objects.all()
    return get_object_or_404(atividades, pk=atividade_id, ativo=True)


def _criar_formularios_inscricao(request, atividade, inscricao, educador, endereco, trabalho, acao):
    """Monta todos os formulários do fluxo com instâncias e prefixos consistentes."""
    dados_post = request.POST or None
    enviando_trabalho = acao == "submeter"
    formulario_usuario = ProfileUserForm(dados_post, instance=request.user, prefix="usuario")
    formulario_dados = DadosPessoaisInscricaoForm(
        dados_post,
        instance=educador,
        prefix="dados",
        atividade=atividade,
        inscricao=inscricao,
    )
    endereco_data = request.POST if request.method == "POST" else None
    formulario_endereco = EnderecoForm(
        endereco_data,
        instance=endereco,
        prefix="endereco",
        required_for_registration=True,
    )
    formacao_data = request.POST if request.method == "POST" else None
    formulario_formacoes = FormacaoFormSet(
        formacao_data,
        instance=educador,
        prefix="formacao",
        require_one=True,
    )
    formulario_trabalho = TrabalhoForm(
        request.POST if enviando_trabalho else None,
        request.FILES if enviando_trabalho else None,
        instance=trabalho or Trabalho(),
        prefix="trabalho",
        required=enviando_trabalho,
        modelo_submissao=atividade.modelo_submissao,
    )
    formulario_coautores = CoautorFormSet(
        request.POST if enviando_trabalho else None,
        instance=trabalho or formulario_trabalho.instance,
        prefix="coautor",
    )
    relato = atividade.modelo_submissao == Atividade.ModeloSubmissao.RELATO_EXPERIENCIA
    estado_id = (
        request.POST.get("trabalho-estado")
        if request.method == "POST"
        else getattr(trabalho, "estado_id", None)
    )
    formulario_municipios = TrabalhoMunicipioFormSet(
        request.POST if enviando_trabalho and relato else None,
        instance=trabalho or formulario_trabalho.instance,
        prefix="municipio",
        form_kwargs={"estado": estado_id},
    )
    formulario_evidencias = EvidenciaTrabalhoFormSet(
        request.POST if enviando_trabalho else None,
        request.FILES if enviando_trabalho else None,
        instance=trabalho or formulario_trabalho.instance,
        prefix="evidencia",
    )
    return FormulariosInscricao(
        usuario=formulario_usuario,
        dados_pessoais=formulario_dados,
        endereco=formulario_endereco,
        formacoes=formulario_formacoes,
        trabalho=formulario_trabalho,
        coautores=formulario_coautores,
        municipios=formulario_municipios,
        evidencias=formulario_evidencias,
    )


def _extrair_dados_rascunho(post):
    """Mantém somente campos conhecidos e limita o volume salvo no JSON."""
    dados = {}
    for chave, valores in post.lists():
        if not chave.startswith(PREFIXOS_RASCUNHO) or len(dados) >= 200:
            continue
        dados[chave] = [str(valor)[:2000] for valor in valores[:20]]
    return dados


def _salvar_rascunho(request, atividade):
    """Persiste o estado bruto para aceitar campos ainda incompletos ou inválidos."""
    etapas = {valor for valor, _ in RascunhoInscricao.Etapa.choices}
    etapa = request.POST.get("etapa_atual", RascunhoInscricao.Etapa.PESSOAL)
    if etapa not in etapas:
        etapa = RascunhoInscricao.Etapa.PESSOAL
    return RascunhoInscricao.objects.update_or_create(
        atividade=atividade,
        usuario=request.user,
        defaults={"dados": _extrair_dados_rascunho(request.POST), "etapa": etapa},
    )[0]


def _salvar_inscricao(atividade, formularios):
    """Atualiza o perfil e garante uma única inscrição por usuário e atividade."""
    usuario = formularios.usuario.save()
    educador = formularios.dados_pessoais.save(commit=False)
    educador.usuario = usuario
    educador.nome_completo = usuario.get_full_name()
    educador.save()
    if formularios.endereco.is_bound and formularios.endereco.has_changed():
        endereco = formularios.endereco.save(commit=False)
        endereco.educador = educador
        endereco.save()
    if formularios.formacoes.is_bound:
        formularios.formacoes.instance = educador
        formularios.formacoes.save()

    try:
        # O savepoint permite recuperar uma disputa entre duas requisições simultâneas.
        with transaction.atomic():
            inscricao, foi_criada = Inscricao.objects.get_or_create(
                atividade=atividade,
                usuario=usuario,
                defaults={"modalidade": formularios.dados_pessoais.cleaned_data["modalidade_inscricao"]},
            )
    except IntegrityError:
        inscricao = Inscricao.objects.get(atividade=atividade, usuario=usuario)
        foi_criada = False
    modalidade = formularios.dados_pessoais.cleaned_data["modalidade_inscricao"]
    refeicoes = (
        formularios.dados_pessoais.cleaned_data["refeicoes"]
        if modalidade == Inscricao.Modalidade.PRESENCIAL
        else ()
    )
    campos_alterados = []
    if inscricao.modalidade != modalidade:
        inscricao.modalidade = modalidade
        campos_alterados.append("modalidade")
    if campos_alterados:
        inscricao.save(update_fields=campos_alterados)
    inscricao.refeicoes.set(refeicoes)
    inscricao.programacoes.set(formularios.dados_pessoais.cleaned_data["programacoes"])
    return inscricao, foi_criada


def _salvar_trabalho(inscricao, formularios):
    """Vincula o trabalho à inscrição antes de persistir sua autoria ordenada."""
    trabalho = formularios.trabalho.save(commit=False)
    trabalho.inscricao = inscricao
    trabalho.versao_termos = Trabalho.VERSAO_ATUAL_TERMOS
    trabalho.termos_aceitos_em = timezone.now()
    trabalho.save()
    formularios.coautores.instance = trabalho
    formularios.coautores.save()
    formularios.evidencias.instance = trabalho
    formularios.evidencias.save()
    if formularios.trabalho.modelo_submissao == Atividade.ModeloSubmissao.RELATO_EXPERIENCIA:
        formularios.municipios.instance = trabalho
        formularios.municipios.save()
        trabalho.n_participantes = sum(
            item.participantes for item in trabalho.municipios.all()
        )
        trabalho.save(update_fields=("n_participantes",))


@login_required
@transaction.atomic
def inscricao_atividade(request, pk):
    """Exibe e processa a inscrição simples ou acompanhada de um trabalho."""
    atividade = _carregar_atividade(pk, bloquear=request.method == "POST")
    educador, _ = Educador.objects.get_or_create(usuario=request.user)
    endereco = Endereco.objects.filter(educador=educador).first() or Endereco(educador=educador)
    inscricao = Inscricao.objects.filter(atividade=atividade, usuario=request.user).first()
    rascunho = RascunhoInscricao.objects.filter(atividade=atividade, usuario=request.user).first()
    trabalho = Trabalho.objects.filter(inscricao=inscricao).first() if inscricao else None
    acao = request.POST.get("acao") if request.method == "POST" else None

    formularios = _criar_formularios_inscricao(
        request,
        atividade,
        inscricao,
        educador,
        endereco,
        trabalho,
        acao,
    )

    if request.method == "POST":
        if acao not in ACOES_INSCRICAO:
            raise Http404("Ação de inscrição inválida.")
        if acao == "salvar_rascunho":
            pode_salvar = atividade.periodo_inscricoes_aberto or bool(
                inscricao and atividade.submissoes_abertas
            )
            if pode_salvar:
                _salvar_rascunho(request, atividade)
                mensagem = "Rascunho salvo. Você pode continuar a inscrição depois."
                if request.FILES:
                    mensagem += " Selecione o arquivo novamente quando retornar."
                messages.success(request, mensagem)
            else:
                messages.error(request, "O prazo para salvar esta inscrição está encerrado.")
            return redirect("dashboard")
        if acao == "atualizar":
            inscricao_disponivel = bool(inscricao and atividade.periodo_inscricoes_aberto)
        elif acao == "inscrever":
            inscricao_disponivel = bool(
                atividade.periodo_inscricoes_aberto
                and (inscricao is not None or atividade.inscricoes_abertas)
            )
        else:
            inscricao_disponivel = inscricao is not None or atividade.inscricoes_abertas
        submissao_disponivel = acao != "submeter" or atividade.submissoes_abertas
        formularios_validos = formularios.validar(acao)

        if not inscricao_disponivel:
            messages.error(request, "As inscrições para esta atividade estão encerradas ou não há mais vagas.")
        elif not submissao_disponivel:
            messages.error(request, "O prazo para submissão de trabalhos está encerrado.")
        elif formularios_validos:
            inscricao, inscricao_criada = _salvar_inscricao(atividade, formularios)

            if acao == "submeter":
                _salvar_trabalho(inscricao, formularios)
                messages.success(request, "Inscrição finalizada e trabalho submetido com sucesso.")
            elif acao == "atualizar":
                messages.success(request, "Sua inscrição foi atualizada com sucesso.")
            elif inscricao_criada:
                messages.success(request, "Sua inscrição foi finalizada com sucesso.")
            else:
                messages.info(request, "Você já está inscrito nesta atividade. Seus dados foram atualizados.")
            if rascunho:
                rascunho.delete()
            return redirect("dashboard")

    active_tab = rascunho.etapa if request.method == "GET" and rascunho else "pessoal"
    perfil_sem_erros = formularios.perfil_sem_erros()
    if acao == "submeter" and perfil_sem_erros and not formularios.dados_pessoais.errors:
        active_tab = "trabalho"
    elif (
        {"modalidade_inscricao", "programacoes", "refeicoes"}
        & set(formularios.dados_pessoais.errors)
        and perfil_sem_erros
    ):
        active_tab = "modalidade"

    return render(
        request,
        "atividades/inscricao.html",
        {
            "atividade": atividade,
            "inscricao": inscricao,
            "trabalho": trabalho,
            **formularios.contexto_template(),
            "active_tab": active_tab,
            "rascunho": rascunho,
            "dados_rascunho": rascunho.dados if request.method == "GET" and rascunho else {},
            "pode_salvar_rascunho": atividade.periodo_inscricoes_aberto or bool(
                inscricao and atividade.submissoes_abertas
            ),
        },
    )


@login_required
@transaction.atomic
def cancelar_inscricao_atividade(request, pk):
    """Confirma e cancela a inscrição do usuário somente durante o período permitido."""
    atividade = _carregar_atividade(pk, bloquear=request.method == "POST")
    inscricao = get_object_or_404(
        Inscricao.objects.select_related("atividade", "usuario"),
        atividade=atividade,
        usuario=request.user,
    )

    if not atividade.periodo_inscricoes_aberto:
        messages.error(request, "O período para cancelar esta inscrição está encerrado.")
        return redirect("dashboard")

    if request.method == "POST":
        inscricao.delete()
        messages.success(request, "Sua inscrição foi cancelada com sucesso.")
        return redirect("dashboard")

    return render(
        request,
        "atividades/confirmar_cancelamento.html",
        {"atividade": atividade, "inscricao": inscricao},
    )


@login_required
def baixar_trabalho(request, pk):
    """Entrega o PDF ao autor, à gestão ou a um avaliador designado."""
    trabalho = get_object_or_404(Trabalho.objects.select_related("inscricao__usuario"), pk=pk)
    autorizado = (
        trabalho.inscricao.usuario_id == request.user.pk
        or request.user.has_perm("core.view_trabalho")
        or DesignacaoAvaliacao.objects.filter(trabalho=trabalho, avaliador=request.user).exists()
    )
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
    """Retorna até oito usuários ativos para compor a autoria do trabalho."""
    termo = request.GET.get("q", "").strip()
    if len(termo) < 3:
        return JsonResponse({"results": [], "message": "Digite ao menos 3 caracteres."})

    digitos = somente_digitos(termo)
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

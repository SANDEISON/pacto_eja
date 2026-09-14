from django.contrib import messages
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..forms import SalaProgramacaoFormSet
from ..models import (
    Cidade,
    CorRaca,
    CursoCertificado,
    Educador,
    EducadorGenero,
    Escola,
    Estado,
    Modalidade,
    Nivel,
    ProgramacaoSala,
    Sala,
    Situacao,
    TematicaSala,
)
from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


CATALOGS = {
    "cidades": {
        "model": Cidade,
        "title": "Cidades",
        "singular": "cidade",
        "fields": ("codigo_ibge", "estado", "nome_cidade"),
        "search_fields": ("nome_cidade", "estado__nome_estado", "estado__sigla", "codigo_ibge"),
        "columns": (("Código IBGE", "codigo_ibge"), ("Cidade", "nome_cidade"), ("Estado", "estado")),
        "select_related": ("estado",),
        "list_url_name": "city_list",
    },
    "cores-racas": {
        "model": CorRaca,
        "title": "Cores/raças",
        "singular": "cor/raça",
        "fields": ("nome",),
        "search_fields": ("nome",),
        "columns": (("ID", "pk"), ("Nome", "nome")),
        "list_url_name": "race_color_list",
    },
    "cursos-certificados": {
        "model": CursoCertificado,
        "title": "Cursos para certificados",
        "singular": "curso para certificado",
        "fields": ("nome",),
        "search_fields": ("nome",),
        "columns": (("ID", "pk"), ("Curso", "nome")),
        "list_url_name": "certificate_course_list",
    },
    "generos-educadores": {
        "model": EducadorGenero,
        "title": "Gêneros",
        "singular": "gênero do educador",
        "fields": ("codigo", "nome"),
        "search_fields": ("codigo", "nome"),
        "columns": (("ID", "pk"), ("Nome", "nome"), ("Código", "codigo")),
        "list_url_name": "educator_gender_list",
    },
    "cadastros-educadores": {
        "model": Educador,
        "title": "Educadores",
        "singular": "educador",
        "fields": ("usuario", "nome_completo", "nome_social", "cpf", "data_nascimento", "genero", "telefone", "estado_civil", "cor_raca"),
        "search_fields": ("nome_completo", "nome_social", "cpf", "usuario__username", "usuario__email"),
        "columns": (("Nome", "nome_completo"), ("Usuário", "usuario"), ("CPF", "cpf"), ("Gênero", "genero"), ("Cor/raça", "cor_raca")),
        "select_related": ("usuario", "genero", "estado_civil", "cor_raca"),
        "list_url_name": "educator_model_list",
        "allow_add": False,
    },
    "escolas": {
        "model": Escola,
        "title": "Escolas",
        "singular": "escola",
        "fields": ("id_escola", "nome", "id_municipio", "sigla_uf", "restricao_atendimento", "localizacao", "localidade_diferenciada", "categoria_administrativa", "endereco", "telefone", "dependencia_administrativa", "categoria_privada", "etapas_modalidades_oferecidas"),
        "search_fields": ("id_escola", "nome", "id_municipio", "sigla_uf", "endereco"),
        "columns": (("ID", "id_escola"), ("Escola", "nome"), ("Município", "id_municipio"), ("UF", "sigla_uf"), ("Localização", "localizacao")),
        "list_url_name": "school_list",
    },
    "estados": {
        "model": Estado,
        "title": "Estados",
        "singular": "estado",
        "fields": ("nome_estado", "sigla"),
        "search_fields": ("nome_estado", "sigla"),
        "columns": (("ID", "pk"), ("Estado", "nome_estado"), ("Sigla", "sigla")),
        "list_url_name": "state_list",
    },
    "niveis": {
        "model": Nivel,
        "title": "Níveis",
        "singular": "nível",
        "fields": ("codigo", "nome"),
        "search_fields": ("codigo", "nome"),
        "columns": (("ID", "pk"), ("Nome", "nome"), ("Código", "codigo")),
        "list_url_name": "level_list",
    },
    "modalidades": {
        "model": Modalidade,
        "title": "Modalidades",
        "singular": "modalidade",
        "fields": ("codigo", "nome"),
        "search_fields": ("codigo", "nome"),
        "columns": (("ID", "pk"), ("Nome", "nome"), ("Código", "codigo")),
        "list_url_name": "modality_list",
    },
    "situacoes": {
        "model": Situacao,
        "title": "Situações",
        "singular": "situação",
        "fields": ("codigo", "nome"),
        "search_fields": ("codigo", "nome"),
        "columns": (("ID", "pk"), ("Nome", "nome"), ("Código", "codigo")),
        "list_url_name": "situation_list",
    },
    "salas": {
        "model": Sala,
        "title": "Salas",
        "singular": "sala",
        "fields": ("nome",),
        "search_fields": ("nome",),
        "columns": (("ID", "pk"), ("Sala", "nome")),
        "list_url_name": "room_list",
    },
    "programacoes-salas": {
        "model": ProgramacaoSala,
        "title": "Programações das salas",
        "singular": "programação da sala",
        "fields": (
            "sala",
            "data",
            "turno",
            "modalidade",
            "link",
            "tematica",
            "descricao",
            "quantidade_max_participantes",
        ),
        "search_fields": (
            "sala__nome",
            "tematica__nome",
            "tematica__mediador",
            "descricao",
        ),
        "columns": (
            ("Sala", "sala"),
            ("Data", "data"),
            ("Turno", "get_turno_display"),
            ("Modalidade", "get_modalidade_display"),
            ("Link", "link"),
            ("Temática", "tematica"),
            ("Vagas", "quantidade_max_participantes"),
        ),
        "select_related": ("sala", "tematica"),
        "list_url_name": "room_schedule_list",
    },
    "tematicas-salas": {
        "model": TematicaSala,
        "title": "Temáticas das salas",
        "singular": "temática da sala",
        "fields": ("nome", "mediador"),
        "search_fields": ("nome", "mediador"),
        "columns": (("Temática", "nome"), ("Mediador", "mediador")),
        "list_url_name": "room_theme_list",
    },
}


def resolve_attr(registro, caminho_atributo):
    """Resolve acessos como ``estado__sigla`` para montar tabelas genéricas."""
    valor_atual = registro
    for atributo in caminho_atributo.split("__"):
        valor_atual = getattr(valor_atual, atributo, None)
        if valor_atual is None:
            return "—"
        if callable(valor_atual):
            valor_atual = valor_atual()
    return valor_atual if valor_atual not in (None, "") else "—"


def bootstrap_widget_class(widget):
    """Retorna a classe Bootstrap adequada ao tipo de widget do Django."""
    input_type = getattr(widget, "input_type", "")
    if input_type == "checkbox":
        return "form-check-input"
    if input_type == "select":
        return "form-select"
    return "form-control"


class CatalogMixin(ManagementPermissionMixin):
    """Seleciona a definição do catálogo e deriva sua permissão de acesso."""
    catalog_key = None
    action = "view"

    def setup(self, request, *args, **kwargs):
        """Valida a chave recebida na URL e configura o model correspondente."""
        super().setup(request, *args, **kwargs)
        self.catalog_key = self.catalog_key or kwargs.get("catalog_key")
        try:
            self.catalog = CATALOGS[self.catalog_key]
        except KeyError as error:
            raise Http404("Cadastro administrativo não encontrado.") from error
        self.model = self.catalog["model"]

    def get_permission_required(self):
        """Monta o codename esperado pelo sistema de permissões do Django."""
        return (f"{self.model._meta.app_label}.{self.action}_{self.model._meta.model_name}",)

    def has_permission(self):
        """Aceita visualização para quem possui permissão de leitura ou alteração."""
        if self.action == "view":
            opts = self.model._meta
            return self.request.user.has_perm(
                f"{opts.app_label}.view_{opts.model_name}"
            ) or self.request.user.has_perm(f"{opts.app_label}.change_{opts.model_name}")
        return super().has_permission()

    def get_context_data(self, **kwargs):
        """Disponibiliza a configuração do catálogo para todos os templates."""
        context = super().get_context_data(**kwargs)
        context.update(
            catalog=self.catalog,
            catalog_key=self.catalog_key,
            list_url_name=self.catalog["list_url_name"],
        )
        return context


class CatalogListView(CatalogMixin, SearchableListMixin, ListView):
    """Renderiza qualquer catálogo configurado como uma tabela pesquisável."""
    action = "view"
    template_name = "management/catalog_list.html"
    context_object_name = "objects"
    paginate_by = 20

    def get_queryset(self):
        """Aplica busca e carrega relacionamentos usados nas colunas da tabela."""
        self.search_fields = self.catalog["search_fields"]
        queryset = super().get_queryset()
        if self.catalog.get("select_related"):
            queryset = queryset.select_related(*self.catalog["select_related"])
        return queryset

    def get_context_data(self, **kwargs):
        """Transforma os registros nas linhas da tabela e calcula as ações permitidas."""
        context = super().get_context_data(**kwargs)
        context["table_columns"] = [label for label, _ in self.catalog["columns"]]
        context["table_rows"] = [
            {
                "object": registro,
                "cells": [
                    resolve_attr(registro, caminho_atributo)
                    for _, caminho_atributo in self.catalog["columns"]
                ],
            }
            for registro in context["objects"]
        ]
        opts = self.model._meta
        context.update(
            can_add=self.catalog.get("allow_add", True) and self.request.user.has_perm(f"{opts.app_label}.add_{opts.model_name}"),
            can_change=self.request.user.has_perm(f"{opts.app_label}.change_{opts.model_name}"),
            can_delete=self.request.user.has_perm(f"{opts.app_label}.delete_{opts.model_name}"),
        )
        return context


class CatalogFormMixin(CatalogMixin):
    """Cria formulários de catálogo e aplica os estilos comuns do projeto."""
    template_name = "management/catalog_form.html"

    def get_form_class(self):
        """Cria o ModelForm a partir dos campos declarados no catálogo."""
        return modelform_factory(self.model, fields=self.catalog["fields"])

    def get_form(self, form_class=None):
        """Ajusta widgets e protege o identificador imutável de escolas."""
        form = super().get_form(form_class)
        for field in form.fields.values():
            widget = field.widget
            css_class = bootstrap_widget_class(widget)
            widget.attrs["class"] = f'{widget.attrs.get("class", "")} {css_class}'.strip()
        if "data_nascimento" in form.fields:
            form.fields["data_nascimento"].widget.input_type = "date"
        if "data" in form.fields:
            form.fields["data"].widget.input_type = "date"
        if self.model is Escola and self.object and self.object.pk:
            form.fields["id_escola"].disabled = True
        return form

    def get_success_url(self):
        """Retorna à lista do mesmo catálogo depois de salvar."""
        return reverse(self.catalog["list_url_name"])

    def can_manage_room_schedules(self):
        """Indica se o formulário de sala também pode editar suas programações."""
        return self.model is Sala and self.request.user.has_perms(
            (
                "core.add_programacaosala",
                "core.change_programacaosala",
                "core.delete_programacaosala",
            )
        )

    def get_room_schedule_formset(self):
        """Monta o formset de programações associado à sala atual."""
        kwargs = {
            "instance": self.object if self.object is not None else Sala(),
            "prefix": "programacoes",
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update(data=self.request.POST, files=self.request.FILES)
        return SalaProgramacaoFormSet(**kwargs)

    def get_context_data(self, **kwargs):
        """Inclui as programações somente quando o usuário tem todas as permissões."""
        context = super().get_context_data(**kwargs)
        context["can_manage_room_schedules"] = self.can_manage_room_schedules()
        if context["can_manage_room_schedules"]:
            context["programacao_formset"] = kwargs.get(
                "programacao_formset"
            ) or self.get_room_schedule_formset()
        return context

    def form_valid(self, form):
        """Salva sala e programações na mesma transação quando aplicável."""
        if self.can_manage_room_schedules():
            formset = self.get_room_schedule_formset()
            if not formset.is_valid():
                return self.render_to_response(
                    self.get_context_data(form=form, programacao_formset=formset)
                )
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
            messages.success(
                self.request,
                f"{self.catalog['singular'].capitalize()} e programações salvas com sucesso.",
            )
            return HttpResponseRedirect(self.get_success_url())
        messages.success(self.request, f"{self.catalog['singular'].capitalize()} salvo(a) com sucesso.")
        return super().form_valid(form)


class CatalogCreateView(CatalogFormMixin, CreateView):
    """Cria registros nos catálogos que permitem inclusão manual."""
    action = "add"

    def dispatch(self, request, *args, **kwargs):
        """Bloqueia inclusão nos catálogos definidos apenas para consulta."""
        if not self.catalog.get("allow_add", True):
            raise Http404("Inclusão indisponível para este cadastro.")
        return super().dispatch(request, *args, **kwargs)


class CatalogUpdateView(CatalogFormMixin, UpdateView):
    """Edita um registro do catálogo selecionado."""
    action = "change"


class CatalogDeleteView(CatalogMixin, DeleteView):
    """Exclui registros não protegidos por relacionamentos do domínio."""
    action = "delete"
    template_name = "management/confirm_delete.html"

    def get_success_url(self):
        """Retorna à lista depois da exclusão."""
        return reverse(self.catalog["list_url_name"])

    def get_context_data(self, **kwargs):
        """Informa ao template o nome do registro e o destino de cancelamento."""
        context = super().get_context_data(**kwargs)
        context.update(object_label=self.catalog["singular"], cancel_url_name=self.catalog["list_url_name"])
        return context

    def form_valid(self, form):
        """Converte vínculos protegidos em uma mensagem compreensível ao usuário."""
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f"Não foi possível excluir: este(a) {self.catalog['singular']} está em uso.")
            return HttpResponseRedirect(self.get_success_url())
        messages.success(self.request, f"{self.catalog['singular'].capitalize()} excluído(a) com sucesso.")
        return response

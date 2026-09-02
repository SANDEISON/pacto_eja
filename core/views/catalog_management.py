from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..models import Cidade, CorRaca, CursoCertificado, Educador, EducadorGenero, Escola, Estado, Modalidade, Nivel, Situacao
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
}


def resolve_attr(obj, accessor):
    value = obj
    for part in accessor.split("__"):
        value = getattr(value, part, None)
        if value is None:
            return "—"
    return value if value not in (None, "") else "—"


class CatalogMixin(ManagementPermissionMixin):
    catalog_key = None
    action = "view"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.catalog_key = self.catalog_key or kwargs.get("catalog_key")
        try:
            self.catalog = CATALOGS[self.catalog_key]
        except KeyError as error:
            raise Http404("Cadastro administrativo não encontrado.") from error
        self.model = self.catalog["model"]

    def get_permission_required(self):
        return (f"{self.model._meta.app_label}.{self.action}_{self.model._meta.model_name}",)

    def has_permission(self):
        if self.action == "view":
            opts = self.model._meta
            return self.request.user.has_perm(
                f"{opts.app_label}.view_{opts.model_name}"
            ) or self.request.user.has_perm(f"{opts.app_label}.change_{opts.model_name}")
        return super().has_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            catalog=self.catalog,
            catalog_key=self.catalog_key,
            list_url_name=self.catalog["list_url_name"],
        )
        return context


class CatalogListView(CatalogMixin, SearchableListMixin, ListView):
    action = "view"
    template_name = "management/catalog_list.html"
    context_object_name = "objects"
    paginate_by = 20

    def get_queryset(self):
        self.search_fields = self.catalog["search_fields"]
        queryset = super().get_queryset()
        if self.catalog.get("select_related"):
            queryset = queryset.select_related(*self.catalog["select_related"])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["table_columns"] = [label for label, _ in self.catalog["columns"]]
        context["table_rows"] = [
            {"object": obj, "cells": [resolve_attr(obj, accessor) for _, accessor in self.catalog["columns"]]}
            for obj in context["objects"]
        ]
        opts = self.model._meta
        context.update(
            can_add=self.catalog.get("allow_add", True) and self.request.user.has_perm(f"{opts.app_label}.add_{opts.model_name}"),
            can_change=self.request.user.has_perm(f"{opts.app_label}.change_{opts.model_name}"),
            can_delete=self.request.user.has_perm(f"{opts.app_label}.delete_{opts.model_name}"),
        )
        return context


class CatalogFormMixin(CatalogMixin):
    template_name = "management/catalog_form.html"

    def get_form_class(self):
        return modelform_factory(self.model, fields=self.catalog["fields"])

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            widget = field.widget
            css_class = "form-check-input" if widget.input_type == "checkbox" else "form-select" if widget.input_type == "select" else "form-control"
            widget.attrs["class"] = f'{widget.attrs.get("class", "")} {css_class}'.strip()
        if "data_nascimento" in form.fields:
            form.fields["data_nascimento"].widget.input_type = "date"
        if self.model is Escola and self.object and self.object.pk:
            form.fields["id_escola"].disabled = True
        return form

    def get_success_url(self):
        return reverse(self.catalog["list_url_name"])

    def form_valid(self, form):
        messages.success(self.request, f"{self.catalog['singular'].capitalize()} salvo(a) com sucesso.")
        return super().form_valid(form)


class CatalogCreateView(CatalogFormMixin, CreateView):
    action = "add"

    def dispatch(self, request, *args, **kwargs):
        if not self.catalog.get("allow_add", True):
            raise Http404("Inclusão indisponível para este cadastro.")
        return super().dispatch(request, *args, **kwargs)


class CatalogUpdateView(CatalogFormMixin, UpdateView):
    action = "change"


class CatalogDeleteView(CatalogMixin, DeleteView):
    action = "delete"
    template_name = "management/confirm_delete.html"

    def get_success_url(self):
        return reverse(self.catalog["list_url_name"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(object_label=self.catalog["singular"], cancel_url_name=self.catalog["list_url_name"])
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f"Não foi possível excluir: este(a) {self.catalog['singular']} está em uso.")
            return HttpResponseRedirect(self.get_success_url())
        messages.success(self.request, f"{self.catalog['singular'].capitalize()} excluído(a) com sucesso.")
        return response

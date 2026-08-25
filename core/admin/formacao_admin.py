from django.contrib import admin

from ..models import Formacao


@admin.register(Formacao)
class FormacaoAdmin(admin.ModelAdmin):
    list_display = (
        "educador",
        "nivel",
        "nome_curso",
        "instituicao",
        "situacao",
        "ano_conclusao",
    )
    search_fields = (
        "educador__nome_completo",
        "educador__nome_social",
        "nome_curso",
        "instituicao",
    )
    list_filter = ("nivel", "situacao", "modalidade")
    list_select_related = ("educador",)
    autocomplete_fields = ("educador",)

from django.contrib import admin

from ..models import Cidade


@admin.register(Cidade)
class CidadeAdmin(admin.ModelAdmin):
    list_display = ("nome_cidade", "estado")
    search_fields = ("nome_cidade", "estado__nome_estado", "estado__sigla")
    list_filter = ("estado",)
    list_select_related = ("estado",)
    ordering = ("nome_cidade",)

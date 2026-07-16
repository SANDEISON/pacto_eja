from django.contrib import admin

from ..models import Escola


@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ("id_escola", "nome", "id_municipio", "sigla_uf", "localizacao", "dependencia_administrativa")
    search_fields = ("=id_escola", "nome", "=id_municipio", "endereco")
    list_filter = ("sigla_uf", "localizacao", "categoria_administrativa", "dependencia_administrativa", "porte")
    ordering = ("nome",)
    readonly_fields = ("id_escola",)

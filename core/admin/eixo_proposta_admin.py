from django.contrib import admin

from ..models import EixoProposta


@admin.register(EixoProposta)
class EixoPropostaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "link_acesso")
    search_fields = ("nome", "descricao", "link_acesso")

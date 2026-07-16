from django.contrib import admin

from ..models import Estado


@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ("nome_estado", "sigla")
    search_fields = ("nome_estado", "sigla")
    ordering = ("nome_estado",)

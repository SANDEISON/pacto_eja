from django.contrib import admin

from ..models import CursoCertificado


@admin.register(CursoCertificado)
class CursoCertificadoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)
    ordering = ("id",)

from django.contrib import admin

from ..models import CorRaca


@admin.register(CorRaca)
class CorRacaAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)

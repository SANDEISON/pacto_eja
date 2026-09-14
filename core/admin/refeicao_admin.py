from django.contrib import admin

from ..models import Refeicao


@admin.register(Refeicao)
class RefeicaoAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo", "data", "horario", "atividade")
    list_filter = ("tipo", "data")
    search_fields = ("atividade__titulo",)
    ordering = ("data", "horario", "tipo")

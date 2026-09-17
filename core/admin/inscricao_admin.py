from django.contrib import admin

from ..models import Inscricao


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "atividade", "modalidade", "inscrito_em")
    list_filter = ("modalidade", "atividade", "inscrito_em")
    search_fields = (
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "usuario__email",
        "atividade__titulo",
    )
    list_select_related = ("usuario", "atividade")
    filter_horizontal = ("refeicoes", "programacoes")
    readonly_fields = ("inscrito_em",)

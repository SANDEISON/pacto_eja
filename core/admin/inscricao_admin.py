from django.contrib import admin

from ..models import Inscricao


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "atividade", "modalidade", "vai_apresentar_trabalho", "inscrito_em")
    list_filter = (
        "vai_apresentar_trabalho",
        "modalidade",
        "atividade",
        "programacoes__sala",
        "programacoes",
        "inscrito_em",
    )
    search_fields = (
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "usuario__email",
        "atividade__titulo",
    )
    list_select_related = ("usuario", "atividade")
    filter_horizontal = ("refeicoes", "programacoes")
    readonly_fields = ("inscrito_em", "vai_apresentar_trabalho", "apresentacao_indicada_por", "apresentacao_indicada_em")

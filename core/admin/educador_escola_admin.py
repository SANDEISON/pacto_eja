from django.contrib import admin

from ..models import EducadorEscola


@admin.register(EducadorEscola)
class EducadorEscolaAdmin(admin.ModelAdmin):
    list_display = (
        "educador",
        "estado",
        "cidade",
        "escola",
        "funcao_caracterizacao_turmas",
        "tempo_atuacao",
        "criado_em",
    )
    search_fields = (
        "funcao_educador__educador__cpf",
        "funcao_educador__educador__nome_completo",
        "funcao_educador__educador__usuario__email",
        "escola__nome",
    )
    list_filter = ("cidade__estado", "funcao_caracterizacao_turmas", "tempo_atuacao", "criado_em")
    list_select_related = ("funcao_educador__educador__usuario", "cidade__estado", "escola", "funcao", "funcao_caracterizacao_turmas")
    autocomplete_fields = ("cidade", "escola")
    readonly_fields = ("criado_em",)

    @admin.display(description="estado", ordering="cidade__estado__sigla")
    def estado(self, obj):
        return obj.cidade.estado

    @admin.display(description="educador", ordering="funcao_educador__educador__nome_completo")
    def educador(self, obj):
        return obj.funcao_educador.educador

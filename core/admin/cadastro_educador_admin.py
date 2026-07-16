from django.contrib import admin

from ..models import CadastroEducador


@admin.register(CadastroEducador)
class CadastroEducadorAdmin(admin.ModelAdmin):
    list_display = (
        "id_pessoa",
        "estado",
        "cidade",
        "escola",
        "funcao_caracterizacao_turmas",
        "criado_em",
    )
    search_fields = (
        "id_pessoa__cpf",
        "id_pessoa__usuario__first_name",
        "id_pessoa__usuario__email",
        "escola__nome",
    )
    list_filter = ("estado", "funcao_caracterizacao_turmas", "criado_em")
    list_select_related = ("id_pessoa__usuario", "estado", "cidade", "escola")
    autocomplete_fields = ("id_pessoa", "cidade", "escola")
    readonly_fields = ("criado_em",)

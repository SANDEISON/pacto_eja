from django.contrib import admin

from ..models import FuncaoEducador


@admin.register(FuncaoEducador)
class FuncaoEducadorAdmin(admin.ModelAdmin):
    list_display = ("educador", "educador_escola", "funcao_caracterizacao_turmas")
    search_fields = (
        "educador__cpf",
        "educador__nome_completo",
        "educador__usuario__email",
        "educador_escola__escola__nome",
    )
    list_filter = ("educador_escola__funcao_caracterizacao_turmas",)
    list_select_related = ("educador__usuario", "educador_escola__escola", "educador_escola__funcao_caracterizacao_turmas")
    autocomplete_fields = ("educador", "educador_escola")

    @admin.display(
        description="função e caracterização",
        ordering="educador_escola__funcao_caracterizacao_turmas",
    )
    def funcao_caracterizacao_turmas(self, obj):
        return obj.educador_escola.funcao_caracterizacao_turmas

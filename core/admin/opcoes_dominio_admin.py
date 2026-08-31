from django.contrib import admin

from ..models import (
    EducadorEstadoCivil,
    EducadorGenero,
    Funcao,
    FuncaoCaracterizacaoTurma,
    Modalidade,
    Nivel,
    Situacao,
)


class OpcaoDominioAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "codigo")
    search_fields = ("nome", "codigo")
    ordering = ("id",)


admin.site.register(Nivel, OpcaoDominioAdmin)
admin.site.register(Situacao, OpcaoDominioAdmin)
admin.site.register(Modalidade, OpcaoDominioAdmin)
admin.site.register(FuncaoCaracterizacaoTurma, OpcaoDominioAdmin)
admin.site.register(EducadorGenero, OpcaoDominioAdmin)
admin.site.register(EducadorEstadoCivil, OpcaoDominioAdmin)
admin.site.register(Funcao, OpcaoDominioAdmin)

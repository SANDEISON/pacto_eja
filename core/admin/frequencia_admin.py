from django.contrib import admin
from ..models import Frequencia, ChamadaFrequencia


@admin.register(Frequencia)
class FrequenciaAdmin(admin.ModelAdmin):
    list_display = ("inscricao", "programacao", "registrada_em", "metodo", "registrada_por")
    list_filter = ("programacao", "metodo")
    search_fields = ("inscricao__usuario__first_name", "inscricao__usuario__email")
    readonly_fields = ("inscricao", "programacao", "chamada", "registrada_em", "metodo", "registrada_por")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChamadaFrequencia)
class ChamadaFrequenciaAdmin(admin.ModelAdmin):
    list_display = ("atividade", "programacao", "aberta_em", "expira_em", "encerrada_em", "responsavel")
    readonly_fields = ("atividade", "programacao", "aberta_em", "expira_em", "encerrada_em", "responsavel", "codigo")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

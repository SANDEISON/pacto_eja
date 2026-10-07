from django.contrib import admin

from ..models import EnvioCadastroEducador


@admin.register(EnvioCadastroEducador)
class EnvioCadastroEducadorAdmin(admin.ModelAdmin):
    list_display = ("numero", "educador", "usuario", "operacao", "concluido_em", "data_referencia", "total_atuacoes")
    list_filter = ("operacao", "concluido_em", "data_referencia")
    search_fields = ("=numero", "=id", "educador__nome_completo", "educador__cpf", "educador__usuario__username")
    list_select_related = ("educador__usuario",)
    readonly_fields = ("numero", "id", "educador", "operacao", "concluido_em", "data_referencia", "total_atuacoes")
    ordering = ("-data_referencia", "-concluido_em")
    date_hierarchy = "concluido_em"

    @admin.display(description="Usuário", ordering="educador__usuario_id")
    def usuario(self, obj):
        return obj.educador.usuario_id

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

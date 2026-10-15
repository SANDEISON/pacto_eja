from django.contrib import admin

from ..models import Educador


@admin.register(Educador)
class EducadorAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "nome_social", "usuario", "cpf", "telefone", "data_nascimento", "genero", "estado_civil", "undime_confirmada", "undime_confirmado_por", "undime_confirmado_em")
    search_fields = ("nome_completo", "nome_social", "usuario__username", "usuario__first_name", "usuario__last_name", "usuario__email", "cpf", "telefone", "genero__nome", "estado_civil__nome")
    list_filter = ("genero", "estado_civil", "representante_estado_undime_consed", "undime_confirmada", ("undime_confirmado_em", admin.EmptyFieldListFilter))
    list_select_related = ("usuario", "genero", "estado_civil", "undime_confirmado_por")
    autocomplete_fields = ("usuario",)
    readonly_fields = ("undime_confirmada", "undime_confirmado_por", "undime_confirmado_em")

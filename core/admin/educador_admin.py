from django.contrib import admin

from ..models import Educador


@admin.register(Educador)
class EducadorAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "usuario", "cpf", "telefone", "data_nascimento", "genero", "estado_civil")
    search_fields = ("nome_completo", "usuario__username", "usuario__first_name", "usuario__last_name", "usuario__email", "cpf", "telefone")
    list_filter = ("genero", "estado_civil")
    autocomplete_fields = ("usuario",)

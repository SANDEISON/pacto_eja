from django.contrib import admin

from ..models import Pessoa


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "cpf", "telefone", "data_nascimento", "genero", "estado_civil")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name", "usuario__email", "cpf", "telefone")
    list_filter = ("genero", "estado_civil")
    autocomplete_fields = ("usuario",)

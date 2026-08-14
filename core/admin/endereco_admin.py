from django.contrib import admin

from ..models import Endereco


@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    list_display = ("educador", "logradouro", "numero", "bairro", "cidade", "uf", "cep")
    search_fields = (
        "educador__nome_completo",
        "educador__nome_social",
        "cep",
        "logradouro",
        "bairro",
        "cidade__nome_cidade",
    )
    list_filter = ("cidade__estado",)
    list_select_related = ("educador", "cidade__estado")
    autocomplete_fields = ("educador", "cidade")

    @admin.display(description="UF", ordering="cidade__estado__sigla")
    def uf(self, obj):
        return obj.uf

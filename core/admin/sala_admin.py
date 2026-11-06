from django.contrib import admin

from ..models import ProgramacaoSala, Sala, TematicaSala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)


@admin.register(ProgramacaoSala)
class ProgramacaoSalaAdmin(admin.ModelAdmin):
    class Media:
        js = ("js/programacao_sala_modalidade.js",)

    list_display = (
        "id",
        "sala",
        "data",
        "turno",
        "modalidade",
        "link",
        "responsavel",
        "mediador",
        "tematica",
        "publica",
        "quantidade_max_participantes",
    )
    list_filter = ("turno", "modalidade", "data", "tematica", "publica")
    search_fields = ("sala__nome", "tematica__nome", "mediador", "descricao")


@admin.register(TematicaSala)
class TematicaSalaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "mediador")
    search_fields = (
        "nome",
        "mediador__username",
        "mediador__email",
        "mediador__first_name",
        "mediador__last_name",
    )

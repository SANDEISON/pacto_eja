from django.contrib import admin

from ..models import ProgramacaoSala, Sala, TematicaSala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)


@admin.register(ProgramacaoSala)
class ProgramacaoSalaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sala",
        "data",
        "turno",
        "modalidade",
        "link",
        "tematica",
        "quantidade_max_participantes",
    )
    list_filter = ("turno", "modalidade", "data", "tematica")
    search_fields = ("sala__nome", "tematica__nome", "descricao")


@admin.register(TematicaSala)
class TematicaSalaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "mediador")
    search_fields = ("nome", "mediador")

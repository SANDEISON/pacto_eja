from django.contrib import admin

from ..models import Atividade


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "tipo",
        "modalidade",
        "data_inicio",
        "inscricoes_fim",
        "vagas",
        "vagas_online",
        "ativo",
    )
    list_filter = ("ativo", "tipo", "modalidade", "permite_submissao")
    search_fields = ("titulo", "descricao", "endereco", "local", "link")
    date_hierarchy = "data_inicio"
    filter_horizontal = ("programacoes",)
    readonly_fields = ("vagas", "vagas_online", "criado_em", "atualizado_em")

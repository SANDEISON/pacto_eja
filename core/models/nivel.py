from .opcao_dominio import OpcaoDominio


class Nivel(OpcaoDominio):
    class Meta(OpcaoDominio.Meta):
        db_table = "core_nivel"
        verbose_name = "nível de formação"
        verbose_name_plural = "níveis de formação"

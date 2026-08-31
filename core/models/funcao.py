from .opcao_dominio import OpcaoDominio


class Funcao(OpcaoDominio):
    class Meta(OpcaoDominio.Meta):
        db_table = "core_funcao"
        verbose_name = "função"
        verbose_name_plural = "funções"

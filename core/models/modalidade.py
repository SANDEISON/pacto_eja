from .opcao_dominio import OpcaoDominio


class Modalidade(OpcaoDominio):
    class Meta(OpcaoDominio.Meta):
        db_table = "core_modalidade"
        verbose_name = "modalidade da formação"
        verbose_name_plural = "modalidades das formações"

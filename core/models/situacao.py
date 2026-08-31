from .opcao_dominio import OpcaoDominio


class Situacao(OpcaoDominio):
    class Meta(OpcaoDominio.Meta):
        db_table = "core_situacao"
        verbose_name = "situação da formação"
        verbose_name_plural = "situações das formações"

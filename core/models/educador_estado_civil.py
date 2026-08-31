from .opcao_dominio import OpcaoDominio


class EducadorEstadoCivil(OpcaoDominio):
    class Meta(OpcaoDominio.Meta):
        db_table = "core_educador_estado_civil"
        verbose_name = "estado civil do educador"
        verbose_name_plural = "estados civis dos educadores"

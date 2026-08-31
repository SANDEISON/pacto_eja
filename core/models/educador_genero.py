from .opcao_dominio import OpcaoDominio


class EducadorGenero(OpcaoDominio):
    class Meta(OpcaoDominio.Meta):
        db_table = "core_educador_genero"
        verbose_name = "gênero do educador"
        verbose_name_plural = "gêneros dos educadores"

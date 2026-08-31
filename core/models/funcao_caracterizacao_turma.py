from .opcao_dominio import OpcaoDominio


class FuncaoCaracterizacaoTurma(OpcaoDominio):
    class Meta(OpcaoDominio.Meta):
        db_table = "core_funcao_caracterizacao_turma"
        verbose_name = "função e caracterização da turma"
        verbose_name_plural = "funções e caracterizações das turmas"

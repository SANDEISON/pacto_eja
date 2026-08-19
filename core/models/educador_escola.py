from django.db import models

from .cidade import Cidade
from .escola import Escola
from .funcao_caracterizacao_turma import FuncaoCaracterizacaoTurma


class EducadorEscola(models.Model):
    class Funcao(models.TextChoices):
        FORMADOR_PACTO_ANOS_INICIAIS = "formador_pacto_anos_iniciais", "Formador(a) do Pacto | Anos Iniciais"
        FORMADOR_PACTO_ANOS_FINAIS = "formador_pacto_anos_finais", "Formador(a) do Pacto | Anos Finais"
        FORMADOR_PACTO_ENSINO_MEDIO = "formador_pacto_ensino_medio", "Formador(a) do Pacto | Ensino Médio"
        PROFESSOR_PACTO_ANOS_INICIAIS = "professor_pacto_anos_iniciais", "Professor(a) do Pacto | Anos Iniciais"
        PROFESSOR_PACTO_ANOS_FINAIS = "professor_pacto_anos_finais", "Professor(a) do Pacto | Anos Finais"
        PROFESSOR_PACTO_ENSINO_MEDIO = "professor_pacto_ensino_medio", "Professor(a) do Pacto | Ensino Médio"
        COORDENADOR_PACTO_UNDIME = "coordenador_pacto_undime", "Coordenador(a) do Pacto - Undime"
        COORDENADOR_PACTO_CONSED = "coordenador_pacto_consed", "Coordenador(a) do Pacto - Consed"
        OUTRO_PROFISSIONAL_EDUCACAO_PACTO = (
            "outro_profissional_educacao_pacto",
            "Outro(a) profissional da Educação ligado(a) ao Pacto",
        )
        PROFISSIONAL_EDUCACAO_NAO_PACTO = (
            "profissional_educacao_nao_pacto",
            "Profissional da Educação NÃO ligado(a) ao Pacto",
        )
        ESTUDANTE_EJA_ANOS_INICIAIS = "estudante_eja_anos_iniciais", "Estudante da EJA | Anos Iniciais"
        ESTUDANTE_EJA_ANOS_FINAIS = "estudante_eja_anos_finais", "Estudante da EJA | Anos Finais"
        ESTUDANTE_EJA_ENSINO_MEDIO = "estudante_eja_ensino_medio", "Estudante da EJA | Ensino Médio"
        PUBLICO_GERAL = "publico_geral", "Público em geral"
        CONVIDADO_ESTRANGEIRO = "convidado_estrangeiro", "Convidado(a) estrangeiro(a)"
        OUTRO = "outro", "Outro"

    class TempoAtuacao(models.TextChoices):
        ZERO_A_TRES_ANOS = "0_3_anos", "0-3 anos"
        QUATRO_A_SEIS_ANOS = "4_6_anos", "4-6 anos"
        MAIS_DE_SEIS_ANOS = "mais_6_anos", "Mais de 6 anos"

    cidade = models.ForeignKey(
        Cidade,
        on_delete=models.PROTECT,
        related_name="vinculos_educador_escola",
        verbose_name="cidade de atuação",
    )
    escola = models.ForeignKey(
        Escola,
        on_delete=models.PROTECT,
        related_name="vinculos_educador_escola",
        verbose_name="escola",
    )
    funcao = models.CharField(
        "função",
        max_length=40,
        choices=Funcao.choices,
        blank=True,
        default="",
    )
    funcao_caracterizacao_turmas = models.CharField(
        "função e caracterização das turmas da EJA",
        max_length=30,
        choices=FuncaoCaracterizacaoTurma.choices,
    )
    tempo_atuacao = models.CharField(
        "tempo de atuação",
        max_length=11,
        choices=TempoAtuacao.choices,
        blank=True,
        default="",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        db_table = "core_educadorescola"
        verbose_name = "vínculo entre educador e escola"
        verbose_name_plural = "vínculos entre educadores e escolas"
        ordering = ("-criado_em",)

    def __str__(self):
        return f"{self.escola} — {self.get_funcao_caracterizacao_turmas_display()}"

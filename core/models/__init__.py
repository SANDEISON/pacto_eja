from .atividade import Atividade
from .avaliacao import Avaliacao, CandidaturaAvaliador, ChamadaAvaliadores, DesignacaoAvaliacao
from .cidade import Cidade
from .cor_raca import CorRaca
from .curso_certificado import CursoCertificado
from .educador import Educador
from .educador_escola import EducadorEscola
from .educador_estado_civil import EducadorEstadoCivil
from .educador_genero import EducadorGenero
from .endereco import Endereco
from .escola import Escola
from .estado import Estado
from .formacao import Formacao
from .funcao import Funcao
from .funcao_caracterizacao_turma import FuncaoCaracterizacaoTurma
from .funcao_educador import FuncaoEducador
from .inscricao import Inscricao
from .modalidade import Modalidade
from .nivel import Nivel
from .programacao_sala import ProgramacaoSala
from .rascunho_inscricao import RascunhoInscricao
from .refeicao import Refeicao
from .sala import Sala
from .situacao import Situacao
from .tematica_sala import TematicaSala
from .trabalho import EvidenciaTrabalho, Trabalho, TrabalhoMunicipio
from .coautor import Coautor

__all__ = [
    "Atividade",
    "Avaliacao",
    "CandidaturaAvaliador",
    "ChamadaAvaliadores",
    "Cidade",
    "CorRaca",
    "CursoCertificado",
    "Coautor",
    "DesignacaoAvaliacao",
    "Educador",
    "EducadorEscola",
    "EducadorEstadoCivil",
    "EducadorGenero",
    "EvidenciaTrabalho",
    "Endereco",
    "Escola",
    "Estado",
    "Formacao",
    "Funcao",
    "FuncaoCaracterizacaoTurma",
    "FuncaoEducador",
    "Modalidade",
    "Nivel",
    "Inscricao",
    "RascunhoInscricao",
    "Refeicao",
    "ProgramacaoSala",
    "Sala",
    "Situacao",
    "TematicaSala",
    "Trabalho",
    "TrabalhoMunicipio",
]

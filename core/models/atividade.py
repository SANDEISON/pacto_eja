import re
from urllib.parse import quote_plus

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Atividade(models.Model):
    """Evento, palestra ou curso que aceita inscrições de educadores."""
    class Tipo(models.TextChoices):
        EVENTO = "evento", "Evento"
        PALESTRA = "palestra", "Palestra"
        CURSO = "curso", "Curso"

    class ModalidadeParticipacao(models.TextChoices):
        ONLINE = "online", "On-line"
        PRESENCIAL = "presencial", "Presencial"
        AMBAS = "ambas", "On-line e presencial"

    class ModeloSubmissao(models.TextChoices):
        ACADEMICO = "academico", "Trabalho acadêmico"
        RELATO_EXPERIENCIA = "relato", "Relato de experiência"

    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices, default=Tipo.EVENTO)
    modalidade = models.CharField(
        "modalidade",
        max_length=10,
        choices=ModalidadeParticipacao.choices,
        default=ModalidadeParticipacao.PRESENCIAL,
    )
    titulo = models.CharField("título", max_length=180)
    descricao = models.TextField("descrição")
    local = models.CharField("local/endereço", max_length=255, blank=True)
    link = models.URLField("link do evento on-line", max_length=500, blank=True)
    data_inicio = models.DateTimeField("início")
    data_fim = models.DateTimeField("término")
    inscricoes_inicio = models.DateTimeField("início das inscrições", null=True, blank=True)
    inscricoes_fim = models.DateTimeField("fim das inscrições")
    vagas = models.PositiveIntegerField("número de vagas", null=True, blank=True)
    programacoes = models.ManyToManyField(
        "ProgramacaoSala",
        verbose_name="programações disponíveis",
        related_name="atividades",
        blank=True,
    )
    permite_submissao = models.BooleanField("permite submissão de trabalho", default=False)
    modelo_submissao = models.CharField(
        "modelo para cadastro do trabalho",
        max_length=12,
        choices=ModeloSubmissao.choices,
        default=ModeloSubmissao.ACADEMICO,
        help_text=(
            "O trabalho acadêmico solicita modalidade, eixo da proposta e apresentação. O relato de "
            "experiência solicita a caracterização e a proposta detalhada."
        ),
    )
    submissoes_fim = models.DateTimeField("fim das submissões", null=True, blank=True)
    ativo = models.BooleanField("ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_atividade"
        verbose_name = "atividade"
        verbose_name_plural = "atividades"
        ordering = ("data_inicio", "titulo")

    def __str__(self):
        return self.titulo

    def clean(self):
        """Valida a coerência entre local, datas de inscrição e submissão."""
        errors = {}
        if self.modalidade in (
            self.ModalidadeParticipacao.PRESENCIAL,
            self.ModalidadeParticipacao.AMBAS,
        ) and not self.local:
            errors["local"] = "Informe o endereço da atividade presencial."
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            errors["data_fim"] = "O término deve ocorrer depois do início."
        if self.inscricoes_inicio and self.inscricoes_fim and self.inscricoes_fim < self.inscricoes_inicio:
            errors["inscricoes_fim"] = "O fim das inscrições deve ocorrer depois do início."
        if self.inscricoes_fim and self.data_inicio and self.inscricoes_fim > self.data_inicio:
            errors["inscricoes_fim"] = "As inscrições devem terminar até o início da atividade."
        if self.permite_submissao and not self.submissoes_fim:
            errors["submissoes_fim"] = "Informe o prazo para submissão de trabalhos."
        if self.submissoes_fim and self.inscricoes_inicio and self.submissoes_fim < self.inscricoes_inicio:
            errors["submissoes_fim"] = "O prazo de submissão não pode terminar antes da abertura das inscrições."
        if errors:
            raise ValidationError(errors)

    @property
    def modalidades_disponiveis(self):
        """Retorna as modalidades que podem ser escolhidas na inscrição."""
        if self.modalidade == self.ModalidadeParticipacao.AMBAS:
            return (
                (self.ModalidadeParticipacao.ONLINE, self.ModalidadeParticipacao.ONLINE.label),
                (self.ModalidadeParticipacao.PRESENCIAL, self.ModalidadeParticipacao.PRESENCIAL.label),
            )
        modalidade = self.ModalidadeParticipacao(self.modalidade)
        return ((modalidade.value, modalidade.label),)

    def aceita_modalidade(self, modalidade):
        """Confere se a modalidade escolhida está habilitada para a atividade."""
        return modalidade in {valor for valor, _ in self.modalidades_disponiveis}

    @property
    def local_url(self):
        """Retorna um link informado no local ou monta uma busca pelo endereço."""
        link_informado = re.search(r"https?://[^\s]+", self.local or "", flags=re.IGNORECASE)
        if link_informado:
            return link_informado.group(0).rstrip(".,;)")
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(self.local or '')}"

    @property
    def local_texto(self):
        """Exibe uma chamada curta para links ou o endereço informado."""
        valor = self.local or ""
        link_informado = re.search(r"https?://[^\s]+", valor, flags=re.IGNORECASE)
        if link_informado:
            return "Abrir no Google Maps"
        return valor

    @property
    def periodo_inscricoes_aberto(self):
        """Indica se alterações em inscrições ainda são permitidas."""
        agora = timezone.now()
        return (
            self.ativo
            and (self.inscricoes_inicio is None or self.inscricoes_inicio <= agora)
            and self.inscricoes_fim >= agora
        )

    @property
    def inscricoes_abertas(self):
        """Indica se o período está aberto e ainda existem vagas."""
        return self.periodo_inscricoes_aberto and (
            self.vagas is None or self.inscricoes.count() < self.vagas
        )

    @property
    def submissoes_abertas(self):
        """Indica se a atividade aceita trabalhos neste momento."""
        agora = timezone.now()
        return bool(
            self.ativo
            and self.permite_submissao
            and self.submissoes_fim
            and self.submissoes_fim >= agora
            and (self.inscricoes_inicio is None or self.inscricoes_inicio <= agora)
        )

    @property
    def vagas_restantes(self):
        """Retorna o saldo de vagas ou ``None`` quando não há limite."""
        if self.vagas is None:
            return None
        return max(self.vagas - self.inscricoes.count(), 0)

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class ChamadaAvaliadores(models.Model):
    """Período em que uma atividade recebe candidaturas de avaliadores."""

    atividade = models.OneToOneField(
        "Atividade", on_delete=models.CASCADE, related_name="chamada_avaliadores", verbose_name="atividade"
    )
    titulo = models.CharField("título da chamada", max_length=180)
    descricao = models.TextField("apresentação da chamada")
    requisitos = models.TextField("requisitos para avaliação")
    inscricoes_inicio = models.DateTimeField("início das candidaturas")
    inscricoes_fim = models.DateTimeField("fim das candidaturas")
    avaliacoes_fim = models.DateTimeField("prazo final das avaliações")
    ativa = models.BooleanField("chamada publicada", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_chamada_avaliadores"
        verbose_name = "chamada de avaliadores"
        verbose_name_plural = "chamadas de avaliadores"
        ordering = ("inscricoes_inicio", "titulo")

    def __str__(self):
        return self.titulo

    def clean(self):
        """Valida a ordem dos prazos e a compatibilidade com a atividade."""
        errors = {}
        if self.inscricoes_fim and self.inscricoes_inicio and self.inscricoes_fim < self.inscricoes_inicio:
            errors["inscricoes_fim"] = "O encerramento deve ocorrer depois da abertura das candidaturas."
        if self.avaliacoes_fim and self.inscricoes_fim and self.avaliacoes_fim <= self.inscricoes_fim:
            errors["avaliacoes_fim"] = "O prazo de avaliação deve ser posterior às candidaturas."
        if self.atividade_id and not self.atividade.permite_submissao:
            errors["atividade"] = "A atividade selecionada precisa permitir submissão de trabalhos."
        if errors:
            raise ValidationError(errors)

    @property
    def candidaturas_abertas(self):
        """Informa se a chamada aceita novas candidaturas neste momento."""
        agora = timezone.now()
        return bool(self.ativa and self.inscricoes_inicio <= agora <= self.inscricoes_fim)


class CandidaturaAvaliador(models.Model):
    """Manifestação de interesse analisada pela coordenação da chamada."""

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADA = "aprovada", "Aprovada"
        REJEITADA = "rejeitada", "Não aprovada"

    chamada = models.ForeignKey(
        ChamadaAvaliadores, on_delete=models.CASCADE, related_name="candidaturas", verbose_name="chamada"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidaturas_avaliador", verbose_name="candidato"
    )
    area_atuacao = models.CharField("área de atuação", max_length=180)
    experiencia = models.TextField("experiência acadêmica ou profissional")
    temas_interesse = models.TextField("temas de interesse")
    conflitos_de_interesse = models.TextField(
        "possíveis conflitos de interesse",
        blank=True,
        help_text="Informe pessoas, instituições ou projetos que você não deve avaliar.",
    )
    status = models.CharField("status", max_length=12, choices=Status.choices, default=Status.PENDENTE)
    justificativa_decisao = models.TextField("observação da coordenação", blank=True)
    analisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidaturas_avaliadas",
        verbose_name="analisada por",
    )
    analisada_em = models.DateTimeField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_candidatura_avaliador"
        verbose_name = "candidatura de avaliador"
        verbose_name_plural = "candidaturas de avaliadores"
        ordering = ("-criada_em",)
        constraints = [
            models.UniqueConstraint(fields=("chamada", "usuario"), name="unique_candidatura_usuario_chamada")
        ]

    def __str__(self):
        return f"{self.usuario} — {self.chamada}"


class DesignacaoAvaliacao(models.Model):
    """Liberação explícita de um trabalho para um avaliador aprovado."""

    trabalho = models.ForeignKey(
        "Trabalho", on_delete=models.CASCADE, related_name="designacoes_avaliacao", verbose_name="trabalho"
    )
    avaliador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="designacoes_avaliacao",
        verbose_name="avaliador",
    )
    prazo = models.DateTimeField("prazo", null=True, blank=True)
    liberada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="designacoes_liberadas",
        verbose_name="liberada por",
    )
    liberada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_designacao_avaliacao"
        verbose_name = "designação de avaliação"
        verbose_name_plural = "designações de avaliação"
        ordering = ("prazo", "trabalho__titulo")
        constraints = [
            models.UniqueConstraint(fields=("trabalho", "avaliador"), name="unique_trabalho_avaliador")
        ]

    def __str__(self):
        return f"{self.trabalho} — {self.avaliador}"

    def clean(self):
        """Exige avaliador aprovado e impede avaliação do próprio trabalho."""
        errors = {}
        atividade = self.trabalho.inscricao.atividade
        candidatura_aprovada = CandidaturaAvaliador.objects.filter(
            chamada__atividade=atividade,
            usuario=self.avaliador,
            status=CandidaturaAvaliador.Status.APROVADA,
        ).exists()
        if not candidatura_aprovada:
            errors["avaliador"] = "Selecione um avaliador aprovado para esta atividade."
        autores_ids = {self.trabalho.inscricao.usuario_id}
        autores_ids.update(self.trabalho.coautores.values_list("usuario_id", flat=True))
        if self.avaliador_id in autores_ids:
            errors["avaliador"] = "Autores e coautores não podem avaliar o próprio trabalho."
        if errors:
            raise ValidationError(errors)

    @property
    def concluida(self):
        """Indica se a designação já possui um parecer concluído."""
        return hasattr(self, "avaliacao") and self.avaliacao.status == Avaliacao.Status.CONCLUIDA


class Avaliacao(models.Model):
    """Parecer acadêmico preenchido pelo avaliador designado."""

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        CONCLUIDA = "concluida", "Concluída"

    class Recomendacao(models.TextChoices):
        ACEITAR = "aceitar", "Aceitar"
        ACEITAR_AJUSTES = "ajustes", "Aceitar com ajustes"
        REJEITAR = "rejeitar", "Não aceitar"

    designacao = models.OneToOneField(
        DesignacaoAvaliacao, on_delete=models.CASCADE, related_name="avaliacao", verbose_name="designação"
    )
    nota_relevancia = models.PositiveSmallIntegerField("relevância", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    nota_metodologia = models.PositiveSmallIntegerField("metodologia", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    nota_clareza = models.PositiveSmallIntegerField("clareza", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    nota_contribuicao = models.PositiveSmallIntegerField("contribuição para a EJA", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    parecer = models.TextField("parecer para a coordenação", blank=True)
    observacoes_autor = models.TextField("orientações para os autores", blank=True)
    recomendacao = models.CharField("recomendação", max_length=12, choices=Recomendacao.choices, blank=True)
    status = models.CharField("status", max_length=10, choices=Status.choices, default=Status.RASCUNHO)
    atualizada_em = models.DateTimeField(auto_now=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_avaliacao"
        verbose_name = "avaliação"
        verbose_name_plural = "avaliações"

    def __str__(self):
        return f"Avaliação de {self.designacao.trabalho}"

    @property
    def media(self):
        """Calcula a média apenas quando os quatro critérios foram avaliados."""
        notas = (self.nota_relevancia, self.nota_metodologia, self.nota_clareza, self.nota_contribuicao)
        return sum(notas) / len(notas) if all(notas) else None

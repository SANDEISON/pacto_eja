from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Atividade(models.Model):
    """Evento, palestra ou curso que aceita inscrições de educadores."""
    class Tipo(models.TextChoices):
        EVENTO = "evento", "Evento"
        PALESTRA = "palestra", "Palestra"
        CURSO = "curso", "Curso"

    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices, default=Tipo.EVENTO)
    titulo = models.CharField("título", max_length=180)
    descricao = models.TextField("descrição")
    local = models.CharField("local/endereço", max_length=255, blank=True)
    link = models.URLField("link do evento on-line", max_length=500, blank=True)
    data_inicio = models.DateTimeField("início")
    data_fim = models.DateTimeField("término")
    inscricoes_inicio = models.DateTimeField("início das inscrições", null=True, blank=True)
    inscricoes_fim = models.DateTimeField("fim das inscrições")
    vagas = models.PositiveIntegerField("número de vagas", null=True, blank=True)
    permite_submissao = models.BooleanField("permite submissão de trabalho", default=False)
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
        if not self.local and not self.link:
            errors["local"] = "Informe o endereço ou o link on-line da atividade."
            errors["link"] = "Informe o endereço ou o link on-line da atividade."
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
    def inscricoes_abertas(self):
        """Indica se o período está aberto e ainda existem vagas."""
        agora = timezone.now()
        dentro_do_periodo = (
            self.ativo
            and (self.inscricoes_inicio is None or self.inscricoes_inicio <= agora)
            and self.inscricoes_fim >= agora
        )
        return dentro_do_periodo and (self.vagas is None or self.inscricoes.count() < self.vagas)

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

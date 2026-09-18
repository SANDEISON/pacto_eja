from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models

from .inscricao import trabalho_upload_path, validate_pdf_size


class Trabalho(models.Model):
    """Trabalho submetido com PDF e metadados estruturados para avaliação."""

    class ModalidadeApresentacao(models.TextChoices):
        ONLINE = "online", "On-line"
        PRESENCIAL = "presencial", "Presencial"

    class AutorizacaoImagens(models.TextChoices):
        COM_IMAGENS = "com", "Autorizo publicação com uso das imagens"
        SEM_IMAGENS = "sem", "Autorizo publicação sem o uso das imagens"

    VERSAO_ATUAL_TERMOS = "2026-01"
    inscricao = models.OneToOneField(
        "Inscricao", on_delete=models.CASCADE, related_name="trabalho", verbose_name="inscrição"
    )
    titulo = models.CharField("Título da proposta/prática", max_length=200)
    modalidade_apresentacao = models.CharField(
        "Apresentação do trabalho",
        max_length=10,
        choices=ModalidadeApresentacao.choices,
        blank=True,
    )
    eixo_proposta = models.ForeignKey(
        "EixoProposta",
        on_delete=models.PROTECT,
        related_name="trabalhos",
        verbose_name="Eixo da proposta",
        null=True,
        blank=True,
    )
    resumo = models.TextField(
        "Apresentação",
        blank=True,
        max_length=1100,
    )

    apresentacao = models.TextField(
        "Apresentação",
        blank=True,
        max_length=1100,
    )
    periodo_inicio = models.DateField("Data de início (dia/mês/ano)", null=True, blank=True)
    periodo_fim = models.DateField("Data de término (dia/mês/ano)", null=True, blank=True)
    turnos = models.JSONField("Turno", default=list, blank=True)
    duracao = models.CharField("Duração", max_length=100, blank=True)
    carga_horaria = models.PositiveIntegerField(
        "Carga horária (em horas)", null=True, blank=True, validators=[MinValueValidator(1)]
    )
    estado = models.ForeignKey(
        "Estado",
        on_delete=models.PROTECT,
        related_name="trabalhos",
        verbose_name="estado da experiência",
        null=True,
        blank=True,
    )
    n_participantes = models.PositiveIntegerField(
        "total de participantes", default=0
    )
    caracterizacao_publico = models.TextField(
        "Caracterização do Público", max_length=500, blank=True
    )
    objetivo_geral = models.TextField("Objetivo Geral", max_length=300, blank=True)
    objetivos_especificos = models.TextField(
        "Objetivos Específicos", max_length=500, blank=True
    )
    desenvolvimento_metodologico = models.TextField(
        "Desenvolvimento metodológico da ação de ensino", max_length=6000, blank=True
    )
    consideracoes = models.TextField(
        "Considerações e avaliação do processo", max_length=2000, blank=True
    )
    referencias = models.TextField("Referências", max_length=1000, blank=True)

    autorizacao_imagens = models.CharField(
        "uso de imagens na publicação",
        max_length=3,
        choices=AutorizacaoImagens.choices,
        blank=True,
    )
    aceitou_termo_imagem = models.BooleanField(
        "li e aceito o Termo de Uso de Imagem", default=False
    )
    aceitou_termo_relato = models.BooleanField(
        "Declaro CIÊNCIA e CONCORDÂNCIA com os 3 (três) termos acima, sobre uso de imagem, cessão de direitos autorais e declaração de originalidade.",
        default=False,
    )
    aceitou_termo_cessao = models.BooleanField(
        "li e aceito o Termo de Cessão de Direitos Autorais", default=False
    )
    aceitou_originalidade = models.BooleanField(
        "Declaro a originalidade da atividade", default=False
    )
    deseja_participar_publicacao = models.BooleanField(
        "tenho interesse em participar da publicação", default=False
    )
    versao_termos = models.CharField(max_length=20, blank=True)
    termos_aceitos_em = models.DateTimeField(null=True, blank=True)
    arquivo = models.FileField(
        "arquivo em PDF",
        upload_to=trabalho_upload_path,
        validators=[FileExtensionValidator(("pdf",), "Envie um arquivo no formato PDF."), validate_pdf_size],
    )
    submetido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_trabalho"
        verbose_name = "trabalho"
        verbose_name_plural = "trabalhos"
        ordering = ("-submetido_em",)

    def __str__(self):
        """Usa o título como identificação do trabalho na administração."""
        return self.titulo


class TrabalhoMunicipio(models.Model):
    """Município alcançado por um relato e sua quantidade de participantes."""

    trabalho = models.ForeignKey(
        Trabalho, on_delete=models.CASCADE, related_name="municipios", verbose_name="trabalho"
    )
    cidade = models.ForeignKey(
        "Cidade", on_delete=models.PROTECT, related_name="trabalhos", verbose_name="município"
    )
    participantes = models.PositiveIntegerField(
        "participantes", validators=[MinValueValidator(1)]
    )

    class Meta:
        db_table = "core_trabalho_municipio"
        verbose_name = "município do trabalho"
        verbose_name_plural = "municípios do trabalho"
        ordering = ("cidade__nome_cidade",)
        constraints = [
            models.UniqueConstraint(
                fields=("trabalho", "cidade"), name="unique_municipio_por_trabalho"
            )
        ]

    def __str__(self):
        """Resume o município e o público alcançado pelo relato."""
        return f"{self.cidade}: {self.participantes}"


TAMANHO_MAXIMO_EVIDENCIA = 10 * 1024 * 1024


def validate_evidencia_size(arquivo):
    """Limita cada evidência a 10 MB antes de armazená-la."""
    if arquivo.size > TAMANHO_MAXIMO_EVIDENCIA:
        raise ValidationError("Cada imagem deve ter no máximo 10 MB.")


def evidencia_upload_path(evidencia, nome_arquivo):
    """Organiza evidências por atividade e usuário usando um nome não previsível."""
    extensao = Path(nome_arquivo).suffix.lower()
    trabalho = evidencia.trabalho
    return (
        f"trabalhos/atividade-{trabalho.inscricao.atividade_id}/"
        f"usuario-{trabalho.inscricao.usuario_id}/evidencias/{uuid4().hex}{extensao}"
    )


class EvidenciaTrabalho(models.Model):
    """Imagem que documenta a efetivação da ação apresentada no trabalho."""

    trabalho = models.ForeignKey(
        Trabalho, on_delete=models.CASCADE, related_name="evidencias", verbose_name="trabalho"
    )
    arquivo = models.FileField(
        "imagem",
        upload_to=evidencia_upload_path,
        validators=[
            FileExtensionValidator(("jpg", "jpeg", "png"), "Envie uma imagem JPG ou PNG."),
            validate_evidencia_size,
        ],
    )
    nome_original = models.CharField(max_length=255, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_evidencia_trabalho"
        verbose_name = "evidência do trabalho"
        verbose_name_plural = "evidências do trabalho"
        ordering = ("enviado_em",)

    def save(self, *args, **kwargs):
        """Preserva o nome enviado pelo usuário antes de gerar o caminho definitivo."""
        if self.arquivo and not self.nome_original:
            self.nome_original = Path(self.arquivo.name).name[:255]
        super().save(*args, **kwargs)

    def __str__(self):
        """Exibe o nome original quando ele estiver disponível."""
        return self.nome_original or Path(self.arquivo.name).name

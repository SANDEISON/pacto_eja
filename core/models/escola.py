from django.db import models


class Escola(models.Model):
    id_escola = models.BigIntegerField("ID da escola", primary_key=True)
    nome = models.CharField("nome", max_length=255, db_index=True)
    id_municipio = models.BigIntegerField("ID do município", db_index=True)
    sigla_uf = models.CharField("UF", max_length=2, db_index=True)
    restricao_atendimento = models.CharField("restrição de atendimento", max_length=100, blank=True)
    localizacao = models.CharField("localização", max_length=50, blank=True)
    localidade_diferenciada = models.CharField("localidade diferenciada", max_length=100, blank=True)
    categoria_administrativa = models.CharField("categoria administrativa", max_length=50, blank=True)
    endereco = models.TextField("endereço", blank=True)
    telefone = models.CharField("telefone", max_length=50, blank=True)
    dependencia_administrativa = models.CharField("dependência administrativa", max_length=50, blank=True)
    categoria_privada = models.CharField("categoria privada", max_length=100, blank=True)
    porte = models.CharField("porte", max_length=50, blank=True)
    etapas_modalidades_oferecidas = models.TextField("etapas e modalidades oferecidas", blank=True)
    latitude = models.DecimalField("latitude", max_digits=18, decimal_places=14, null=True, blank=True)
    longitude = models.DecimalField("longitude", max_digits=18, decimal_places=14, null=True, blank=True)

    class Meta:
        verbose_name = "escola"
        verbose_name_plural = "escolas"
        ordering = ("nome",)
        indexes = [models.Index(fields=("sigla_uf", "id_municipio"), name="escola_uf_municipio_idx")]

    def __str__(self):
        return self.nome

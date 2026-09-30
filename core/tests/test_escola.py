from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from ..models import Cidade, Escola


class EscolaModelTests(TestCase):
    def test_removed_fields_are_not_part_of_school_model(self):
        field_names = {field.name for field in Escola._meta.get_fields()}

        self.assertTrue({"latitude", "longitude", "porte"}.isdisjoint(field_names))

    def test_school_uses_source_identifier_as_primary_key(self):
        escola = Escola.objects.create(
            id_escola=27000001,
            nome="Escola Teste",
            id_municipio=2704302,
            sigla_uf="AL",
        )
        self.assertEqual(escola.pk, 27000001)
        self.assertEqual(str(escola), "Escola Teste")

    def test_every_city_with_ibge_code_has_an_other_school(self):
        cidades = Cidade.objects.filter(codigo_ibge__gt=0).select_related("estado")
        outras = Escola.objects.filter(nome="Outra").in_bulk()
        self.assertTrue(cidades.exists())
        for cidade in cidades:
            escola = outras[9_000_000_000 + cidade.codigo_ibge]
            self.assertEqual(escola.id_municipio, cidade.codigo_ibge)
            self.assertEqual(escola.sigla_uf, cidade.estado.sigla)

    def test_other_school_data_load_is_idempotent(self):
        migration = import_module("core.migrations.0039_escola_outra_por_municipio")
        total = Escola.objects.count()
        migration.criar_escolas_outra(apps, SimpleNamespace(connection=connection))
        self.assertEqual(Escola.objects.count(), total)

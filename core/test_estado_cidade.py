from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from .models import Cidade, Estado


class EstadoCidadeModelTests(TestCase):
    def test_migration_populates_official_ibge_reference(self):
        self.assertEqual(Estado.objects.count(), 27)
        self.assertEqual(Cidade.objects.count(), 5571)
        self.assertTrue(
            Cidade.objects.filter(
                nome_cidade="Boa Esperança do Norte",
                estado__sigla="MT",
            ).exists()
        )

    def test_city_belongs_to_state_and_has_readable_name(self):
        estado = Estado.objects.get(sigla="AL")
        cidade = Cidade.objects.get(estado=estado, nome_cidade="Maceió")

        self.assertEqual(cidade.estado, estado)
        self.assertEqual(str(estado), "Alagoas (AL)")
        self.assertEqual(str(cidade), "Maceió - AL")

    def test_city_name_is_unique_inside_each_state(self):
        estado = Estado.objects.get(sigla="AL")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Cidade.objects.create(estado=estado, nome_cidade="Maceió")

    def test_state_with_cities_cannot_be_deleted(self):
        estado = Estado.objects.get(sigla="AL")

        with self.assertRaises(ProtectedError):
            estado.delete()

from django.test import TestCase

from .models import Escola


class EscolaModelTests(TestCase):
    def test_school_uses_source_identifier_as_primary_key(self):
        escola = Escola.objects.create(
            id_escola=27000001,
            nome="Escola Teste",
            id_municipio=2704302,
            sigla_uf="AL",
            latitude="-9.66580000000000",
            longitude="-35.73530000000000",
        )
        self.assertEqual(escola.pk, 27000001)
        self.assertEqual(str(escola), "Escola Teste")

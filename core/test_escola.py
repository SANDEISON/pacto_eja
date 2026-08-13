from django.test import TestCase

from .models import Escola


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

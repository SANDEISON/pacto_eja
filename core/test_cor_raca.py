from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import CorRaca, Educador


class CorRacaModelTests(TestCase):
    def test_migration_creates_initial_values(self):
        self.assertSetEqual(
            set(CorRaca.objects.values_list("nome", flat=True)),
            {"Preto", "Pardo", "Branco", "Indígena", "Amarelo"},
        )

    def test_educador_stores_cor_raca_id(self):
        cor_raca = CorRaca.objects.get(nome="Pardo")
        usuario = get_user_model().objects.create_user(username="educador-cor-raca")

        educador = Educador.objects.get(usuario=usuario)
        educador.cor_raca = cor_raca
        educador.save(update_fields=("cor_raca",))

        self.assertEqual(educador.cor_raca_id, cor_raca.pk)

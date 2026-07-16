from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Pessoa


User = get_user_model()


class PessoaModelTests(TestCase):
    def test_profile_is_created_with_user(self):
        user = User.objects.create_user(username="pessoa@example.com", email="pessoa@example.com", password="SenhaForte2026!")
        self.assertTrue(Pessoa.objects.filter(usuario=user).exists())


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="maria@example.com",
            email="maria@example.com",
            first_name="Maria",
            password="SenhaForte2026!",
        )
        self.client.force_login(self.user)

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("profile"))
        self.assertRedirects(response, f"{reverse('accounts:signin')}?next={reverse('profile')}")

    def test_user_can_update_account_and_personal_data(self):
        response = self.client.post(
            reverse("profile"),
            {
                "user-full_name": "Maria da Silva",
                "user-email": "maria.silva@example.com",
                "pessoa-cpf": "529.982.247-25",
                "pessoa-data_nascimento": "1990-05-12",
                "pessoa-genero": Pessoa.Genero.FEMININO,
                "pessoa-telefone": "(82) 99999-1234",
                "pessoa-estado_civil": Pessoa.EstadoCivil.CASADO,
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.user.pessoa.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Maria da Silva")
        self.assertEqual(self.user.email, "maria.silva@example.com")
        self.assertEqual(self.user.username, "maria.silva@example.com")
        self.assertEqual(self.user.pessoa.cpf, "52998224725")
        self.assertEqual(self.user.pessoa.data_nascimento, date(1990, 5, 12))

    def test_invalid_cpf_and_future_birth_date_are_rejected(self):
        response = self.client.post(
            reverse("profile"),
            {
                "user-full_name": "Maria",
                "user-email": "maria@example.com",
                "pessoa-cpf": "111.111.111-11",
                "pessoa-data_nascimento": (date.today() + timedelta(days=1)).isoformat(),
                "pessoa-genero": "",
                "pessoa-telefone": "",
                "pessoa-estado_civil": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe um CPF válido")
        self.assertContains(response, "não pode estar no futuro")

    def test_user_can_change_password_without_losing_session(self):
        response = self.client.post(
            reverse("profile_password_change"),
            {"old_password": "SenhaForte2026!", "new_password1": "NovaSenha2026!", "new_password2": "NovaSenha2026!"},
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaSenha2026!"))
        self.assertIn("_auth_user_id", self.client.session)

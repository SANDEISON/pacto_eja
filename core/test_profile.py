from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Educador, EducadorEscola, FuncaoEducador


User = get_user_model()


class EducadorModelTests(TestCase):
    def test_profile_is_created_with_user(self):
        user = User.objects.create_user(
            username="pessoa@example.com",
            email="pessoa@example.com",
            first_name="Maria",
            last_name="Educadora",
            password="SenhaForte2026!",
        )
        self.assertTrue(Educador.objects.filter(usuario=user).exists())
        self.assertEqual(user.educador.nome_completo, "Maria Educadora")

    def test_database_tables_use_educator_names(self):
        self.assertEqual(Educador._meta.db_table, "core_educador")
        self.assertEqual(EducadorEscola._meta.db_table, "core_educadorescola")
        self.assertEqual(FuncaoEducador._meta.db_table, "core_funcaoeducador")
        field_names = {field.name for field in EducadorEscola._meta.get_fields()}
        self.assertNotIn("estado", field_names)
        self.assertNotIn("educador", field_names)
        self.assertIn("funcao_educador", field_names)
        self.assertIn("funcao_caracterizacao_turmas", field_names)
        self.assertIn(
            "educador_escola",
            {field.name for field in FuncaoEducador._meta.get_fields()},
        )


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
                "educador-cpf": "529.982.247-25",
                "educador-data_nascimento": "1990-05-12",
                "educador-genero": Educador.Genero.FEMININO,
                "educador-telefone": "(82) 99999-1234",
                "educador-estado_civil": Educador.EstadoCivil.CASADO,
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.user.educador.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Maria da Silva")
        self.assertEqual(self.user.email, "maria.silva@example.com")
        self.assertEqual(self.user.username, "maria@example.com")
        self.assertEqual(self.user.educador.nome_completo, "Maria da Silva")
        self.assertEqual(self.user.educador.cpf, "52998224725")
        self.assertEqual(self.user.educador.data_nascimento, date(1990, 5, 12))

    def test_invalid_cpf_and_future_birth_date_are_rejected(self):
        response = self.client.post(
            reverse("profile"),
            {
                "user-full_name": "Maria",
                "user-email": "maria@example.com",
                "educador-cpf": "111.111.111-11",
                "educador-data_nascimento": (date.today() + timedelta(days=1)).isoformat(),
                "educador-genero": "",
                "educador-telefone": "",
                "educador-estado_civil": "",
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

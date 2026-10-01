from unittest.mock import patch

from django.core.cache import cache
from django.core import mail
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import CadastroPendente, Educador

from accounts.forms import SignUpForm


class AuthenticationTests(TestCase):
    def setUp(self):
        """Isola o limite de recuperação entre os testes."""
        cache.clear()

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('accounts:signin')}?next={reverse('dashboard')}")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_signup_creates_user_without_email_confirmation(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "full_name": "Maria da Silva",
                "cpf": "529.982.247-25",
                "email": "maria@example.com",
                "password1": "SenhaForte2026!",
                "password2": "SenhaForte2026!",
            },
        )
        self.assertRedirects(response, reverse("accounts:signin"))
        user = get_user_model().objects.get(username="52998224725")
        self.assertEqual(user.first_name, "Maria")
        self.assertEqual(user.last_name, "da Silva")
        self.assertEqual(user.email, "maria@example.com")
        self.assertEqual(user.educador.cpf, "52998224725")
        self.assertTrue(user.check_password("SenhaForte2026!"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(CadastroPendente.objects.exists())
        self.assertEqual(mail.outbox, [])
        login_response = self.client.post(
            reverse("accounts:signin"),
            {"username": "529.982.247-25", "password": "SenhaForte2026!"},
        )
        self.assertRedirects(login_response, reverse("dashboard"))

    def test_signup_succeeds_when_email_service_is_unavailable(self):
        with patch("accounts.views.send_mail", side_effect=OSError("SMTP indisponível")) as send_mail:
            response = self.client.post(
                reverse("accounts:signup"),
                {
                    "full_name": "Maria da Silva",
                    "cpf": "529.982.247-25",
                    "email": "maria@example.com",
                    "password1": "SenhaForte2026!",
                    "password2": "SenhaForte2026!",
                },
            )

        self.assertRedirects(response, reverse("accounts:signin"))
        send_mail.assert_not_called()
        self.assertTrue(get_user_model().objects.filter(username="52998224725").exists())
        self.assertFalse(CadastroPendente.objects.exists())

    def signup_data(self, **overrides):
        data = {
            "full_name": "Maria da Silva", "cpf": "529.982.247-25",
            "email": "maria@example.com", "password1": "SenhaForte2026!",
            "password2": "SenhaForte2026!",
        }
        data.update(overrides)
        return data

    def test_signup_defines_password_for_existing_account_without_login(self):
        user = get_user_model().objects.create_user(
            username="52998224725", email="maria@example.com", password="52998224725",
            first_name="Maria", last_name="da Silva",
        )
        educador = user.educador
        educador.cpf = "52998224725"
        educador.nome_completo = "Nome já registrado no perfil"
        educador.telefone = "83999999999"
        educador.save(update_fields=("cpf", "nome_completo", "telefone"))
        total_users = get_user_model().objects.count()
        total_profiles = Educador.objects.count()

        response = self.client.post(reverse("accounts:signup"), self.signup_data(), follow=True)

        self.assertRedirects(response, reverse("accounts:signin"))
        self.assertContains(response, "Sua senha foi definida e sua conta já pode ser acessada.")
        user.refresh_from_db()
        educador.refresh_from_db()
        self.assertTrue(user.check_password("SenhaForte2026!"))
        self.assertFalse(user.check_password("52998224725"))
        self.assertEqual(user.email, "maria@example.com")
        self.assertEqual(user.get_full_name(), "Maria da Silva")
        self.assertEqual(educador.nome_completo, "Nome já registrado no perfil")
        self.assertEqual(educador.telefone, "83999999999")
        self.assertEqual(get_user_model().objects.count(), total_users)
        self.assertEqual(Educador.objects.count(), total_profiles)
        self.assertIsNone(user.last_login)
        response = self.client.post(
            reverse("accounts:signin"), {"username": "529.982.247-25", "password": "SenhaForte2026!"},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_signup_preserves_existing_account_identity(self):
        user = get_user_model().objects.create_user(
            username="52998224725", email="maria@example.com", password="52998224725",
            first_name="Maria", last_name="da Silva",
        )
        response = self.client.post(
            reverse("accounts:signup"),
            self.signup_data(full_name="Outro Nome", email="novo@example.com"),
        )
        self.assertRedirects(response, reverse("accounts:signin"))
        user.refresh_from_db()
        self.assertEqual(user.email, "maria@example.com")
        self.assertEqual(user.get_full_name(), "Maria da Silva")
        self.assertTrue(user.check_password("SenhaForte2026!"))

    def test_signup_rejects_existing_account_after_first_login(self):
        user = get_user_model().objects.create_user(username="52998224725", password="SenhaAnterior2026!")
        user.last_login = timezone.now()
        user.save(update_fields=("last_login",))
        response = self.client.post(reverse("accounts:signup"), self.signup_data())
        self.assertEqual(response.status_code, 200)
        self.assertIn("cpf", response.context["form"].errors)
        user.refresh_from_db()
        self.assertTrue(user.check_password("SenhaAnterior2026!"))

    def test_signup_rechecks_first_login_before_saving_password(self):
        user = get_user_model().objects.create_user(username="52998224725", password="SenhaAnterior2026!")
        form = SignUpForm(self.signup_data())
        self.assertTrue(form.is_valid(), form.errors)
        get_user_model().objects.filter(pk=user.pk).update(last_login=timezone.now())
        with self.assertRaises(ValidationError):
            form.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password("SenhaAnterior2026!"))

    def test_signup_existing_account_requires_valid_matching_passwords(self):
        user = get_user_model().objects.create_user(username="52998224725", password="SenhaAnterior2026!")
        for overrides in ({"password2": "OutraSenha2026!"}, {"password1": "123", "password2": "123"}):
            with self.subTest(overrides=overrides):
                response = self.client.post(reverse("accounts:signup"), self.signup_data(**overrides))
                self.assertIn("password2", response.context["form"].errors)
                user.refresh_from_db()
                self.assertTrue(user.check_password("SenhaAnterior2026!"))

    def test_signup_existing_account_rejects_another_users_email(self):
        user = get_user_model().objects.create_user(username="52998224725", password="SenhaAnterior2026!")
        get_user_model().objects.create_user(username="outro", email="maria@example.com")
        response = self.client.post(reverse("accounts:signup"), self.signup_data())
        self.assertIn("email", response.context["form"].errors)
        user.refresh_from_db()
        self.assertTrue(user.check_password("SenhaAnterior2026!"))

    def test_signup_locates_existing_account_by_profile_cpf(self):
        user = get_user_model().objects.create_user(username="maria@example.com", email="maria@example.com")
        user.educador.cpf = "52998224725"
        user.educador.save(update_fields=("cpf",))
        response = self.client.post(reverse("accounts:signup"), self.signup_data())
        self.assertRedirects(response, reverse("accounts:signin"))
        user.refresh_from_db()
        self.assertEqual(user.username, "52998224725")
        self.assertTrue(user.check_password("SenhaForte2026!"))

    def test_signup_does_not_update_inactive_account(self):
        user = get_user_model().objects.create_user(
            username="52998224725", password="SenhaAnterior2026!", is_active=False,
        )
        response = self.client.post(reverse("accounts:signup"), self.signup_data())
        self.assertIn("cpf", response.context["form"].errors)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("SenhaAnterior2026!"))

    def test_user_can_sign_in_with_formatted_cpf(self):
        user = get_user_model().objects.create_user(
            username="52998224725",
            email="maria@example.com",
            password="SenhaForte2026!",
        )
        user.educador.cpf = "52998224725"
        user.educador.save(update_fields=("cpf",))

        response = self.client.post(
            reverse("accounts:signin"),
            {"username": "529.982.247-25", "password": "SenhaForte2026!"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def login_with_initial_password(self, **overrides):
        user = get_user_model().objects.create_user(username="52998224725", password="pactoeja2026")
        data = {"username": "529.982.247-25", "password": "pactoeja2026"}
        data.update(overrides)
        return user, self.client.post(reverse("accounts:signin"), data)

    def test_initial_password_login_requires_password_change_before_dashboard(self):
        user, response = self.login_with_initial_password(next=reverse("dashboard"))
        self.assertRedirects(response, reverse("accounts:change_initial_password"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertTrue(self.client.session["alteracao_senha_obrigatoria"])
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("accounts:change_initial_password"))
        page = self.client.get(reverse("accounts:change_initial_password"))
        self.assertContains(page, "Você está usando a senha inicial.")
        self.assertContains(page, 'name="new_password1"')
        self.assertContains(page, 'name="new_password2"')
        self.assertNotContains(page, 'name="old_password"')

    def test_required_password_change_rejects_invalid_passwords(self):
        user, _ = self.login_with_initial_password()
        cases = [
            ({"new_password1": "SenhaNova2026!", "new_password2": "OutraSenha2026!"}, "new_password2"),
            ({"new_password1": "123", "new_password2": "123"}, "new_password2"),
            ({"new_password1": "pactoeja2026", "new_password2": "pactoeja2026"}, "new_password1"),
        ]
        for data, field in cases:
            with self.subTest(data=data):
                response = self.client.post(reverse("accounts:change_initial_password"), data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertTrue(self.client.session["alteracao_senha_obrigatoria"])
                user.refresh_from_db()
                self.assertTrue(user.check_password("pactoeja2026"))

    def test_required_password_change_saves_password_and_preserves_session(self):
        user, _ = self.login_with_initial_password()
        response = self.client.post(
            reverse("accounts:change_initial_password"),
            {"new_password1": "SenhaNova2026!", "new_password2": "SenhaNova2026!"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("SenhaNova2026!"))
        self.assertFalse(user.check_password("pactoeja2026"))
        self.assertNotIn("alteracao_senha_obrigatoria", self.client.session)
        self.assertNotIn("destino_apos_alterar_senha", self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.client.post(reverse("accounts:logout"))
        response = self.client.post(
            reverse("accounts:signin"), {"username": "52998224725", "password": "SenhaNova2026!"},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_required_password_change_does_not_redirect_to_external_next(self):
        self.login_with_initial_password(next="https://example.com/")
        response = self.client.post(
            reverse("accounts:change_initial_password"),
            {"new_password1": "SenhaNova2026!", "new_password2": "SenhaNova2026!"},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_required_password_change_allows_logout(self):
        self.login_with_initial_password()
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("accounts:signin"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_required_password_change_requires_authenticated_session(self):
        url = reverse("accounts:change_initial_password")
        self.assertRedirects(self.client.get(url), f"{reverse('accounts:signin')}?next={url}")
        self.assertRedirects(
            self.client.post(url, {"new_password1": "SenhaNova2026!", "new_password2": "SenhaNova2026!"}),
            f"{reverse('accounts:signin')}?next={url}",
        )

    def test_initial_password_for_wrong_account_does_not_start_password_change(self):
        user = get_user_model().objects.create_user(username="52998224725", password="SenhaForte2026!")
        response = self.client.post(
            reverse("accounts:signin"), {"username": "52998224725", "password": "pactoeja2026"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn("alteracao_senha_obrigatoria", self.client.session)
        user.refresh_from_db()
        self.assertTrue(user.check_password("SenhaForte2026!"))

    def test_logout_only_accepts_post(self):
        user = get_user_model().objects.create_user(username="user@example.com", password="SenhaForte2026!")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("accounts:signin"))

    def test_signin_displays_password_recovery_link(self):
        response = self.client.get(reverse("accounts:signin"))

        self.assertContains(response, reverse("accounts:password_recovery"))

    def test_signin_displays_whatsapp_support_link(self):
        response = self.client.get(reverse("accounts:signin"))

        self.assertContains(response, "Dúvidas - WhatsApp (83) 3048-8555")
        self.assertContains(response, 'class="bi bi-whatsapp"')
        self.assertContains(response, "https://wa.me/558330488555")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_recovery_sends_a_working_temporary_password(self):
        usuario = get_user_model().objects.create_user(
            username="52998224725",
            email="maria@example.com",
            password="SenhaAnterior2026!",
            first_name="Maria",
        )

        response = self.client.post(
            reverse("accounts:password_recovery"),
            {"cpf": "529.982.247-25"},
        )

        self.assertRedirects(response, reverse("accounts:signin"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["maria@example.com"])
        senha_temporaria = mail.outbox[0].body.split("Sua senha temporária é: ", 1)[1].splitlines()[0]
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password(senha_temporaria))
        self.assertFalse(usuario.check_password("SenhaAnterior2026!"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_recovery_does_not_reveal_an_unknown_cpf(self):
        response = self.client.post(
            reverse("accounts:password_recovery"),
            {"cpf": "111.444.777-35"},
            follow=True,
        )

        self.assertContains(response, "Se o CPF estiver vinculado a uma conta com e-mail")
        self.assertContains(response, "aguarde 5 minutos antes de solicitar novamente")
        self.assertEqual(mail.outbox, [])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_recovery_limits_repeated_requests(self):
        usuario = get_user_model().objects.create_user(
            username="52998224725",
            email="maria@example.com",
            password="SenhaAnterior2026!",
        )
        url = reverse("accounts:password_recovery")

        self.client.post(url, {"cpf": "529.982.247-25"})
        usuario.refresh_from_db()
        senha_apos_primeiro_envio = usuario.password
        self.client.post(url, {"cpf": "529.982.247-25"})

        usuario.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(usuario.password, senha_apos_primeiro_envio)

    def test_email_failure_preserves_the_current_password(self):
        usuario = get_user_model().objects.create_user(
            username="52998224725",
            email="maria@example.com",
            password="SenhaAnterior2026!",
        )

        with self.assertLogs("accounts.views", level="ERROR"):
            with patch("accounts.views.send_mail", side_effect=OSError("SMTP indisponível")):
                response = self.client.post(
                    reverse("accounts:password_recovery"),
                    {"cpf": "529.982.247-25"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não foi possível enviar o e-mail agora")
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password("SenhaAnterior2026!"))

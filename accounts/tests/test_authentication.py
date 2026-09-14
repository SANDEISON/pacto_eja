from unittest.mock import patch

from django.core.cache import cache
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


class AuthenticationTests(TestCase):
    def setUp(self):
        """Isola o limite de recuperação entre os testes."""
        cache.clear()

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('accounts:signin')}?next={reverse('dashboard')}")

    def test_signup_creates_user_and_logs_in(self):
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
        self.assertRedirects(response, reverse("dashboard"))
        user = get_user_model().objects.get(username="52998224725")
        self.assertEqual(user.first_name, "Maria")
        self.assertEqual(user.last_name, "da Silva")
        self.assertEqual(user.email, "maria@example.com")
        self.assertEqual(user.educador.cpf, "52998224725")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

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

    def test_logout_only_accepts_post(self):
        user = get_user_model().objects.create_user(username="user@example.com", password="SenhaForte2026!")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("accounts:signin"))

    def test_signin_displays_password_recovery_link(self):
        response = self.client.get(reverse("accounts:signin"))

        self.assertContains(response, reverse("accounts:password_recovery"))

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

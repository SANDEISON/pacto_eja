from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('accounts:signin')}?next=/")

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"full_name": "Maria da Silva", "email": "maria@example.com", "password1": "SenhaForte2026!", "password2": "SenhaForte2026!"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        user = get_user_model().objects.get(username="maria@example.com")
        self.assertEqual(user.first_name, "Maria")
        self.assertEqual(user.last_name, "da Silva")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_logout_only_accepts_post(self):
        user = get_user_model().objects.create_user(username="user@example.com", password="SenhaForte2026!")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("accounts:signin"))

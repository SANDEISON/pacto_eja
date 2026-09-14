from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ReportsViewTests(TestCase):
    """Garante acesso e serialização segura dos dados dos relatórios."""

    def test_reports_require_staff_user(self):
        usuario = get_user_model().objects.create_user(
            username="52998224725",
            password="SenhaForte2026!",
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse("reports"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:signin')}?next={reverse('reports')}",
            fetch_redirect_response=False,
        )

    def test_reports_prepare_participants_and_safe_json(self):
        usuario = get_user_model().objects.create_user(
            username="52998224725",
            password="SenhaForte2026!",
            is_staff=True,
            first_name="Maria </script>",
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse("reports"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_educadores"], 1)
        self.assertEqual(
            response.context["participantes_detalhados"][0]["nome"],
            "Maria </script>",
        )
        self.assertContains(response, r"Maria \u003C/script\u003E")
        self.assertNotContains(response, "Maria </script>")

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="educador@example.com", first_name="Educador", password="SenhaForte2026!")
        self.client.force_login(self.user)

    def test_dashboard_uses_adminlte_layout(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")
        self.assertContains(response, "PAINEL DE ACOMPANHAMENTO", html=False)

    def test_regular_user_menu_hides_management_and_system_headers(self):
        response = self.client.get(reverse("dashboard"))
        menu_texts = [item.get("text") or item.get("header") for item in response.context["adminlte_menu_sidebar"]]
        self.assertEqual(menu_texts, ["Início", "Meu perfil", "Sair"])

    def test_staff_user_sees_management_menu(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.user.user_permissions.add(Permission.objects.get(codename="view_educadorescola"))
        response = self.client.get(reverse("dashboard"))
        menu_texts = [item.get("text") or item.get("header") for item in response.context["adminlte_menu_sidebar"]]
        self.assertEqual(
            menu_texts,
            ["Início", "GESTÃO", "Formações", "Educadores", "Relatórios", "Meu perfil", "Sair"],
        )

    def test_all_error_pages_render(self):
        for code in (400, 401, 403, 404, 500, 503):
            with self.subTest(code=code):
                response = self.client.get(reverse("error_preview", args=[code]))
                self.assertEqual(response.status_code, code)
                self.assertContains(response, str(code), status_code=code)

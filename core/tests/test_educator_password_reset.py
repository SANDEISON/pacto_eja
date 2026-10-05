from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from accounts.constants import SENHA_INICIAL


User = get_user_model()


class EducatorPasswordResetTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="gestor", password="SenhaGestor2026!")
        self.manager.user_permissions.add(Permission.objects.get(codename="change_educador"))
        self.educator = User.objects.create_user(username="52998224725", password="SenhaAnterior2026!")
        self.url = reverse("educator_password_reset", args=(self.educator.educador.pk,))
        self.client.force_login(self.manager)

    def test_reset_changes_only_selected_account_and_requires_new_password(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("educator_model_list"))
        self.educator.refresh_from_db()
        self.manager.refresh_from_db()
        self.assertTrue(self.educator.check_password(SENHA_INICIAL))
        self.assertFalse(self.educator.check_password("SenhaAnterior2026!"))
        self.assertTrue(self.manager.check_password("SenhaGestor2026!"))
        self.client.logout()
        response = self.client.post(
            reverse("accounts:signin"),
            {"username": self.educator.username, "password": SENHA_INICIAL},
        )
        self.assertRedirects(response, reverse("accounts:change_initial_password"))
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("accounts:change_initial_password"))

    def test_get_does_not_change_password(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.educator.refresh_from_db()
        self.assertTrue(self.educator.check_password("SenhaAnterior2026!"))

    def test_anonymous_request_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.post(self.url), f"{reverse('accounts:signin')}?next={self.url}")
        self.educator.refresh_from_db()
        self.assertTrue(self.educator.check_password("SenhaAnterior2026!"))

    def test_view_permission_does_not_allow_reset_or_display_button(self):
        self.manager.user_permissions.clear()
        self.manager.user_permissions.add(Permission.objects.get(codename="view_educador"))
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertNotContains(self.client.get(reverse("educator_model_list")), self.url)
        self.educator.refresh_from_db()
        self.assertTrue(self.educator.check_password("SenhaAnterior2026!"))

    def test_change_permission_displays_button(self):
        response = self.client.get(reverse("educator_model_list"))
        self.assertContains(response, self.url)
        self.assertContains(response, "Redefinir senha")

    def test_reset_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.manager)
        self.assertEqual(client.post(self.url).status_code, 403)
        self.educator.refresh_from_db()
        self.assertTrue(self.educator.check_password("SenhaAnterior2026!"))

    def test_only_superuser_can_reset_privileged_account(self):
        for field in ("is_staff", "is_superuser"):
            with self.subTest(field=field):
                setattr(self.educator, field, True)
                self.educator.save(update_fields=(field,))
                self.assertEqual(self.client.post(self.url).status_code, 403)
                self.assertNotContains(self.client.get(reverse("educator_model_list")), self.url)
                setattr(self.educator, field, False)
                self.educator.save(update_fields=(field,))
        self.educator.refresh_from_db()
        self.assertTrue(self.educator.check_password("SenhaAnterior2026!"))
        self.manager.is_superuser = True
        self.manager.save(update_fields=("is_superuser",))
        self.educator.is_superuser = True
        self.educator.save(update_fields=("is_superuser",))
        self.assertRedirects(self.client.post(self.url), reverse("educator_model_list"))
        self.educator.refresh_from_db()
        self.assertTrue(self.educator.check_password(SENHA_INICIAL))

    def test_unknown_educator_returns_not_found(self):
        url = reverse("educator_password_reset", args=(999999,))
        self.assertEqual(self.client.post(url).status_code, 404)

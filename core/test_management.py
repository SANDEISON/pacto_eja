from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class ManagementAccessTests(TestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user(username="comum@example.com", password="SenhaForte2026!")
        self.admin = User.objects.create_superuser(username="admin@example.com", email="admin@example.com", password="SenhaForte2026!")

    def test_regular_user_cannot_access_management(self):
        self.client.force_login(self.regular_user)
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("group_list")).status_code, 403)

    def test_superuser_sees_users_and_groups_menu(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        administer = next(item for item in response.context["adminlte_menu_sidebar"] if item.get("text") == "Administrar")
        self.assertEqual([item["text"] for item in administer["submenu"]], ["Usuários", "Grupos"])


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin@example.com", email="admin@example.com", password="SenhaForte2026!")
        self.client.force_login(self.admin)

    def test_create_and_search_user(self):
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "nova@example.com",
                "first_name": "Nova",
                "last_name": "Pessoa",
                "email": "nova@example.com",
                "password1": "SenhaForte2026!",
                "password2": "SenhaForte2026!",
                "is_active": "on",
                "groups": [],
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        created = User.objects.get(username="nova@example.com")
        self.assertTrue(created.check_password("SenhaForte2026!"))
        response = self.client.get(reverse("user_list"), {"q": "Nova"})
        self.assertContains(response, "nova@example.com")

    def test_admin_cannot_delete_own_account(self):
        response = self.client.post(reverse("user_delete", args=[self.admin.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())


class GroupManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin@example.com", email="admin@example.com", password="SenhaForte2026!")
        self.client.force_login(self.admin)

    def test_group_crud(self):
        response = self.client.post(reverse("group_create"), {"name": "Coordenadores", "permissions": []})
        self.assertRedirects(response, reverse("group_list"))
        group = Group.objects.get(name="Coordenadores")
        response = self.client.post(reverse("group_update", args=[group.pk]), {"name": "Gestores", "permissions": []})
        self.assertRedirects(response, reverse("group_list"))
        group.refresh_from_db()
        self.assertEqual(group.name, "Gestores")
        response = self.client.post(reverse("group_delete", args=[group.pk]))
        self.assertRedirects(response, reverse("group_list"))
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

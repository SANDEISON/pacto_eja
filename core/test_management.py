from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from .models import CursoCertificado, EducadorGenero, Nivel


User = get_user_model()


class ManagementAccessTests(TestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user(username="comum@example.com", password="SenhaForte2026!")
        self.admin = User.objects.create_superuser(username="admin@example.com", email="admin@example.com", password="SenhaForte2026!")

    def test_regular_user_cannot_access_management(self):
        self.client.force_login(self.regular_user)
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("group_list")).status_code, 403)

    def test_superuser_sees_system_management_menu(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        administer = next(item for item in response.context["adminlte_menu_sidebar"] if item.get("text") == "Administrar")
        self.assertEqual(
            [item["text"] for item in administer["submenu"]],
            [
                "Cidades",
                "Cores/raças",
                "Cursos para certificados",
                "Gêneros",
                "Educadores",
                "Escolas",
                "Estados",
                "Níveis",
                "Modalidades",
                "Situações",
            ],
        )

    def test_system_menu_uses_custom_management_pages(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        administer = next(item for item in response.context["adminlte_menu_sidebar"] if item.get("text") == "Administrar")
        routes = {item["text"]: item["route"] for item in administer["submenu"]}
        self.assertEqual(routes["Cidades"], "city_list")
        self.assertEqual(routes["Cursos para certificados"], "certificate_course_list")
        self.assertEqual(routes["Gêneros"], "educator_gender_list")
        self.assertEqual(routes["Níveis"], "level_list")
        self.assertNotIn("admin:", routes["Níveis"])

    def test_staff_with_change_permission_sees_educator_gender_menu(self):
        staff = User.objects.create_user(
            username="gestor.generos@example.com",
            password="SenhaForte2026!",
            is_staff=True,
        )
        staff.user_permissions.add(Permission.objects.get(codename="change_educadorgenero"))
        self.client.force_login(staff)

        response = self.client.get(reverse("dashboard"))
        administer = next(
            item for item in response.context["adminlte_menu_sidebar"] if item.get("text") == "Administrar"
        )
        self.assertIn("Gêneros", [item["text"] for item in administer["submenu"]])
        self.assertEqual(self.client.get(reverse("educator_gender_list")).status_code, 200)


class CatalogManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin.catalogos@example.com",
            email="admin.catalogos@example.com",
            password="senha-segura",
        )
        self.client.force_login(self.admin)

    def test_custom_list_pages_are_available(self):
        url_names = (
            "city_list",
            "race_color_list",
            "certificate_course_list",
            "educator_gender_list",
            "educator_model_list",
            "school_list",
            "state_list",
            "level_list",
            "modality_list",
            "situation_list",
        )
        for url_name in url_names:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "management/catalog_list.html")

    def test_educator_gender_is_registered_in_django_admin(self):
        self.assertIn(EducadorGenero, admin.site._registry)
        self.assertEqual(admin.site._registry[EducadorGenero].list_display, ("id", "nome", "codigo"))

    def test_certificate_course_is_registered_in_django_admin(self):
        self.assertIn(CursoCertificado, admin.site._registry)
        self.assertEqual(admin.site._registry[CursoCertificado].list_display, ("id", "nome"))

    def test_level_crud_uses_custom_pages(self):
        create_response = self.client.post(
            reverse("catalog_create", args=("niveis",)),
            {"codigo": "curso_livre", "nome": "Curso livre"},
        )
        self.assertRedirects(create_response, reverse("level_list"))
        nivel = Nivel.objects.get(codigo="curso_livre")

        update_response = self.client.post(
            reverse("catalog_update", args=("niveis", nivel.pk)),
            {"codigo": "curso_livre", "nome": "Curso livre atualizado"},
        )
        self.assertRedirects(update_response, reverse("level_list"))
        nivel.refresh_from_db()
        self.assertEqual(nivel.nome, "Curso livre atualizado")

        delete_response = self.client.post(reverse("catalog_delete", args=("niveis", nivel.pk)))
        self.assertRedirects(delete_response, reverse("level_list"))
        self.assertFalse(Nivel.objects.filter(pk=nivel.pk).exists())

    def test_educator_edit_uses_profile_fields(self):
        educator_user = User.objects.create_user(
            username="educadora@example.com",
            email="educadora@example.com",
            first_name="Maria",
            last_name="Educadora",
        )
        educador = educator_user.educador
        genero = EducadorGenero.objects.get(codigo="feminino")

        get_response = self.client.get(
            reverse("catalog_update", args=("cadastros-educadores", educador.pk))
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, "management/educator_profile_form.html")
        self.assertContains(get_response, "Dados da conta")
        self.assertContains(get_response, "Dados pessoais")
        self.assertContains(get_response, "Endereço")
        self.assertContains(get_response, "Formações")

        post_response = self.client.post(
            reverse("catalog_update", args=("cadastros-educadores", educador.pk)),
            {
                "user-full_name": "Maria Atualizada",
                "user-email": "maria.atualizada@example.com",
                "educador-nome_social": "Maria",
                "educador-cpf": "",
                "educador-data_nascimento": "",
                "educador-genero": genero.pk,
                "educador-cor_raca": "",
                "educador-estado_civil": "",
                "educador-telefone": "(82) 99999-0000",
                "endereco-cep": "",
                "endereco-logradouro": "",
                "endereco-numero": "",
                "endereco-complemento": "",
                "endereco-bairro": "",
                "endereco-estado": "",
                "endereco-cidade": "",
                "formacao-TOTAL_FORMS": "0",
                "formacao-INITIAL_FORMS": "0",
                "formacao-MIN_NUM_FORMS": "0",
                "formacao-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertRedirects(post_response, reverse("educator_model_list"))
        educator_user.refresh_from_db()
        educador.refresh_from_db()
        self.assertEqual(educator_user.get_full_name(), "Maria Atualizada")
        self.assertEqual(educator_user.email, "maria.atualizada@example.com")
        self.assertEqual(educador.genero, genero)
        self.assertEqual(educador.telefone, "(82) 99999-0000")


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin@example.com", email="admin@example.com", password="SenhaForte2026!")
        self.client.force_login(self.admin)

    def test_create_and_search_user(self):
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "529.982.247-25",
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
        created = User.objects.get(username="52998224725")
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

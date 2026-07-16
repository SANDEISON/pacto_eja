from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CadastroEducador, Cidade, Escola, Estado


User = get_user_model()


class EducatorManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="admin.educadores@example.com",
            email="admin.educadores@example.com",
            password="senha-segura",
        )
        cls.regular_user = User.objects.create_user(
            username="usuario@example.com",
            email="usuario@example.com",
            password="senha-segura",
        )
        cls.educator_user = User.objects.create_user(
            username="educador@example.com",
            email="educador@example.com",
            first_name="Educador Gerenciado",
            password="senha-segura",
        )
        cls.educator_user.pessoa.cpf = "52998224725"
        cls.educator_user.pessoa.save(update_fields=("cpf",))
        cls.estado = Estado.objects.get(sigla="AL")
        cls.cidade = Cidade.objects.get(estado=cls.estado, nome_cidade="Maceió")
        cls.escola = Escola.objects.create(
            id_escola=27000002,
            nome="Escola de Gestão",
            id_municipio=cls.cidade.codigo_ibge,
            sigla_uf=cls.estado.sigla,
        )
        cls.cadastro = CadastroEducador.objects.create(
            id_pessoa=cls.educator_user.pessoa,
            estado=cls.estado,
            cidade=cls.cidade,
            escola=cls.escola,
            funcao_caracterizacao_turmas="anos_iniciais_eja",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def form_data(self, **overrides):
        data = {
            "id_pessoa": self.educator_user.pessoa.pk,
            "estado": self.estado.pk,
            "cidade": self.cidade.pk,
            "escola": self.escola.pk,
            "funcao_caracterizacao_turmas": "ensino_medio",
        }
        data.update(overrides)
        return data

    def test_user_without_permission_cannot_open_management(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("educator_list"))

        self.assertEqual(response.status_code, 403)

    def test_list_displays_registered_educators(self):
        response = self.client.get(reverse("educator_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Educador Gerenciado")
        self.assertContains(response, "Escola de Gestão")

    def test_management_menu_links_to_educators(self):
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, reverse("educator_list"))

    def test_create_educator_registration(self):
        novo_usuario = User.objects.create_user(
            username="novo.educador@example.com",
            email="novo.educador@example.com",
            first_name="Novo Educador",
        )
        response = self.client.post(
            reverse("educator_create"),
            self.form_data(id_pessoa=novo_usuario.pessoa.pk),
        )

        self.assertRedirects(response, reverse("educator_list"))
        self.assertTrue(CadastroEducador.objects.filter(id_pessoa=novo_usuario.pessoa).exists())

    def test_management_rejects_second_registration_for_same_person(self):
        response = self.client.post(reverse("educator_create"), self.form_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Esta pessoa já possui um cadastro de educador.")
        self.assertEqual(CadastroEducador.objects.filter(id_pessoa=self.educator_user.pessoa).count(), 1)

    def test_update_educator_registration(self):
        response = self.client.post(
            reverse("educator_update", args=(self.cadastro.pk,)),
            self.form_data(funcao_caracterizacao_turmas="educacao_profissional"),
        )

        self.assertRedirects(response, reverse("educator_list"))
        self.cadastro.refresh_from_db()
        self.assertEqual(self.cadastro.funcao_caracterizacao_turmas, "educacao_profissional")

    def test_delete_educator_registration(self):
        response = self.client.post(reverse("educator_delete", args=(self.cadastro.pk,)))

        self.assertRedirects(response, reverse("educator_list"))
        self.assertFalse(CadastroEducador.objects.filter(pk=self.cadastro.pk).exists())

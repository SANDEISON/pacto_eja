from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cidade, EducadorEscola, Escola, Estado, FuncaoCaracterizacaoTurma, FuncaoEducador


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
        cls.educator_user.educador.cpf = "52998224725"
        cls.educator_user.educador.save(update_fields=("cpf",))
        cls.estado = Estado.objects.get(sigla="AL")
        cls.cidade = Cidade.objects.get(estado=cls.estado, nome_cidade="Maceió")
        cls.escola = Escola.objects.create(
            id_escola=27000002,
            nome="Escola de Gestão",
            id_municipio=cls.cidade.codigo_ibge,
            sigla_uf=cls.estado.sigla,
        )
        cls.anos_iniciais = FuncaoCaracterizacaoTurma.objects.get(codigo="anos_iniciais_eja")
        cls.ensino_medio = FuncaoCaracterizacaoTurma.objects.get(codigo="ensino_medio")
        cls.educacao_profissional = FuncaoCaracterizacaoTurma.objects.get(codigo="educacao_profissional")
        cls.cadastro = EducadorEscola.objects.create(
            cidade=cls.cidade,
            escola=cls.escola,
            funcao_caracterizacao_turmas=cls.anos_iniciais,
        )
        cls.funcao_educador = FuncaoEducador.objects.create(
            educador=cls.educator_user.educador,
            educador_escola=cls.cadastro,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def form_data(self, **overrides):
        data = {
            "educador": self.educator_user.educador.pk,
            "estado": self.estado.pk,
            "cidade": self.cidade.pk,
            "escola": self.escola.pk,
            "funcao_caracterizacao_turmas": self.ensino_medio.pk,
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
            self.form_data(educador=novo_usuario.educador.pk),
        )

        self.assertRedirects(response, reverse("educator_list"))
        self.assertTrue(
            EducadorEscola.objects.filter(
                funcao_educador__educador=novo_usuario.educador,
            ).exists()
        )

    def test_management_allows_second_registration_for_same_person(self):
        outra_escola = Escola.objects.create(
            id_escola=27000003,
            nome="Segunda Escola de Gestão",
            id_municipio=self.cidade.codigo_ibge,
            sigla_uf=self.estado.sigla,
        )
        response = self.client.post(
            reverse("educator_create"),
            self.form_data(
                escola=outra_escola.pk,
                funcao_caracterizacao_turmas=self.anos_iniciais.pk,
            ),
        )

        self.assertRedirects(response, reverse("educator_list"))
        self.assertEqual(
            EducadorEscola.objects.filter(
                funcao_educador__educador=self.educator_user.educador,
            ).count(),
            2,
        )
        self.assertEqual(
            FuncaoEducador.objects.filter(educador=self.educator_user.educador).count(),
            2,
        )

    def test_management_rejects_exact_duplicate_registration(self):
        response = self.client.post(
            reverse("educator_create"),
            self.form_data(funcao_caracterizacao_turmas=self.anos_iniciais.pk),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este vínculo do educador com a escola já está cadastrado.")

    def test_update_educator_registration(self):
        get_response = self.client.get(reverse("educator_update", args=(self.cadastro.pk,)))
        self.assertEqual(get_response.context["form"]["estado"].value(), self.estado.pk)

        response = self.client.post(
            reverse("educator_update", args=(self.cadastro.pk,)),
            self.form_data(funcao_caracterizacao_turmas=self.educacao_profissional.pk),
        )

        self.assertRedirects(response, reverse("educator_list"))
        self.cadastro.refresh_from_db()
        self.assertEqual(
            self.cadastro.funcao_caracterizacao_turmas,
            self.educacao_profissional,
        )

    def test_delete_educator_registration(self):
        response = self.client.post(reverse("educator_delete", args=(self.cadastro.pk,)))

        self.assertRedirects(response, reverse("educator_list"))
        self.assertFalse(EducadorEscola.objects.filter(pk=self.cadastro.pk).exists())

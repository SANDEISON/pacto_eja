import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cidade, Educador, EducadorEscola, Escola, Estado, FuncaoEducador


User = get_user_model()


class EducadorEscolaCadastroPublicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.estado = Estado.objects.get(sigla="AL")
        cls.cidade = Cidade.objects.get(estado=cls.estado, nome_cidade="Maceió")
        cls.escola = Escola.objects.create(
            id_escola=27000001,
            nome="Escola Municipal de Teste",
            id_municipio=cls.cidade.codigo_ibge,
            sigla_uf=cls.estado.sigla,
        )

    def registration_data(self, **overrides):
        data = {
            "cpf": "529.982.247-25",
            "nome_completo": "Maria Educadora da Silva",
            "email": "maria.educadora@example.com",
            "atuacoes_json": json.dumps([self.assignment_data()]),
        }
        data.update(overrides)
        return data

    def assignment_data(self, **overrides):
        data = {
            "estado_id": self.estado.pk,
            "cidade_id": self.cidade.pk,
            "escola_id": self.escola.pk,
            "funcao": "alfabetizacao_eja",
        }
        data.update(overrides)
        return data

    def test_public_form_does_not_require_login(self):
        response = self.client.get(reverse("cadastro_educador"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro de Participantes")

    def test_home_redirects_to_public_form(self):
        response = self.client.get(reverse("home"))

        self.assertRedirects(response, reverse("cadastro_educador"))

    def test_cities_endpoint_filters_by_state(self):
        response = self.client.get(reverse("cadastro_educador_cidades"), {"estado": self.estado.pk})

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            {"id": self.cidade.pk, "nome_cidade": "Maceió"},
            response.json()["results"],
        )

    def test_schools_endpoint_filters_by_city_and_name(self):
        response = self.client.get(
            reverse("cadastro_educador_escolas"),
            {"cidade": self.cidade.pk, "q": "Municipal de Teste"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"],
            [{"id_escola": self.escola.pk, "nome": self.escola.nome}],
        )

    def test_new_cpf_creates_user_person_and_registration(self):
        response = self.client.post(reverse("cadastro_educador"), self.registration_data())

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        usuario = User.objects.get(username="52998224725")
        self.assertEqual(usuario.first_name, "Maria")
        self.assertEqual(usuario.last_name, "Educadora da Silva")
        self.assertEqual(usuario.get_full_name(), "Maria Educadora da Silva")
        self.assertEqual(usuario.email, "maria.educadora@example.com")
        self.assertTrue(usuario.check_password("52998224725"))
        self.assertEqual(usuario.educador.cpf, "52998224725")
        self.assertEqual(usuario.educador.nome_completo, "Maria Educadora da Silva")
        cadastro = EducadorEscola.objects.get(funcao_educador__educador=usuario.educador)
        self.assertEqual(cadastro.cidade, self.cidade)
        self.assertEqual(cadastro.cidade.estado, self.estado)
        self.assertEqual(cadastro.escola, self.escola)

    def test_single_submission_creates_multiple_school_assignments(self):
        segunda_escola = Escola.objects.create(
            id_escola=27000004,
            nome="Segunda Escola Municipal de Teste",
            id_municipio=self.cidade.codigo_ibge,
            sigla_uf=self.estado.sigla,
        )
        atuacoes = [
            self.assignment_data(),
            self.assignment_data(
                escola_id=segunda_escola.pk,
                funcao="ensino_medio",
            ),
        ]

        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(atuacoes_json=json.dumps(atuacoes)),
        )

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        educador = User.objects.get(username="52998224725").educador
        self.assertEqual(FuncaoEducador.objects.filter(educador=educador).count(), 2)
        self.assertEqual(
            EducadorEscola.objects.filter(funcao_educador__educador=educador).count(),
            2,
        )

    def test_registration_requires_at_least_one_assignment(self):
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(atuacoes_json="[]"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adicione pelo menos uma atuação antes de salvar o cadastro.")
        self.assertFalse(User.objects.filter(username="52998224725").exists())

    def test_existing_cpf_reuses_user_and_person(self):
        usuario = User.objects.create_user(
            username="existente@example.com",
            email="existente@example.com",
            first_name="Educador Existente",
            password="senha-segura",
        )
        educador = usuario.educador
        educador.cpf = "52998224725"
        educador.save(update_fields=("cpf",))
        total_usuarios = User.objects.count()

        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(nome_completo="Nome adulterado", email="outro@example.com"),
        )

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        self.assertEqual(User.objects.count(), total_usuarios)
        self.assertTrue(
            EducadorEscola.objects.filter(
                funcao_educador__educador=educador,
                escola=self.escola,
            ).exists()
        )
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, "Educador Existente")
        self.assertEqual(usuario.email, "existente@example.com")

    def test_person_can_submit_a_second_registration(self):
        usuario = User.objects.create_user(
            username="ja.cadastrado@example.com",
            email="ja.cadastrado@example.com",
            first_name="Educador Já Cadastrado",
        )
        educador = usuario.educador
        educador.cpf = "52998224725"
        educador.save(update_fields=("cpf",))
        vinculo = EducadorEscola.objects.create(
            cidade=self.cidade,
            escola=self.escola,
            funcao_caracterizacao_turmas="anos_iniciais_eja",
        )
        FuncaoEducador.objects.create(
            educador=educador,
            educador_escola=vinculo,
        )

        response = self.client.post(reverse("cadastro_educador"), self.registration_data())

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        self.assertEqual(
            EducadorEscola.objects.filter(funcao_educador__educador=educador).count(),
            2,
        )

    def test_cpf_lookup_returns_saved_person_data(self):
        usuario = User.objects.create_user(
            username="consulta@example.com",
            email="consulta@example.com",
            first_name="Pessoa Localizada",
        )
        educador = usuario.educador
        educador.cpf = "52998224725"
        educador.save(update_fields=("cpf",))

        response = self.client.get(reverse("cadastro_educador_cpf_lookup"), {"cpf": "529.982.247-25"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "valid": True,
                "exists": True,
                "registered": False,
                "nome_completo": "Pessoa Localizada",
                "email": "consulta@example.com",
            },
        )

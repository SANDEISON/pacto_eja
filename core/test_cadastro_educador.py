from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CadastroEducador, Cidade, Escola, Estado, Pessoa


User = get_user_model()


class CadastroEducadorPublicoTests(TestCase):
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
            "estado": self.estado.pk,
            "cidade": self.cidade.pk,
            "escola": self.escola.pk,
            "funcao_caracterizacao_turmas": "alfabetizacao_eja",
        }
        data.update(overrides)
        return data

    def test_public_form_does_not_require_login(self):
        response = self.client.get(reverse("cadastro_educador"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro de educadores")

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
            {"cidade": self.cidade.pk, "q": "Municipal"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"],
            [{"id_escola": self.escola.pk, "nome": self.escola.nome}],
        )

    def test_new_cpf_creates_user_person_and_registration(self):
        response = self.client.post(reverse("cadastro_educador"), self.registration_data())

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        usuario = User.objects.get(username="maria.educadora@example.com")
        self.assertEqual(usuario.first_name, "Maria Educadora da Silva")
        self.assertTrue(usuario.check_password("52998224725"))
        self.assertEqual(usuario.pessoa.cpf, "52998224725")
        cadastro = CadastroEducador.objects.get(id_pessoa=usuario.pessoa)
        self.assertEqual(cadastro.cidade, self.cidade)
        self.assertEqual(cadastro.escola, self.escola)

    def test_existing_cpf_reuses_user_and_person(self):
        usuario = User.objects.create_user(
            username="existente@example.com",
            email="existente@example.com",
            first_name="Educador Existente",
            password="senha-segura",
        )
        pessoa = usuario.pessoa
        pessoa.cpf = "52998224725"
        pessoa.save(update_fields=("cpf",))
        total_usuarios = User.objects.count()

        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(nome_completo="Nome adulterado", email="outro@example.com"),
        )

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        self.assertEqual(User.objects.count(), total_usuarios)
        self.assertTrue(CadastroEducador.objects.filter(id_pessoa=pessoa, escola=self.escola).exists())
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, "Educador Existente")
        self.assertEqual(usuario.email, "existente@example.com")

    def test_person_cannot_submit_a_second_registration(self):
        usuario = User.objects.create_user(
            username="ja.cadastrado@example.com",
            email="ja.cadastrado@example.com",
            first_name="Educador Já Cadastrado",
        )
        pessoa = usuario.pessoa
        pessoa.cpf = "52998224725"
        pessoa.save(update_fields=("cpf",))
        CadastroEducador.objects.create(
            id_pessoa=pessoa,
            estado=self.estado,
            cidade=self.cidade,
            escola=self.escola,
            funcao_caracterizacao_turmas="anos_iniciais_eja",
        )

        response = self.client.post(reverse("cadastro_educador"), self.registration_data())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Esta pessoa já possui um cadastro de educador.")
        self.assertEqual(CadastroEducador.objects.filter(id_pessoa=pessoa).count(), 1)

    def test_cpf_lookup_returns_saved_person_data(self):
        usuario = User.objects.create_user(
            username="consulta@example.com",
            email="consulta@example.com",
            first_name="Pessoa Localizada",
        )
        pessoa = usuario.pessoa
        pessoa.cpf = "52998224725"
        pessoa.save(update_fields=("cpf",))

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

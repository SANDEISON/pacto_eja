from datetime import date
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Cidade, CorRaca, CursoCertificado, Educador, EducadorEscola, EducadorGenero, Endereco,
    Escola, Estado, Funcao, FuncaoCaracterizacaoTurma, FuncaoEducador,
)


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
        cls.cor_raca = CorRaca.objects.get(nome="Pardo")
        cls.genero_feminino = EducadorGenero.objects.get(codigo="feminino")
        cls.genero_nao_binario = EducadorGenero.objects.get(codigo="nao_binario")
        cls.funcao = Funcao.objects.get(codigo="formador_pacto_anos_iniciais")
        cls.alfabetizacao = FuncaoCaracterizacaoTurma.objects.get(codigo="alfabetizacao_eja")
        cls.anos_iniciais = FuncaoCaracterizacaoTurma.objects.get(codigo="anos_iniciais_eja")
        cls.ensino_medio = FuncaoCaracterizacaoTurma.objects.get(codigo="ensino_medio")
        cls.curso_certificado = CursoCertificado.objects.get(
            nome="Alfabetização de Jovens, Adultos e Idosos - 80 horas"
        )
        cls.outro_curso_certificado = CursoCertificado.objects.get(
            nome="Formação em Serviço para Formadores Regionais - 360 horas"
        )

    def registration_data(self, **overrides):
        data = {
            "cpf": "529.982.247-25",
            "nome_completo": "Maria Educadora da Silva",
            "email": "maria.educadora@example.com",
            "data_nascimento": "1990-05-12",
            "cor_raca": self.cor_raca.pk,
            "genero": self.genero_feminino.pk,
            "curso_certificado": [self.curso_certificado.pk],
            "endereco_cep": "57000-000",
            "endereco_logradouro": "Avenida Fernandes Lima",
            "endereco_numero": "1000",
            "endereco_complemento": "Sala 10",
            "endereco_bairro": "Farol",
            "endereco_estado": self.estado.pk,
            "endereco_cidade": self.cidade.pk,
            "atuacoes_json": json.dumps([self.assignment_data()]),
        }
        data.update(overrides)
        return data

    def assignment_data(self, **overrides):
        data = {
            "estado_id": self.estado.pk,
            "cidade_id": self.cidade.pk,
            "escola_id": self.escola.pk,
            "funcao": self.funcao.pk,
            "funcao_caracterizacao_turmas": self.alfabetizacao.pk,
            "tempo_atuacao": "4_6_anos",
        }
        data.update(overrides)
        return data

    def test_public_form_does_not_require_login(self):
        response = self.client.get(reverse("cadastro_educador"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro de Participantes")
        self.assertContains(response, "Cor/raça")
        self.assertContains(response, "Pardo")
        self.assertContains(response, 'id="id_cor_raca"')
        self.assertContains(response, 'id="id_genero"')
        self.assertContains(response, 'id="id_data_nascimento"')
        self.assertContains(response, "Endereço")
        self.assertContains(response, 'id="id_endereco_cep"')
        self.assertContains(response, 'id="id_endereco_logradouro"')
        self.assertContains(response, 'id="id_endereco_estado"')
        self.assertContains(response, 'id="id_endereco_cidade"')
        self.assertContains(response, "Feminino")
        self.assertContains(response, "Masculino")
        self.assertContains(response, "Não binário")
        self.assertContains(response, 'id="id_tempo_atuacao"')
        self.assertContains(response, 'id="id_funcao"')
        self.assertContains(response, "Formador(a) do Pacto | Anos Iniciais")
        self.assertContains(response, "Convidado(a) estrangeiro(a)")
        self.assertContains(response, "0-3 anos")
        self.assertContains(response, "4-6 anos")
        self.assertContains(response, "Mais de 6 anos")
        self.assertContains(response, "Solicito liberação do Certificado do Curso:")
        self.assertContains(response, "Você pode selecionar apenas um curso ou os dois")
        self.assertContains(response, "Alfabetização de Jovens, Adultos e Idosos - 80 horas")
        self.assertContains(response, "Formação em Serviço para Formadores Regionais - 360 horas")
        self.assertContains(response, 'type="checkbox"')

    def test_cor_raca_options_are_ordered_by_id(self):
        response = self.client.get(reverse("cadastro_educador"))

        queryset = response.context["form"].fields["cor_raca"].queryset
        ids = list(queryset.values_list("id", flat=True))
        self.assertEqual(ids, sorted(ids))

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
        self.assertEqual(usuario.educador.cor_raca, self.cor_raca)
        self.assertEqual(usuario.educador.genero, self.genero_feminino)
        self.assertEqual(usuario.educador.data_nascimento, date(1990, 5, 12))
        self.assertQuerySetEqual(
            usuario.educador.cursos_certificados.all(),
            [self.curso_certificado],
        )
        endereco = usuario.educador.endereco
        self.assertEqual(endereco.cep, "57000000")
        self.assertEqual(endereco.logradouro, "Avenida Fernandes Lima")
        self.assertEqual(endereco.numero, "1000")
        self.assertEqual(endereco.complemento, "Sala 10")
        self.assertEqual(endereco.bairro, "Farol")
        self.assertEqual(endereco.cidade, self.cidade)
        cadastro = EducadorEscola.objects.get(funcao_educador__educador=usuario.educador)
        self.assertEqual(cadastro.cidade, self.cidade)
        self.assertEqual(cadastro.cidade.estado, self.estado)
        self.assertEqual(cadastro.escola, self.escola)
        self.assertEqual(cadastro.funcao, self.funcao)
        self.assertEqual(cadastro.tempo_atuacao, "4_6_anos")

    def test_registration_allows_requesting_both_certificates(self):
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(
                curso_certificado=[
                    self.curso_certificado.pk,
                    self.outro_curso_certificado.pk,
                ]
            ),
        )

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        educador = Educador.objects.get(cpf="52998224725")
        self.assertQuerySetEqual(
            educador.cursos_certificados.all(),
            [self.curso_certificado, self.outro_curso_certificado],
        )

    def test_registration_requires_complete_address(self):
        data = self.registration_data()
        address_fields = (
            "endereco_cep",
            "endereco_logradouro",
            "endereco_numero",
            "endereco_complemento",
            "endereco_bairro",
            "endereco_estado",
            "endereco_cidade",
        )
        for field_name in address_fields:
            data.pop(field_name)

        response = self.client.post(reverse("cadastro_educador"), data)

        self.assertEqual(response.status_code, 200)
        for field_name in address_fields:
            self.assertFormError(response.context["form"], field_name, "Este campo é obrigatório.")
        self.assertFalse(User.objects.filter(username="52998224725").exists())

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
                funcao_caracterizacao_turmas=self.ensino_medio.pk,
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
        self.assertEqual(Endereco.objects.filter(educador=educador).count(), 1)
        educador.endereco.refresh_from_db()
        self.assertEqual(educador.endereco.logradouro, "Avenida Fernandes Lima")
        self.assertEqual(educador.endereco.numero, "1000")

    def test_registration_requires_at_least_one_assignment(self):
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(atuacoes_json="[]"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adicione pelo menos uma atuação antes de salvar o cadastro.")
        self.assertFalse(User.objects.filter(username="52998224725").exists())

    def test_registration_rejects_assignment_without_experience_time(self):
        atuacao = self.assignment_data()
        atuacao.pop("tempo_atuacao")

        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(atuacoes_json=json.dumps([atuacao])),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Há uma atuação com informações inválidas.")
        self.assertFalse(User.objects.filter(username="52998224725").exists())

    def test_registration_rejects_assignment_without_function(self):
        atuacao = self.assignment_data()
        atuacao.pop("funcao")

        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(atuacoes_json=json.dumps([atuacao])),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Há uma atuação com informações inválidas.")
        self.assertFalse(User.objects.filter(username="52998224725").exists())

    def test_registration_rejects_future_birth_date(self):
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(data_nascimento="2999-01-01"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "não pode estar no futuro")
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
        educador.cor_raca = CorRaca.objects.get(nome="Branco")
        educador.save(update_fields=("cpf", "cor_raca"))
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
        educador.refresh_from_db()
        self.assertEqual(educador.cor_raca, self.cor_raca)
        self.assertEqual(educador.endereco.cep, "57000000")

    def test_person_can_submit_a_second_registration(self):
        usuario = User.objects.create_user(
            username="ja.cadastrado@example.com",
            email="ja.cadastrado@example.com",
            first_name="Educador Já Cadastrado",
        )
        educador = usuario.educador
        educador.cpf = "52998224725"
        educador.cor_raca = self.cor_raca
        educador.genero = self.genero_nao_binario
        educador.data_nascimento = date(1985, 8, 20)
        educador.save(update_fields=("cpf", "cor_raca", "genero", "data_nascimento"))
        Endereco.objects.create(
            educador=educador,
            cep="57000000",
            logradouro="Rua do Cadastro",
            numero="20",
            complemento="Casa",
            bairro="Centro",
            cidade=self.cidade,
        )
        vinculo = EducadorEscola.objects.create(
            cidade=self.cidade,
            escola=self.escola,
            funcao_caracterizacao_turmas=self.anos_iniciais,
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
        self.assertEqual(Endereco.objects.filter(educador=educador).count(), 1)
        educador.endereco.refresh_from_db()
        self.assertEqual(educador.endereco.logradouro, "Avenida Fernandes Lima")
        self.assertEqual(educador.endereco.numero, "1000")

    def test_cpf_lookup_returns_saved_person_data(self):
        usuario = User.objects.create_user(
            username="consulta@example.com",
            email="consulta@example.com",
            first_name="Pessoa Localizada",
        )
        educador = usuario.educador
        educador.cpf = "52998224725"
        educador.cor_raca = self.cor_raca
        educador.genero = self.genero_nao_binario
        educador.data_nascimento = date(1985, 8, 20)
        educador.save(update_fields=("cpf", "cor_raca", "genero", "data_nascimento"))

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
                "cor_raca_id": self.cor_raca.pk,
                "genero": self.genero_nao_binario.pk,
                "data_nascimento": "1985-08-20",
            },
        )

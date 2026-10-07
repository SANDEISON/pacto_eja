from datetime import date
from importlib import import_module
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.apps import apps
from django.core import mail
from django.db import IntegrityError, connection
from django.test import TestCase, override_settings
from django.urls import reverse

from ..models import (
    CadastroPendente, Cidade, CorRaca, CursoCertificado, Educador, EducadorEscola, EducadorGenero, Endereco,
    Escola, Estado, Funcao, FuncaoCaracterizacaoTurma, FuncaoEducador, EnvioCadastroEducador,
)


User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
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
        if "email_confirmacao" not in overrides:
            data["email_confirmacao"] = data["email"]
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

    def submit_registration(self, data):
        response = self.client.post(reverse("cadastro_educador"), data)
        self.assertRedirects(response, reverse("cadastro_educador_success"))
        self.assertTrue(User.objects.filter(username="52998224725").exists())
        self.assertEqual(mail.outbox, [])
        self.assertFalse(CadastroPendente.objects.exists())

    def test_successful_registration_records_one_completed_submission(self):
        self.submit_registration(self.registration_data())
        envio = EnvioCadastroEducador.objects.get()
        self.assertEqual(envio.educador.usuario.username, "52998224725")
        self.assertEqual(envio.operacao, EnvioCadastroEducador.Operacao.CADASTRO)
        self.assertEqual(envio.total_atuacoes, 1)
        self.assertIsNotNone(envio.concluido_em)
        self.assertIsInstance(envio.numero, int)
        self.assertGreater(envio.numero, 0)

    def test_edit_records_a_separate_submission_and_keeps_the_original(self):
        self.submit_registration(self.registration_data())
        original = EnvioCadastroEducador.objects.get()
        response = self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf="52998224725", endereco_logradouro="Rua Corrigida",
        ))
        self.assertRedirects(response, reverse("cadastro_educador_success"))
        envios = list(EnvioCadastroEducador.objects.order_by("concluido_em"))
        self.assertEqual(len(envios), 2)
        self.assertEqual(envios[0].pk, original.pk)
        self.assertEqual(envios[1].educador_id, original.educador_id)
        self.assertEqual(envios[1].operacao, EnvioCadastroEducador.Operacao.EDICAO)
        self.assertGreater(envios[1].numero, original.numero)
        self.assertNotEqual(envios[1].pk, original.pk)
        self.assertEqual(FuncaoEducador.objects.count(), 1)

    def test_invalid_and_rejected_submissions_do_not_create_history(self):
        self.client.post(reverse("cadastro_educador"), self.registration_data(email_confirmacao=""))
        self.assertFalse(EnvioCadastroEducador.objects.exists())
        self.submit_registration(self.registration_data())
        self.client.post(reverse("cadastro_educador"), self.registration_data())
        self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf="52998224725", email_confirmacao="outro@example.com",
        ))
        self.assertEqual(EnvioCadastroEducador.objects.count(), 1)

    def test_history_failure_rolls_back_the_registration(self):
        with patch.object(EnvioCadastroEducador.objects, "create", side_effect=IntegrityError("Falha no histórico")):
            response = self.client.post(reverse("cadastro_educador"), self.registration_data())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertFalse(User.objects.filter(username="52998224725").exists())
        self.assertFalse(FuncaoEducador.objects.exists())
        self.assertFalse(Endereco.objects.exists())
        self.assertFalse(EnvioCadastroEducador.objects.exists())

    def import_legacy_registrations(self):
        migration = import_module("core.migrations.0043_registros_legados_cadastro")
        migration.importar_registros_legados(apps, SimpleNamespace(connection=connection))

    def test_legacy_import_creates_one_reference_even_with_duplicate_assignments(self):
        self.submit_registration(self.registration_data())
        EnvioCadastroEducador.objects.all().delete()
        original = EducadorEscola.objects.get()
        primeira_data = original.criado_em
        educador = Educador.objects.get(cpf="52998224725")
        original.pk = None
        original.save()
        FuncaoEducador.objects.create(educador=educador, educador_escola=original)

        self.import_legacy_registrations()
        self.import_legacy_registrations()

        legado = EnvioCadastroEducador.objects.get()
        self.assertEqual(legado.operacao, EnvioCadastroEducador.Operacao.LEGADO)
        self.assertIsNone(legado.concluido_em)
        self.assertEqual(legado.data_referencia, primeira_data)
        self.assertEqual(legado.total_atuacoes, 2)
        self.assertEqual(FuncaoEducador.objects.count(), 2)

    def test_legacy_import_skips_recorded_submissions_and_accounts_without_assignments(self):
        self.submit_registration(self.registration_data())
        original = EnvioCadastroEducador.objects.get()
        User.objects.create_user(username="conta-sem-atuacoes")
        self.import_legacy_registrations()
        self.assertEqual(EnvioCadastroEducador.objects.count(), 1)
        self.assertEqual(EnvioCadastroEducador.objects.get().pk, original.pk)

    def test_edit_of_legacy_registration_records_a_proven_submission(self):
        self.submit_registration(self.registration_data())
        EnvioCadastroEducador.objects.all().delete()
        self.import_legacy_registrations()
        response = self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf="52998224725", endereco_logradouro="Rua Corrigida",
        ))
        self.assertRedirects(response, reverse("cadastro_educador_success"))
        self.assertEqual(EnvioCadastroEducador.objects.count(), 2)
        envio = EnvioCadastroEducador.objects.get(operacao=EnvioCadastroEducador.Operacao.EDICAO)
        self.assertIsNotNone(envio.concluido_em)
        self.assertIsNone(envio.data_referencia)

    def test_public_form_does_not_require_login(self):
        response = self.client.get(reverse("cadastro_educador"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Solicitação de certificado",
        )
        self.assertContains(response, "Cor/raça")
        self.assertContains(response, "Pardo")
        self.assertContains(response, 'id="id_cor_raca"')
        self.assertContains(response, 'id="id_genero"')
        self.assertContains(response, 'id="id_data_nascimento"')
        self.assertContains(response, 'id="id_email_confirmacao"')
        self.assertContains(response, "Confirme o e-mail")
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
        self.assertContains(
            response,
            "Selecione abaixo o(s) curso(s) para o(s) qual(is) deseja solicitar o certificado. "
            "Você pode optar por um ou mais de um curso simultaneamente.",
        )
        self.assertNotContains(response, "Não desejo suprimir o certificado")
        self.assertNotContains(response, 'id="id_nao_solicitar_certificado"')
        self.assertContains(response, "Alfabetização de Jovens, Adultos e Idosos - 80 horas")
        self.assertContains(response, "Formação em Serviço para Formadores Regionais - 360 horas")
        self.assertContains(response, 'type="checkbox"')
        self.assertNotContains(response, "Fazer login")

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
        self.submit_registration(self.registration_data())

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
        self.assertFalse(CadastroPendente.objects.exists())

    def test_other_school_is_listed_before_the_result_limit(self):
        Escola.objects.bulk_create([
            Escola(
                id_escola=28000000 + index,
                nome=f"Escola {index:03d}",
                id_municipio=self.cidade.codigo_ibge,
                sigla_uf=self.estado.sigla,
            )
            for index in range(105)
        ])
        response = self.client.get(
            reverse("cadastro_educador_escolas"), {"cidade": self.cidade.pk}
        )
        results = response.json()["results"]
        self.assertEqual(len(results), 100)
        self.assertEqual(results[0], {
            "id_escola": 9_000_000_000 + self.cidade.codigo_ibge,
            "nome": "Outra",
        })

    def test_registration_can_use_other_school(self):
        outra = Escola.objects.get(pk=9_000_000_000 + self.cidade.codigo_ibge)
        self.submit_registration(self.registration_data(
            atuacoes_json=json.dumps([self.assignment_data(escola_id=outra.pk)])
        ))
        cadastro = EducadorEscola.objects.get(funcao_educador__educador__cpf="52998224725")
        self.assertEqual(cadastro.escola, outra)
        self.assertEqual(cadastro.cidade, self.cidade)

    def test_registration_allows_requesting_both_certificates(self):
        self.submit_registration(
            self.registration_data(
                curso_certificado=[
                    self.curso_certificado.pk,
                    self.outro_curso_certificado.pk,
                ]
            ),
        )

        educador = Educador.objects.get(cpf="52998224725")
        self.assertQuerySetEqual(
            educador.cursos_certificados.all(),
            [self.curso_certificado, self.outro_curso_certificado],
        )

    def test_registration_requires_certificate_choice(self):
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(curso_certificado=[]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "curso_certificado",
            "Selecione pelo menos um curso para solicitar o certificado.",
        )
        self.assertFalse(Educador.objects.filter(cpf="52998224725").exists())

    def test_removed_opt_out_cannot_bypass_required_certificate_choice(self):
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(
                curso_certificado=[],
                nao_solicitar_certificado="on",
            ),
        )

        self.assertFormError(
            response.context["form"], "curso_certificado",
            "Selecione pelo menos um curso para solicitar o certificado.",
        )
        self.assertFalse(Educador.objects.filter(cpf="52998224725").exists())

    def test_registration_ignores_removed_opt_out_when_course_is_selected(self):
        self.submit_registration(
            self.registration_data(nao_solicitar_certificado="on"),
        )

    def test_success_page_does_not_offer_login(self):
        response = self.client.get(reverse("cadastro_educador_success"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O cadastro foi concluído.")
        self.assertNotContains(response, "Fazer login")
        self.assertNotContains(response, "utilize o CPF como usuário e senha")

    def test_registration_requires_complete_address(self):
        data = self.registration_data()
        address_fields = (
            "endereco_cep",
            "endereco_logradouro",
            "endereco_numero",
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

    def test_registration_accepts_empty_address_complement(self):
        self.submit_registration(
            self.registration_data(endereco_complemento=""),
        )

        educador = Educador.objects.get(cpf="52998224725")
        self.assertEqual(educador.endereco.complemento, "")

    def test_registration_requires_complete_identification(self):
        data = self.registration_data()
        identification_fields = (
            "nome_completo",
            "data_nascimento",
            "email",
            "email_confirmacao",
            "cor_raca",
            "genero",
        )
        for field_name in identification_fields:
            data.pop(field_name)

        response = self.client.post(reverse("cadastro_educador"), data)

        self.assertEqual(response.status_code, 200)
        for field_name in identification_fields:
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

        self.submit_registration(
            self.registration_data(atuacoes_json=json.dumps(atuacoes)),
        )

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

    def test_existing_cpf_without_assignments_can_complete_registration(self):
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
        self.assertEqual(usuario.get_full_name(), "Educador Existente")
        self.assertEqual(usuario.email, "existente@example.com")
        educador.refresh_from_db()
        self.assertEqual(educador.cor_raca, self.cor_raca)
        self.assertTrue(Endereco.objects.filter(educador=educador).exists())
        self.assertTrue(usuario.check_password("senha-segura"))

    def test_person_cannot_submit_a_second_registration(self):
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

        self.assertEqual(response.status_code, 200)
        self.assertIn("cpf", response.context["form"].errors)
        self.assertEqual(
            EducadorEscola.objects.filter(funcao_educador__educador=educador).count(),
            1,
        )
        self.assertEqual(Endereco.objects.filter(educador=educador).count(), 1)
        educador.endereco.refresh_from_db()
        self.assertEqual(educador.endereco.logradouro, "Rua do Cadastro")
        self.assertEqual(educador.endereco.numero, "20")

    def test_repeated_submission_keeps_only_first_registration(self):
        self.submit_registration(self.registration_data())
        educador = Educador.objects.get(cpf="52998224725")
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(
                cpf="52998224725",
                endereco_logradouro="Endereço alterado",
                curso_certificado=[self.outro_curso_certificado.pk],
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("cpf", response.context["form"].errors)
        self.assertEqual(FuncaoEducador.objects.filter(educador=educador).count(), 1)
        self.assertEqual(educador.endereco.logradouro, "Avenida Fernandes Lima")
        self.assertEqual(list(educador.cursos_certificados.all()), [self.curso_certificado])

    def test_existing_registration_can_be_edited_without_duplicate_records(self):
        self.submit_registration(self.registration_data())
        educador = Educador.objects.get(cpf="52998224725")
        usuario = educador.usuario
        original_assignment = EducadorEscola.objects.get(funcao_educador__educador=educador)
        total_users = User.objects.count()

        response = self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf=educador.cpf,
            nome_completo="Maria Nome Corrigido",
            email="corrigido@example.com",
            endereco_logradouro="Rua Corrigida",
            genero=self.genero_nao_binario.pk,
            curso_certificado=[self.outro_curso_certificado.pk],
            atuacoes_json=json.dumps([self.assignment_data(tempo_atuacao="mais_6_anos")]),
        ))

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        educador.refresh_from_db()
        usuario.refresh_from_db()
        original_assignment.refresh_from_db()
        self.assertEqual(User.objects.count(), total_users)
        self.assertEqual(educador.nome_completo, "Maria Nome Corrigido")
        self.assertEqual(usuario.get_full_name(), "Maria Nome Corrigido")
        self.assertEqual(usuario.email, "corrigido@example.com")
        self.assertTrue(usuario.check_password("52998224725"))
        self.assertEqual(educador.endereco.logradouro, "Rua Corrigida")
        self.assertEqual(educador.genero, self.genero_nao_binario)
        self.assertEqual(list(educador.cursos_certificados.all()), [self.outro_curso_certificado])
        self.assertEqual(original_assignment.tempo_atuacao, "mais_6_anos")
        self.assertEqual(FuncaoEducador.objects.filter(educador=educador).count(), 1)
        self.assertEqual(Endereco.objects.filter(educador=educador).count(), 1)

    def test_edit_replaces_removed_assignments(self):
        self.submit_registration(self.registration_data())
        original_assignment = EducadorEscola.objects.get()
        response = self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf="52998224725",
            atuacoes_json=json.dumps([self.assignment_data(
                funcao_caracterizacao_turmas=self.ensino_medio.pk,
            )]),
        ))
        self.assertRedirects(response, reverse("cadastro_educador_success"))
        self.assertFalse(EducadorEscola.objects.filter(pk=original_assignment.pk).exists())
        self.assertEqual(FuncaoEducador.objects.count(), 1)
        self.assertEqual(EducadorEscola.objects.get().funcao_caracterizacao_turmas, self.ensino_medio)

    def test_invalid_edit_keeps_existing_data_and_edit_mode(self):
        self.submit_registration(self.registration_data())
        response = self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf="52998224725", email_confirmacao="outro@example.com",
            endereco_logradouro="Rua Corrigida", atuacoes_json="[]",
        ))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].edicao)
        self.assertContains(response, "Salvar Alterações")
        self.assertEqual(Endereco.objects.get().logradouro, "Avenida Fernandes Lima")
        self.assertEqual(FuncaoEducador.objects.count(), 1)

    def test_edit_requires_matching_cpf_and_unique_email(self):
        self.submit_registration(self.registration_data())
        response = self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf="11111111111",
        ))
        self.assertIn("cpf", response.context["form"].errors)
        User.objects.create_user(username="outro", email="outro@example.com")
        response = self.client.post(reverse("cadastro_educador"), self.registration_data(
            editar_cpf="52998224725", email="outro@example.com",
        ))
        self.assertFormError(response.context["form"], "email", "Já existe um usuário cadastrado com este e-mail.")
        self.assertEqual(User.objects.get(username="52998224725").email, "maria.educadora@example.com")

    def test_edit_lookup_loads_saved_data_and_assignments(self):
        self.submit_registration(self.registration_data())
        url = reverse("cadastro_educador_cpf_lookup")
        response = self.client.get(url, {"cpf": "52998224725"})
        self.assertTrue(response.json()["registered"])
        self.assertNotIn("dados", response.json())
        response = self.client.get(url, {"cpf": "52998224725", "editar": "1"})
        dados = response.json()["dados"]
        self.assertEqual(dados["nome_completo"], "Maria Educadora da Silva")
        self.assertEqual(dados["endereco_logradouro"], "Avenida Fernandes Lima")
        self.assertEqual(dados["curso_certificado"], [self.curso_certificado.pk])
        self.assertEqual(len(dados["atuacoes"]), 1)
        for key, value in self.assignment_data().items():
            self.assertEqual(dados["atuacoes"][0][key], value)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_cpf_username_without_profile_cpf_reuses_existing_account(self):
        usuario = User.objects.create_user(username="52998224725")
        total_usuarios = User.objects.count()
        lookup = self.client.get(reverse("cadastro_educador_cpf_lookup"), {"cpf": "52998224725"})
        self.assertTrue(lookup.json()["exists"])
        self.assertFalse(lookup.json()["registered"])
        response = self.client.post(reverse("cadastro_educador"), self.registration_data())
        self.assertRedirects(response, reverse("cadastro_educador_success"))
        self.assertEqual(User.objects.count(), total_usuarios)
        usuario.educador.refresh_from_db()
        self.assertEqual(usuario.educador.cpf, "52998224725")
        self.assertTrue(FuncaoEducador.objects.filter(educador=usuario.educador).exists())
        lookup = self.client.get(reverse("cadastro_educador_cpf_lookup"), {"cpf": "52998224725"})
        self.assertTrue(lookup.json()["exists"])
        self.assertTrue(lookup.json()["registered"])
        self.assertNotIn("dados", lookup.json())

    def test_cpf_lookup_prefills_personal_data_for_incomplete_registration(self):
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
        educador.cursos_certificados.add(self.curso_certificado)
        Endereco.objects.create(
            educador=educador, cep="57000000", logradouro="Rua Existente", numero="20",
            complemento="Casa", bairro="Centro", cidade=self.cidade,
        )

        response = self.client.get(reverse("cadastro_educador_cpf_lookup"), {"cpf": "529.982.247-25"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "valid": True,
                "exists": True,
                "registered": False,
                "dados": {
                    "nome_completo": "Pessoa Localizada",
                    "email": "consulta@example.com",
                    "data_nascimento": "1985-08-20",
                    "cor_raca": self.cor_raca.pk,
                    "genero": self.genero_nao_binario.pk,
                    "curso_certificado": [self.curso_certificado.pk],
                    "endereco_cep": "57000000",
                    "endereco_logradouro": "Rua Existente",
                    "endereco_numero": "20",
                    "endereco_complemento": "Casa",
                    "endereco_bairro": "Centro",
                    "endereco_estado": self.estado.pk,
                    "endereco_cidade": self.cidade.pk,
                },
            },
        )
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_existing_account_cannot_use_another_accounts_email(self):
        usuario = User.objects.create_user(username="52998224725", email="existente@example.com")
        User.objects.create_user(username="outro", email="outro@example.com")
        response = self.client.post(
            reverse("cadastro_educador"), self.registration_data(email="outro@example.com"),
        )
        self.assertFormError(response.context["form"], "email", "Já existe um usuário cadastrado com este e-mail.")
        self.assertFalse(FuncaoEducador.objects.filter(educador=usuario.educador).exists())

    def test_registration_rejects_different_email_confirmation(self):
        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(email_confirmacao="outro@example.com"),
        )

        self.assertFormError(
            response.context["form"], "email_confirmacao", "Os e-mails informados não são iguais."
        )
        self.assertFalse(User.objects.filter(username="52998224725").exists())
        self.assertFalse(EducadorEscola.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_registration_requires_email_confirmation(self):
        response = self.client.post(
            reverse("cadastro_educador"), self.registration_data(email_confirmacao="")
        )

        self.assertFormError(response.context["form"], "email_confirmacao", "Este campo é obrigatório.")
        self.assertFalse(User.objects.filter(username="52998224725").exists())

    def test_registration_rejects_invalid_email_confirmation(self):
        response = self.client.post(
            reverse("cadastro_educador"), self.registration_data(email_confirmacao="email-invalido")
        )

        self.assertIn("email_confirmacao", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="52998224725").exists())

    def test_registration_compares_email_ignoring_case_and_outer_spaces(self):
        self.submit_registration(
            self.registration_data(
                email=" Maria.Educadora@EXAMPLE.COM ",
                email_confirmacao="maria.educadora@example.com",
            )
        )

        self.assertEqual(User.objects.get(username="52998224725").email, "maria.educadora@example.com")

    def test_existing_cpf_requires_matching_submitted_emails(self):
        usuario = User.objects.create_user(username="52998224725", email="existente@example.com")
        educador = usuario.educador
        educador.cpf = "52998224725"
        educador.save(update_fields=("cpf",))

        response = self.client.post(
            reverse("cadastro_educador"),
            self.registration_data(email_confirmacao="outro@example.com"),
        )

        self.assertFormError(
            response.context["form"], "email_confirmacao", "Os e-mails informados não são iguais."
        )
        self.assertFalse(EducadorEscola.objects.exists())
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, "existente@example.com")

    def test_registration_succeeds_when_email_service_is_unavailable(self):
        with patch("core.views.cadastro_educador.send_mail", side_effect=OSError("SMTP indisponível")) as send_mail:
            response = self.client.post(
                reverse("cadastro_educador"), self.registration_data()
            )

        self.assertRedirects(response, reverse("cadastro_educador_success"))
        send_mail.assert_not_called()
        self.assertTrue(User.objects.filter(username="52998224725").exists())
        self.assertTrue(EducadorEscola.objects.filter(funcao_educador__educador__cpf="52998224725").exists())
        self.assertFalse(CadastroPendente.objects.exists())

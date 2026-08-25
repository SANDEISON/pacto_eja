from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cidade, CorRaca, Educador, EducadorEscola, Endereco, Estado, Formacao, FuncaoEducador


User = get_user_model()


class EducadorModelTests(TestCase):
    def test_profile_is_created_with_user(self):
        user = User.objects.create_user(
            username="pessoa@example.com",
            email="pessoa@example.com",
            first_name="Maria",
            last_name="Educadora",
            password="SenhaForte2026!",
        )
        self.assertTrue(Educador.objects.filter(usuario=user).exists())
        self.assertEqual(user.educador.nome_completo, "Maria Educadora")

    def test_database_tables_use_educator_names(self):
        self.assertEqual(Educador._meta.db_table, "core_educador")
        self.assertEqual(EducadorEscola._meta.db_table, "core_educadorescola")
        self.assertEqual(Endereco._meta.db_table, "core_endereco")
        self.assertEqual(Formacao._meta.db_table, "core_formacao")
        self.assertEqual(FuncaoEducador._meta.db_table, "core_funcaoeducador")
        field_names = {field.name for field in EducadorEscola._meta.get_fields()}
        self.assertNotIn("estado", field_names)
        self.assertNotIn("educador", field_names)
        self.assertIn("funcao_educador", field_names)
        self.assertIn("funcao_caracterizacao_turmas", field_names)
        self.assertIn(
            "educador_escola",
            {field.name for field in FuncaoEducador._meta.get_fields()},
        )


class ProfileViewTests(TestCase):
    def setUp(self):
        self.cor_raca = CorRaca.objects.get(nome="Indígena")
        self.estado = Estado.objects.get(sigla="AL")
        self.cidade = Cidade.objects.get(estado=self.estado, nome_cidade="Maceió")
        self.user = User.objects.create_user(
            username="maria@example.com",
            email="maria@example.com",
            first_name="Maria",
            password="SenhaForte2026!",
        )
        self.client.force_login(self.user)

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("profile"))
        self.assertRedirects(response, f"{reverse('accounts:signin')}?next={reverse('profile')}")

    def test_profile_displays_account_tabs(self):
        response = self.client.get(reverse("profile"))

        self.assertContains(response, "Pessoais")
        self.assertContains(response, "Formação")
        self.assertContains(response, "Endereço")
        self.assertContains(response, "Contatos")
        self.assertContains(response, "Cor/raça")
        self.assertContains(response, 'id="id_educador-cor_raca"')
        self.assertContains(response, "Nome social")
        self.assertContains(response, 'id="id_educador-nome_social"')
        self.assertContains(response, 'id="id_endereco-cep"')
        self.assertContains(response, 'id="id_endereco-logradouro"')
        self.assertContains(response, 'id="id_endereco-estado"')
        self.assertContains(response, 'id="id_endereco-cidade"')
        self.assertContains(response, 'id="id_formacao-TOTAL_FORMS"')
        self.assertContains(response, 'id="add-formation"')
        self.assertContains(response, 'id="formation-records-block"')
        self.assertContains(response, 'aria-label="Registros de formações"')
        self.assertContains(response, 'href="/perfil/?adicionar_formacao=1#education-pane"')
        self.assertContains(response, 'id="formation-modal-formacao-__prefix__"')
        self.assertContains(response, 'data-save-formation-label')
        self.assertContains(response, "Adicionar à lista")
        self.assertContains(response, 'data-edit-formation')
        self.assertContains(response, 'data-remove-formation')
        self.assertContains(response, 'class="nav-link active" id="personal-tab"')
        self.assertContains(response, 'class="tab-pane active" id="personal-pane"')

    def profile_data(self, **overrides):
        data = {
            "user-full_name": "Maria",
            "user-email": "maria@example.com",
            "educador-nome_social": "",
            "educador-cpf": "",
            "educador-data_nascimento": "",
            "educador-genero": "",
            "educador-cor_raca": "",
            "educador-telefone": "",
            "educador-estado_civil": "",
        }
        data.update(overrides)
        return data

    def test_user_can_add_multiple_formations(self):
        response = self.client.post(
            reverse("profile"),
            self.profile_data(
                **{
                    "formacao-TOTAL_FORMS": "2",
                    "formacao-INITIAL_FORMS": "0",
                    "formacao-MIN_NUM_FORMS": "0",
                    "formacao-MAX_NUM_FORMS": "1000",
                    "formacao-0-nivel": Formacao.Nivel.GRADUACAO_LICENCIATURA,
                    "formacao-0-nome_curso": "Pedagogia",
                    "formacao-0-instituicao": "Universidade Federal de Alagoas",
                    "formacao-0-situacao": Formacao.Situacao.CONCLUIDO,
                    "formacao-0-modalidade": Formacao.Modalidade.PRESENCIAL,
                    "formacao-0-ano_inicio": "2010",
                    "formacao-0-ano_conclusao": "2014",
                    "formacao-1-nivel": Formacao.Nivel.MESTRADO,
                    "formacao-1-nome_curso": "Educação",
                    "formacao-1-instituicao": "Universidade Federal da Paraíba",
                    "formacao-1-situacao": Formacao.Situacao.CURSANDO,
                    "formacao-1-modalidade": Formacao.Modalidade.PRESENCIAL,
                    "formacao-1-ano_inicio": "2025",
                    "formacao-1-ano_conclusao": "",
                }
            ),
        )

        self.assertRedirects(response, reverse("profile"))
        formacoes = self.user.educador.formacoes.all()
        self.assertEqual(formacoes.count(), 2)
        self.assertTrue(formacoes.filter(nome_curso="Pedagogia", ano_conclusao=2014).exists())
        self.assertTrue(formacoes.filter(nome_curso="Educação", situacao=Formacao.Situacao.CURSANDO).exists())

    def test_add_formation_button_has_server_fallback(self):
        response = self.client.get(f'{reverse("profile")}?adicionar_formacao=1')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_formacao-0-nivel"')
        self.assertContains(response, 'id="formation-modal-formacao-0"')
        self.assertContains(response, 'data-formation-modal-title')
        self.assertContains(response, 'name="formacao-TOTAL_FORMS" value="1"')
        self.assertContains(response, 'class="nav-link active" id="education-tab"')
        self.assertContains(response, 'class="tab-pane active" id="education-pane"')
        self.assertNotContains(response, "Seu perfil foi atualizado com sucesso.")
        self.assertFalse(self.user.educador.formacoes.exists())

    def test_user_can_update_and_remove_formations(self):
        pedagogia = Formacao.objects.create(
            educador=self.user.educador,
            nivel=Formacao.Nivel.GRADUACAO_LICENCIATURA,
            nome_curso="Pedagogia",
            instituicao="UFAL",
            situacao=Formacao.Situacao.CONCLUIDO,
            modalidade=Formacao.Modalidade.PRESENCIAL,
            ano_inicio=2010,
            ano_conclusao=2014,
        )
        especializacao = Formacao.objects.create(
            educador=self.user.educador,
            nivel=Formacao.Nivel.ESPECIALIZACAO,
            nome_curso="Educação de Jovens e Adultos",
            instituicao="UFPB",
            situacao=Formacao.Situacao.CONCLUIDO,
            ano_inicio=2018,
            ano_conclusao=2019,
        )

        response = self.client.post(
            reverse("profile"),
            self.profile_data(
                **{
                    "formacao-TOTAL_FORMS": "2",
                    "formacao-INITIAL_FORMS": "2",
                    "formacao-MIN_NUM_FORMS": "0",
                    "formacao-MAX_NUM_FORMS": "1000",
                    "formacao-0-id": pedagogia.pk,
                    "formacao-0-nivel": Formacao.Nivel.GRADUACAO_LICENCIATURA,
                    "formacao-0-nome_curso": "Licenciatura em Pedagogia",
                    "formacao-0-instituicao": "UFAL",
                    "formacao-0-situacao": Formacao.Situacao.CONCLUIDO,
                    "formacao-0-modalidade": Formacao.Modalidade.PRESENCIAL,
                    "formacao-0-ano_inicio": "2010",
                    "formacao-0-ano_conclusao": "2014",
                    "formacao-1-id": especializacao.pk,
                    "formacao-1-DELETE": "on",
                }
            ),
        )

        self.assertRedirects(response, reverse("profile"))
        pedagogia.refresh_from_db()
        self.assertEqual(pedagogia.nome_curso, "Licenciatura em Pedagogia")
        self.assertFalse(Formacao.objects.filter(pk=especializacao.pk).exists())

    def test_completed_formation_requires_valid_completion_year(self):
        response = self.client.post(
            reverse("profile"),
            self.profile_data(
                **{
                    "formacao-TOTAL_FORMS": "1",
                    "formacao-INITIAL_FORMS": "0",
                    "formacao-MIN_NUM_FORMS": "0",
                    "formacao-MAX_NUM_FORMS": "1000",
                    "formacao-0-nivel": Formacao.Nivel.GRADUACAO_LICENCIATURA,
                    "formacao-0-nome_curso": "Pedagogia",
                    "formacao-0-instituicao": "UFAL",
                    "formacao-0-situacao": Formacao.Situacao.CONCLUIDO,
                    "formacao-0-modalidade": Formacao.Modalidade.PRESENCIAL,
                    "formacao-0-ano_inicio": "2020",
                    "formacao-0-ano_conclusao": "2019",
                }
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "não pode ser anterior ao ano de início")
        self.assertContains(response, 'class="nav-link active" id="education-tab"')
        self.assertContains(response, 'class="tab-pane active" id="education-pane"')
        self.assertFalse(self.user.educador.formacoes.exists())

    def test_user_can_update_account_and_personal_data(self):
        response = self.client.post(
            reverse("profile"),
            {
                "user-full_name": "Maria da Silva",
                "user-email": "maria.silva@example.com",
                "educador-nome_social": "Maria Silva",
                "educador-cpf": "529.982.247-25",
                "educador-data_nascimento": "1990-05-12",
                "educador-genero": Educador.Genero.FEMININO,
                "educador-cor_raca": self.cor_raca.pk,
                "educador-telefone": "(82) 99999-1234",
                "educador-estado_civil": Educador.EstadoCivil.CASADO,
                "endereco-cep": "57000-000",
                "endereco-logradouro": "Avenida Fernandes Lima",
                "endereco-numero": "1000-A",
                "endereco-complemento": "Apto. 101",
                "endereco-bairro": "Farol",
                "endereco-estado": self.estado.pk,
                "endereco-cidade": self.cidade.pk,
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.user.educador.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Maria da Silva")
        self.assertEqual(self.user.email, "maria.silva@example.com")
        self.assertEqual(self.user.username, "maria@example.com")
        self.assertEqual(self.user.educador.nome_completo, "Maria da Silva")
        self.assertEqual(self.user.educador.nome_social, "Maria Silva")
        self.assertEqual(self.user.educador.cpf, "52998224725")
        self.assertEqual(self.user.educador.data_nascimento, date(1990, 5, 12))
        self.assertEqual(self.user.educador.cor_raca, self.cor_raca)
        endereco = self.user.educador.endereco
        self.assertEqual(endereco.cep, "57000000")
        self.assertEqual(endereco.logradouro, "Avenida Fernandes Lima")
        self.assertEqual(endereco.numero, "1000-A")
        self.assertEqual(endereco.complemento, "Apto. 101")
        self.assertEqual(endereco.bairro, "Farol")
        self.assertEqual(endereco.cidade, self.cidade)
        self.assertEqual(endereco.uf, "AL")

    def test_invalid_cpf_and_future_birth_date_are_rejected(self):
        response = self.client.post(
            reverse("profile"),
            {
                "user-full_name": "Maria",
                "user-email": "maria@example.com",
                "educador-nome_social": "",
                "educador-cpf": "111.111.111-11",
                "educador-data_nascimento": (date.today() + timedelta(days=1)).isoformat(),
                "educador-genero": "",
                "educador-cor_raca": "",
                "educador-telefone": "",
                "educador-estado_civil": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe um CPF válido")
        self.assertContains(response, "não pode estar no futuro")

    def test_user_can_change_password_without_losing_session(self):
        response = self.client.post(
            reverse("profile_password_change"),
            {"old_password": "SenhaForte2026!", "new_password1": "NovaSenha2026!", "new_password2": "NovaSenha2026!"},
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaSenha2026!"))
        self.assertIn("_auth_user_id", self.client.session)

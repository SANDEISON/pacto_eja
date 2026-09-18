from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import (
    Atividade,
    Cidade,
    Coautor,
    CorRaca,
    EducadorEstadoCivil,
    EducadorGenero,
    Endereco,
    Estado,
    Formacao,
    Inscricao,
    Modalidade,
    Nivel,
    ProgramacaoSala,
    RascunhoInscricao,
    Refeicao,
    Sala,
    Situacao,
    TematicaSala,
    Trabalho,
    TrabalhoMunicipio,
)


class AtividadeFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="participante@example.com",
            email="participante@example.com",
            first_name="Participante",
            password="SenhaForte2026!",
        )
        self.coauthor_user = get_user_model().objects.create_user(
            username="coautora@example.com",
            email="coautora@example.com",
            first_name="Pessoa",
            last_name="Coautora",
            password="SenhaForte2026!",
        )
        agora = timezone.now()
        self.atividade = Atividade.objects.create(
            tipo=Atividade.Tipo.EVENTO,
            titulo="Seminário de Educação de Jovens e Adultos",
            descricao="Encontro para troca de experiências.",
            local="Auditório central",
            data_inicio=agora + timedelta(days=20),
            data_fim=agora + timedelta(days=21),
            inscricoes_inicio=agora - timedelta(days=1),
            inscricoes_fim=agora + timedelta(days=10),
            permite_submissao=True,
            submissoes_fim=agora + timedelta(days=12),
        )
        self.client.force_login(self.user)

    def personal_data(self):
        estado = Estado.objects.get(sigla="AL")
        cidade = Cidade.objects.filter(estado=estado).first()
        nivel = Nivel.objects.first()
        situacao = Situacao.objects.first()
        return {
            "usuario-full_name": "Participante da Silva",
            "usuario-email": "participante@example.com",
            "dados-cpf": "529.982.247-25",
            "dados-modalidade_inscricao": "presencial",
            "dados-data_nascimento": "1990-05-12",
            "dados-telefone": "(82) 99999-9999",
            "dados-genero": EducadorGenero.objects.first().pk,
            "dados-cor_raca": CorRaca.objects.first().pk,
            "dados-estado_civil": EducadorEstadoCivil.objects.first().pk,
            "endereco-cep": "57000-000",
            "endereco-logradouro": "Rua da Inscrição",
            "endereco-numero": "100",
            "endereco-complemento": "",
            "endereco-bairro": "Centro",
            "endereco-estado": estado.pk,
            "endereco-cidade": cidade.pk,
            "formacao-TOTAL_FORMS": "1",
            "formacao-INITIAL_FORMS": "0",
            "formacao-MIN_NUM_FORMS": "0",
            "formacao-MAX_NUM_FORMS": "1000",
            "formacao-0-nivel": nivel.pk,
            "formacao-0-nome_curso": "Pedagogia",
            "formacao-0-instituicao": "Universidade de Teste",
            "formacao-0-situacao": situacao.pk,
            "formacao-0-modalidade": "",
            "formacao-0-ano_inicio": "2020",
            "formacao-0-ano_conclusao": "2024",
        }

    def academic_work_data(self):
        return {
            "trabalho-eixo_tematico": "Práticas pedagógicas na EJA",
            "trabalho-resumo": "Relato acadêmico sobre saberes e práticas na EJA.",
            "trabalho-palavras_chave": "EJA; saberes; práticas pedagógicas",
            "trabalho-aceitou_termo_relato": "on",
            "trabalho-aceitou_termo_cessao": "on",
            "trabalho-aceitou_originalidade": "on",
        }

    def create_programacao(self, modalidade, nome_sala, *, turno=None, data=None):
        return ProgramacaoSala.objects.create(
            sala=Sala.objects.create(nome=nome_sala),
            data=data or timezone.localdate(self.atividade.data_inicio),
            turno=turno or ProgramacaoSala.Turno.MANHA,
            modalidade=modalidade,
            link="https://example.com/sala" if modalidade == ProgramacaoSala.Modalidade.ONLINE else "",
            tematica=TematicaSala.objects.first(),
            descricao=f"Programação {modalidade}",
            quantidade_max_participantes=50,
        )

    def test_dashboard_shows_activity_with_open_registration(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.atividade.titulo)
        self.assertContains(response, "Inscrever-se")
        self.assertContains(response, "google.com/maps/search/")

    def test_activity_modality_validates_required_access_information(self):
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.ONLINE
        self.atividade.local = ""
        self.atividade.full_clean()

        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.local = ""
        with self.assertRaises(ValidationError) as error:
            self.atividade.full_clean()
        self.assertIn("local", error.exception.message_dict)

    def test_registration_page_links_address_to_maps(self):
        response = self.client.get(reverse("atividade_inscricao", args=[self.atividade.pk]))
        self.assertContains(response, "Inscrição em evento")
        self.assertContains(response, "docs/termo_uso_publicacao_trabalho.pdf")
        self.assertContains(response, "docs/termo_cessao_direitos_autorais.pdf")
        self.assertContains(response, "Continuar")
        self.assertContains(response, "Deseja cadastrar um trabalho neste evento?")
        self.assertContains(response, 'data-registration-step="modalidade"')
        self.assertContains(response, "Etapa 2")
        self.assertContains(response, 'data-registration-step="decisao"')
        self.assertContains(response, "Etapa 3")
        self.assertContains(response, 'data-registration-step="trabalho"')
        self.assertContains(response, "Etapa 4")
        self.assertContains(response, "Escolha pelo menos uma sala para montar sua programação")
        self.assertContains(response, "data-registration-modality-continue hidden")
        self.assertContains(response, 'data-work-choice="yes"')
        self.assertContains(response, 'data-work-choice="no"')
        self.assertContains(response, 'data-registration-finish hidden')
        self.assertContains(response, 'data-registration-submit hidden')
        self.assertContains(response, "é necessário possuir cadastro ativo no sistema Pacto EJA")
        self.assertNotContains(response, "Adicionar coautor")
        self.assertContains(response, 'for="coauthor-search">Buscar coautor</label>', count=1)
        self.assertContains(response, 'class="coauthor-row" hidden')
        self.assertContains(response, "Abrir endereço no Google Maps")
        self.assertContains(response, "Auditório central")
        self.assertContains(response, "Modalidade de participação")
        self.assertContains(response, "Selecione a modalidade de participação")
        self.assertContains(
            response,
            '<option value="" selected>Selecione a modalidade de participação</option>',
            html=True,
        )
        self.assertContains(response, "Presencial")
        self.assertContains(response, "Salvar e continuar depois")

    def test_user_can_save_incomplete_registration_and_resume_it(self):
        url = reverse("atividade_inscricao", args=[self.atividade.pk])
        response = self.client.post(
            url,
            {
                "acao": "salvar_rascunho",
                "etapa_atual": "pessoal",
                "usuario-full_name": "Nome ainda incompleto",
                "usuario-email": "participante@example.com",
                "dados-cpf": "529.982",
                "endereco-logradouro": "Rua iniciada",
                "formacao-TOTAL_FORMS": "1",
                "formacao-INITIAL_FORMS": "0",
                "formacao-MIN_NUM_FORMS": "0",
                "formacao-MAX_NUM_FORMS": "1000",
                "formacao-0-nome_curso": "Pedagogia em andamento",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(response, "Rascunho salvo")
        self.assertContains(response, "Continuar inscrição")
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade, usuario=self.user).exists())
        rascunho = RascunhoInscricao.objects.get(
            atividade=self.atividade,
            usuario=self.user,
        )
        self.assertEqual(rascunho.dados["usuario-full_name"], ["Nome ainda incompleto"])
        self.assertEqual(rascunho.dados["endereco-logradouro"], ["Rua iniciada"])

        resumed = self.client.get(url)
        self.assertEqual(resumed.context["dados_rascunho"], rascunho.dados)
        self.assertEqual(resumed.context["active_tab"], "pessoal")
        self.assertContains(resumed, "registration-draft-data")

    def test_finishing_registration_removes_saved_draft(self):
        RascunhoInscricao.objects.create(
            atividade=self.atividade,
            usuario=self.user,
            dados={"usuario-full_name": ["Nome temporário"]},
        )

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data() | {"acao": "inscrever"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(
            RascunhoInscricao.objects.filter(
                atividade=self.atividade,
                usuario=self.user,
            ).exists()
        )
    def test_user_selects_modality_when_activity_accepts_online_and_in_person(self):
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.save(update_fields=("modalidade",))
        url = reverse("atividade_inscricao", args=[self.atividade.pk])

        page = self.client.get(url)
        response = self.client.post(
            url,
            self.personal_data() | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": "online",
            },
        )

        self.assertContains(page, "On-line")
        self.assertContains(page, "Presencial")
        self.assertRedirects(response, reverse("dashboard"))
        inscricao = Inscricao.objects.get(atividade=self.atividade, usuario=self.user)
        self.assertEqual(inscricao.modalidade, Inscricao.Modalidade.ONLINE)

    def test_registration_shows_programs_by_modality_and_saves_multiple_choices(self):
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.save(update_fields=("modalidade",))
        online_um = self.create_programacao(ProgramacaoSala.Modalidade.ONLINE, "Sala virtual 1")
        online_dois = self.create_programacao(
            ProgramacaoSala.Modalidade.ONLINE,
            "Sala virtual 2",
            turno=ProgramacaoSala.Turno.TARDE,
        )
        presencial = self.create_programacao(ProgramacaoSala.Modalidade.PRESENCIAL, "Auditório 1")
        self.atividade.programacoes.set((online_um, online_dois, presencial))
        url = reverse("atividade_inscricao", args=[self.atividade.pk])

        page = self.client.get(url)
        response = self.client.post(
            url,
            self.personal_data()
            | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": Inscricao.Modalidade.ONLINE,
                "dados-programacoes": [str(online_um.pk), str(online_dois.pk)],
            },
        )

        self.assertContains(page, "Escolha as programações")
        self.assertContains(page, "Selecione pelo menos uma sala e, no máximo, uma por turno em cada data.")
        self.assertContains(page, 'class="program-card-content"', count=3)
        self.assertContains(page, 'data-registration-programs-count')
        self.assertContains(page, 'name="dados-programacoes"', count=3)
        self.assertContains(page, 'data-modalidade="online"', count=2)
        self.assertContains(page, 'data-modalidade="presencial"', count=1)
        self.assertNotContains(page, 'data-registration-program-theme-filter')
        self.assertContains(page, 'data-registration-program-date-filter')
        self.assertNotContains(page, 'class="program-card-theme"')
        self.assertContains(page, f'data-tematica="{online_um.tematica_id}"', count=3)
        self.assertContains(page, f'data-data="{online_um.data:%Y-%m-%d}"', count=3)
        self.assertContains(page, 'data-turno="manha"', count=2)
        self.assertContains(page, 'data-turno="tarde"', count=1)
        self.assertRedirects(response, reverse("dashboard"))
        inscricao = Inscricao.objects.get(atividade=self.atividade, usuario=self.user)
        self.assertQuerySetEqual(
            inscricao.programacoes.order_by("pk"),
            [online_um, online_dois],
        )

    def test_registration_requires_a_program_instead_of_the_modality_filter(self):
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.save(update_fields=("modalidade",))
        online = self.create_programacao(
            ProgramacaoSala.Modalidade.ONLINE,
            "Sala virtual obrigatória",
        )
        self.atividade.programacoes.add(online)
        url = reverse("atividade_inscricao", args=[self.atividade.pk])

        page = self.client.get(url)
        invalid_response = self.client.post(
            url,
            self.personal_data()
            | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": "",
            },
        )
        valid_response = self.client.post(
            url,
            self.personal_data()
            | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": "",
                "dados-programacoes": [str(online.pk)],
            },
        )

        self.assertContains(page, "Filtrar por modalidade (opcional)")
        self.assertContains(page, "Todas as modalidades")
        self.assertNotContains(page, "Filtrar por modalidade (opcional) <span class=\"text-danger\">*</span>")
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFormError(
            invalid_response.context["dados_form"],
            "programacoes",
            "Selecione pelo menos uma sala disponível.",
        )
        self.assertEqual(invalid_response.context["active_tab"], "modalidade")
        self.assertRedirects(valid_response, reverse("dashboard"))
        inscricao = Inscricao.objects.get(atividade=self.atividade, usuario=self.user)
        self.assertEqual(inscricao.modalidade, Inscricao.Modalidade.ONLINE)
        self.assertQuerySetEqual(inscricao.programacoes.all(), [online])

    def test_registration_allows_online_and_in_person_programs_without_time_conflict(self):
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.save(update_fields=("modalidade",))
        online = self.create_programacao(ProgramacaoSala.Modalidade.ONLINE, "Sala virtual 3")
        presencial = self.create_programacao(
            ProgramacaoSala.Modalidade.PRESENCIAL,
            "Auditório 2",
            turno=ProgramacaoSala.Turno.TARDE,
        )
        self.atividade.programacoes.add(online, presencial)

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data()
            | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": Inscricao.Modalidade.ONLINE,
                "dados-programacoes": [str(online.pk), str(presencial.pk)],
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        inscricao = Inscricao.objects.get(atividade=self.atividade, usuario=self.user)
        self.assertQuerySetEqual(
            inscricao.programacoes.order_by("pk"),
            sorted((online, presencial), key=lambda programacao: programacao.pk),
        )

    def test_registration_rejects_two_programs_in_the_same_date_and_shift(self):
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.save(update_fields=("modalidade",))
        online = self.create_programacao(ProgramacaoSala.Modalidade.ONLINE, "Sala virtual 4")
        presencial = self.create_programacao(
            ProgramacaoSala.Modalidade.PRESENCIAL,
            "Auditório 3",
        )
        self.atividade.programacoes.add(online, presencial)

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data()
            | {
                "acao": "inscrever",
                "dados-programacoes": [str(online.pk), str(presencial.pk)],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["dados_form"],
            "programacoes",
            "Escolha apenas uma programação por turno em cada data.",
        )
        self.assertEqual(response.context["active_tab"], "modalidade")
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade).exists())

    def test_registration_rejects_program_not_available_in_activity(self):
        externa = self.create_programacao(ProgramacaoSala.Modalidade.PRESENCIAL, "Sala externa")

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data()
            | {"acao": "inscrever", "dados-programacoes": [str(externa.pk)]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "não é uma das escolhas disponíveis",
            response.context["dados_form"].errors["programacoes"][0],
        )
        self.assertEqual(response.context["active_tab"], "modalidade")
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade).exists())

    def test_user_can_select_multiple_available_meals(self):
        data_refeicao = timezone.localdate(self.atividade.data_inicio)
        cafe = Refeicao.objects.create(
            atividade=self.atividade,
            tipo=Refeicao.Tipo.CAFE_DA_MANHA,
            data=data_refeicao,
            horario="08:00",
        )
        almoco = Refeicao.objects.create(
            atividade=self.atividade,
            tipo=Refeicao.Tipo.ALMOCO,
            data=data_refeicao,
            horario="12:00",
        )
        url = reverse("atividade_inscricao", args=[self.atividade.pk])

        page = self.client.get(url)
        response = self.client.post(
            url,
            self.personal_data()
            | {
                "acao": "inscrever",
                "dados-refeicoes": [str(cafe.pk), str(almoco.pk)],
            },
        )

        self.assertContains(page, "Escolha as refeições")
        self.assertContains(page, "Café da manhã")
        self.assertContains(page, "Almoço")
        self.assertRedirects(response, reverse("dashboard"))
        inscricao = Inscricao.objects.get(atividade=self.atividade, usuario=self.user)
        self.assertQuerySetEqual(
            inscricao.refeicoes.order_by("pk"),
            [cafe, almoco],
        )
        self.assertContains(page, 'type="checkbox" name="dados-refeicoes"', count=2)

    def test_registration_rejects_meal_from_another_activity(self):
        outra_atividade = Atividade.objects.create(
            tipo=Atividade.Tipo.EVENTO,
            titulo="Outro evento",
            descricao="Evento com refeição própria.",
            local="Outro auditório",
            data_inicio=self.atividade.data_inicio,
            data_fim=self.atividade.data_fim,
            inscricoes_fim=self.atividade.inscricoes_fim,
        )
        refeicao_externa = Refeicao.objects.create(
            atividade=outra_atividade,
            tipo=Refeicao.Tipo.JANTAR,
            data=timezone.localdate(outra_atividade.data_inicio),
            horario="19:00",
        )

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data()
            | {"acao": "inscrever", "dados-refeicoes": [str(refeicao_externa.pk)]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "não é uma das escolhas disponíveis",
            response.context["dados_form"].errors["refeicoes"][0],
        )
        self.assertEqual(response.context["active_tab"], "modalidade")
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade).exists())

    def test_online_registration_cannot_select_meal(self):
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.save(update_fields=("modalidade",))
        refeicao = Refeicao.objects.create(
            atividade=self.atividade,
            tipo=Refeicao.Tipo.LANCHE,
            data=timezone.localdate(self.atividade.data_inicio),
            horario="15:00",
        )

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data()
            | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": "online",
                "dados-refeicoes": [str(refeicao.pk)],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["dados_form"],
            "refeicoes",
            "A seleção de refeições está disponível somente para a modalidade presencial.",
        )
        self.assertEqual(response.context["active_tab"], "modalidade")
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade).exists())

    def test_registration_rejects_modality_not_offered_by_activity(self):
        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data() | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": "online",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["dados_form"],
            "modalidade_inscricao",
            "Faça uma escolha válida. online não é uma das escolhas disponíveis.",
        )
        self.assertEqual(response.context["active_tab"], "modalidade")
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade, usuario=self.user).exists())

    def test_registration_step_one_shows_all_profile_fields(self):
        response = self.client.get(reverse("atividade_inscricao", args=[self.atividade.pk]))

        self.assertContains(response, "Confirme os dados do seu perfil")
        self.assertContains(response, 'id="id_dados-nome_social"')
        self.assertContains(response, 'id="id_dados-genero"')
        self.assertContains(response, 'id="id_dados-cor_raca"')
        self.assertContains(response, 'id="id_dados-estado_civil"')
        self.assertContains(response, 'id="id_endereco-cep"')
        self.assertContains(response, 'id="id_endereco-logradouro"')
        self.assertContains(response, 'id="id_endereco-estado"')
        self.assertContains(response, 'id="id_endereco-cidade"')
        self.assertContains(response, "Selecione primeiro a UF para carregar os municípios.")
        self.assertEqual(
            response.context["endereco_form"].fields["estado"].queryset.count(),
            27,
        )
        self.assertContains(response, "Formação acadêmica")
        self.assertContains(response, "Adicionar formação")
        self.assertContains(response, 'id="id_formacao-TOTAL_FORMS"')

    def test_registration_prefills_existing_address_and_city_options(self):
        estado = Estado.objects.get(sigla="AL")
        cidade = Cidade.objects.filter(estado=estado).first()
        Endereco.objects.create(
            educador=self.user.educador,
            cep="57000000",
            logradouro="Rua já cadastrada",
            numero="10",
            bairro="Centro",
            cidade=cidade,
        )

        response = self.client.get(reverse("atividade_inscricao", args=[self.atividade.pk]))

        endereco_form = response.context["endereco_form"]
        self.assertEqual(endereco_form.instance.cidade, cidade)
        self.assertIn(cidade, endereco_form.fields["cidade"].queryset)
        self.assertContains(response, "Rua já cadastrada")
        self.assertContains(response, cidade.nome_cidade)

    def test_registration_prefills_existing_personal_data_and_academic_formation(self):
        self.user.first_name = "Maria"
        self.user.last_name = "Educadora"
        self.user.email = "maria@example.com"
        self.user.save(update_fields=("first_name", "last_name", "email"))
        educador = self.user.educador
        educador.nome_social = "Maria Social"
        educador.cpf = "52998224725"
        educador.data_nascimento = "1985-03-20"
        educador.telefone = "(82) 98888-7777"
        educador.genero = EducadorGenero.objects.first()
        educador.cor_raca = CorRaca.objects.first()
        educador.estado_civil = EducadorEstadoCivil.objects.first()
        educador.save()
        formacao = Formacao.objects.create(
            educador=educador,
            nivel=Nivel.objects.first(),
            nome_curso="Letras",
            instituicao="Universidade Federal",
            situacao=Situacao.objects.first(),
            ano_inicio=2015,
        )

        response = self.client.get(reverse("atividade_inscricao", args=[self.atividade.pk]))

        self.assertEqual(response.context["user_form"]["full_name"].value(), "Maria Educadora")
        self.assertEqual(response.context["user_form"]["email"].value(), "maria@example.com")
        self.assertEqual(response.context["dados_form"]["nome_social"].value(), "Maria Social")
        self.assertEqual(response.context["dados_form"]["cpf"].value(), "52998224725")
        self.assertEqual(response.context["dados_form"]["telefone"].value(), "(82) 98888-7777")
        self.assertEqual(response.context["formacao_formset"].forms[0].instance, formacao)
        self.assertContains(response, "Universidade Federal")

    def test_registration_saves_address_and_academic_formation_in_profile(self):
        estado = Estado.objects.get(sigla="AL")
        cidade = Cidade.objects.filter(estado=estado).first()
        nivel = Nivel.objects.first()
        situacao = Situacao.objects.first()
        modalidade = Modalidade.objects.first()
        data = self.personal_data() | {
            "acao": "inscrever",
            "dados-nome_social": "Nome Social",
            "endereco-cep": "57000-000",
            "endereco-logradouro": "Rua da Formação",
            "endereco-numero": "25",
            "endereco-complemento": "Casa",
            "endereco-bairro": "Centro",
            "endereco-estado": estado.pk,
            "endereco-cidade": cidade.pk,
            "formacao-TOTAL_FORMS": "1",
            "formacao-INITIAL_FORMS": "0",
            "formacao-MIN_NUM_FORMS": "0",
            "formacao-MAX_NUM_FORMS": "1000",
            "formacao-0-nivel": nivel.pk,
            "formacao-0-nome_curso": "Pedagogia",
            "formacao-0-instituicao": "Universidade de Teste",
            "formacao-0-situacao": situacao.pk,
            "formacao-0-modalidade": modalidade.pk,
            "formacao-0-ano_inicio": "2020",
            "formacao-0-ano_conclusao": "2024",
        }

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            data,
        )

        self.assertRedirects(response, reverse("dashboard"))
        educador = self.user.educador
        educador.refresh_from_db()
        self.assertEqual(educador.nome_social, "Nome Social")
        endereco = Endereco.objects.get(educador=educador)
        self.assertEqual(endereco.cep, "57000000")
        self.assertEqual(endereco.cidade, cidade)
        formacao = Formacao.objects.get(educador=educador)
        self.assertEqual(formacao.nome_curso, "Pedagogia")
        self.assertEqual(formacao.instituicao, "Universidade de Teste")

    def test_coauthor_search_finds_registered_user(self):
        response = self.client.get(reverse("buscar_coautores"), {"q": "Pessoa Coautora"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["id"], self.coauthor_user.pk)

    def test_coauthor_search_identifies_main_author_cpf(self):
        educador = self.user.educador
        educador.cpf = "52998224725"
        educador.save(update_fields=("cpf",))

        response = self.client.get(reverse("buscar_coautores"), {"q": "529.982.247-25"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])
        self.assertEqual(
            response.json()["message"],
            "Você já é o autor principal do trabalho e não precisa ser incluído como coautor.",
        )

    def test_user_can_finish_simple_registration_only_once(self):
        data = self.personal_data() | {"acao": "inscrever"}
        first = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), data)
        second = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), data)
        self.assertRedirects(first, reverse("dashboard"))
        self.assertRedirects(second, reverse("dashboard"))
        self.assertEqual(Inscricao.objects.filter(atividade=self.atividade, usuario=self.user).count(), 1)
        self.user.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Participante da Silva")
        self.assertEqual(self.user.educador.cpf, "52998224725")

    def test_registration_requires_demographic_and_address_fields(self):
        data = self.personal_data() | {"acao": "inscrever"}
        required_fields = (
            "dados-genero",
            "dados-cor_raca",
            "dados-estado_civil",
            "endereco-cep",
            "endereco-logradouro",
            "endereco-numero",
            "endereco-bairro",
            "endereco-estado",
            "endereco-cidade",
        )
        for field_name in required_fields:
            data.pop(field_name)

        response = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["dados_form"], "genero", "Este campo é obrigatório.")
        self.assertFormError(response.context["dados_form"], "cor_raca", "Este campo é obrigatório.")
        self.assertFormError(response.context["dados_form"], "estado_civil", "Este campo é obrigatório.")
        for field_name in ("cep", "logradouro", "numero", "bairro", "estado", "cidade"):
            self.assertFormError(
                response.context["endereco_form"],
                field_name,
                "Este campo é obrigatório.",
            )
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade, usuario=self.user).exists())

    def test_registration_allows_empty_address_complement(self):
        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data() | {"acao": "inscrever", "endereco-complemento": ""},
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.user.educador.endereco.complemento, "")

    def test_registration_requires_at_least_one_academic_formation(self):
        data = self.personal_data() | {
            "acao": "inscrever",
            "formacao-TOTAL_FORMS": "0",
        }
        for field_name in tuple(data):
            if field_name.startswith("formacao-0-"):
                data.pop(field_name)

        response = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adicione pelo menos uma formação acadêmica.")
        self.assertFalse(Inscricao.objects.filter(atividade=self.atividade, usuario=self.user).exists())

    def test_registered_user_can_edit_and_cancel_from_dashboard_during_registration_period(self):
        Inscricao.objects.create(atividade=self.atividade, usuario=self.user)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "Editar inscrição")
        self.assertContains(response, "Cancelar inscrição")
        self.assertContains(
            response,
            reverse("atividade_inscricao_cancelar", args=[self.atividade.pk]),
        )

    def test_user_can_update_registration_during_registration_period(self):
        Inscricao.objects.create(atividade=self.atividade, usuario=self.user)
        data = self.personal_data() | {
            "acao": "atualizar",
            "usuario-full_name": "Participante Atualizado",
        }

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            data,
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(response, "Sua inscrição foi atualizada com sucesso.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Participante Atualizado")

    def test_user_cannot_update_registration_after_registration_period(self):
        Inscricao.objects.create(atividade=self.atividade, usuario=self.user)
        self.atividade.inscricoes_fim = timezone.now() - timedelta(minutes=1)
        self.atividade.save(update_fields=("inscricoes_fim",))
        data = self.personal_data() | {
            "acao": "atualizar",
            "usuario-full_name": "Alteração fora do prazo",
        }

        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "As inscrições para esta atividade estão encerradas")
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.get_full_name(), "Alteração fora do prazo")

    def test_user_can_cancel_registration_during_registration_period(self):
        Inscricao.objects.create(atividade=self.atividade, usuario=self.user)
        url = reverse("atividade_inscricao_cancelar", args=[self.atividade.pk])

        confirmation = self.client.get(url)
        response = self.client.post(url, follow=True)

        self.assertContains(confirmation, "Deseja cancelar sua inscrição?")
        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(response, "Sua inscrição foi cancelada com sucesso.")
        self.assertFalse(
            Inscricao.objects.filter(atividade=self.atividade, usuario=self.user).exists()
        )

    def test_user_cannot_cancel_registration_after_registration_period(self):
        inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.user)
        self.atividade.inscricoes_fim = timezone.now() - timedelta(minutes=1)
        self.atividade.save(update_fields=("inscricoes_fim",))
        url = reverse("atividade_inscricao_cancelar", args=[self.atividade.pk])

        dashboard = self.client.get(reverse("dashboard"))
        response = self.client.post(url, follow=True)

        self.assertNotContains(dashboard, "Editar inscrição")
        self.assertNotContains(dashboard, "Cancelar inscrição")
        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(response, "O período para cancelar esta inscrição está encerrado.")
        self.assertTrue(Inscricao.objects.filter(pk=inscricao.pk).exists())

    def test_work_submission_requires_a_real_pdf(self):
        data = self.personal_data() | self.academic_work_data() | {
            "acao": "submeter",
            "trabalho-titulo": "Saberes e práticas na EJA",
            "coautor-TOTAL_FORMS": "1",
            "coautor-INITIAL_FORMS": "0",
            "coautor-MIN_NUM_FORMS": "0",
            "coautor-MAX_NUM_FORMS": "1000",
            "coautor-0-nome": "Pessoa Coautora",
            "coautor-0-email": "coautora@example.com",
        }
        invalid = data | {
            "trabalho-arquivo": SimpleUploadedFile("trabalho.txt", b"texto", content_type="text/plain")
        }
        response = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), invalid)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Trabalho.objects.exists())

    def test_user_can_submit_pdf_and_coauthor(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            data = self.personal_data() | self.academic_work_data() | {
                "acao": "submeter",
                "trabalho-titulo": "Saberes e práticas na EJA",
                "trabalho-arquivo": SimpleUploadedFile(
                    "trabalho.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
                ),
                "coautor-TOTAL_FORMS": "1",
                "coautor-INITIAL_FORMS": "0",
                "coautor-MIN_NUM_FORMS": "0",
                "coautor-MAX_NUM_FORMS": "1000",
                "coautor-0-usuario": str(self.coauthor_user.pk),
            }
            response = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), data)
            self.assertRedirects(response, reverse("dashboard"))
            trabalho = Trabalho.objects.get(inscricao__usuario=self.user, inscricao__atividade=self.atividade)
            self.assertEqual(trabalho.titulo, "Saberes e práticas na EJA")
            self.assertEqual(trabalho.eixo_tematico, "Práticas pedagógicas na EJA")
            self.assertEqual(trabalho.versao_termos, Trabalho.VERSAO_ATUAL_TERMOS)
            self.assertIsNotNone(trabalho.termos_aceitos_em)
            self.assertTrue(Coautor.objects.filter(trabalho=trabalho, nome="Pessoa Coautora").exists())
            download = self.client.get(reverse("trabalho_download", args=[trabalho.pk]))
            self.assertEqual(download.status_code, 200)
            for closer in download._resource_closers:
                closer()
            download._resource_closers.clear()

    def test_work_rejects_coauthor_not_registered_on_platform(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            data = self.personal_data() | self.academic_work_data() | {
                "acao": "submeter",
                "trabalho-titulo": "Trabalho com coautor não cadastrado",
                "trabalho-arquivo": SimpleUploadedFile(
                    "trabalho.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
                ),
                "coautor-TOTAL_FORMS": "1",
                "coautor-INITIAL_FORMS": "0",
                "coautor-MIN_NUM_FORMS": "0",
                "coautor-MAX_NUM_FORMS": "1000",
                "coautor-0-nome": "Pessoa sem cadastro",
                "coautor-0-email": "nao-cadastrada@example.com",
            }
            response = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), data)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Este campo é obrigatório")
            self.assertFalse(Trabalho.objects.exists())

    def test_user_can_submit_detailed_experience_report(self):
        self.atividade.modelo_submissao = Atividade.ModeloSubmissao.RELATO_EXPERIENCIA
        self.atividade.save(update_fields=("modelo_submissao",))
        estado = Estado.objects.get(sigla="AL")
        cidade = Cidade.objects.filter(estado=estado).first()
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            data = self.personal_data() | {
                "acao": "submeter",
                "trabalho-titulo": "Formação territorial na EJA",
                "trabalho-apresentacao": "Justificativa e apresentação da experiência.",
                "trabalho-periodo_inicio": "2026-03-01",
                "trabalho-periodo_fim": "2026-03-10",
                "trabalho-turnos": "noite",
                "trabalho-carga_horaria": "20",
                "trabalho-estado": str(estado.pk),
                "trabalho-objetivo_geral": "Fortalecer a formação de educadores.",
                "trabalho-objetivos_especificos": "Compartilhar práticas e avaliar resultados.",
                "trabalho-desenvolvimento_metodologico": "Encontros, rodas de diálogo e oficinas.",
                "trabalho-consideracoes": "A experiência ampliou a participação.",
                "trabalho-referencias": "FREIRE, Paulo. Pedagogia da autonomia.",
                "trabalho-autorizacao_imagens": "sem",
                "trabalho-aceitou_termo_imagem": "on",
                "trabalho-aceitou_termo_relato": "on",
                "trabalho-aceitou_termo_cessao": "on",
                "trabalho-aceitou_originalidade": "on",
                "trabalho-arquivo": SimpleUploadedFile(
                    "relato.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
                ),
                "coautor-TOTAL_FORMS": "0",
                "coautor-INITIAL_FORMS": "0",
                "coautor-MIN_NUM_FORMS": "0",
                "coautor-MAX_NUM_FORMS": "1000",
                "municipio-TOTAL_FORMS": "1",
                "municipio-INITIAL_FORMS": "0",
                "municipio-MIN_NUM_FORMS": "0",
                "municipio-MAX_NUM_FORMS": "1000",
                "municipio-0-cidade": str(cidade.pk),
                "municipio-0-participantes": "35",
                "evidencia-TOTAL_FORMS": "0",
                "evidencia-INITIAL_FORMS": "0",
                "evidencia-MIN_NUM_FORMS": "0",
                "evidencia-MAX_NUM_FORMS": "2",
            }
            response = self.client.post(
                reverse("atividade_inscricao", args=[self.atividade.pk]), data
            )
            self.assertRedirects(response, reverse("dashboard"))
            trabalho = Trabalho.objects.get(inscricao__usuario=self.user)
            self.assertEqual(trabalho.n_participantes, 35)
            self.assertEqual(trabalho.turnos, ["noite"])
            self.assertTrue(
                TrabalhoMunicipio.objects.filter(
                    trabalho=trabalho, cidade=cidade, participantes=35
                ).exists()
            )

    def test_other_user_cannot_download_work(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.user)
            trabalho = Trabalho.objects.create(
                inscricao=inscricao,
                titulo="Trabalho protegido",
                arquivo=SimpleUploadedFile("protegido.pdf", b"%PDF", content_type="application/pdf"),
            )
            other = get_user_model().objects.create_user(username="outro@example.com", password="SenhaForte2026!")
            self.client.force_login(other)
            self.assertEqual(self.client.get(reverse("trabalho_download", args=[trabalho.pk])).status_code, 404)


class AtividadeManagementTests(TestCase):
    def create_activity(self, modalidade=Atividade.ModalidadeParticipacao.AMBAS):
        inicio = timezone.now() + timedelta(days=30)
        return Atividade.objects.create(
            tipo=Atividade.Tipo.EVENTO,
            modalidade=modalidade,
            titulo="Encontro de formação",
            descricao="Atividade para formação de educadores.",
            local="Centro de formação",
            data_inicio=inicio,
            data_fim=inicio + timedelta(days=1),
            inscricoes_fim=inicio - timedelta(days=1),
        )

    def test_management_requires_permission(self):
        regular = get_user_model().objects.create_user(username="regular@example.com", password="SenhaForte2026!")
        self.client.force_login(regular)
        self.assertEqual(self.client.get(reverse("atividade_list")).status_code, 403)

    def test_superuser_can_open_management(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.atividades@example.com", email="admin.atividades@example.com", password="SenhaForte2026!"
        )
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("atividade_list")).status_code, 200)
        response = self.client.get(reverse("atividade_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O sistema criará automaticamente")
        self.assertNotContains(response, "link do evento on-line")
        self.assertContains(response, "Refeições disponíveis")
        self.assertContains(response, "Adicionar refeição")

    def test_superuser_can_create_activity_with_meals(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.refeicoes@example.com",
            email="admin.refeicoes@example.com",
            password="SenhaForte2026!",
        )
        self.client.force_login(admin)
        inicio = timezone.localtime(timezone.now() + timedelta(days=30)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        fim = inicio + timedelta(days=1, hours=10)

        response = self.client.post(
            reverse("atividade_create"),
            {
                "tipo": Atividade.Tipo.EVENTO,
                "modalidade": Atividade.ModalidadeParticipacao.PRESENCIAL,
                "titulo": "Encontro com refeições",
                "descricao": "Atividade de dois dias.",
                "local": "Centro de convenções",
                "data_inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
                "data_fim": fim.strftime("%Y-%m-%dT%H:%M"),
                "inscricoes_inicio": "",
                "inscricoes_fim": (inicio - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "vagas": "100",
                "modelo_submissao": Atividade.ModeloSubmissao.ACADEMICO,
                "submissoes_fim": "",
                "ativo": "on",
                "refeicoes-TOTAL_FORMS": "2",
                "refeicoes-INITIAL_FORMS": "0",
                "refeicoes-MIN_NUM_FORMS": "0",
                "refeicoes-MAX_NUM_FORMS": "1000",
                "refeicoes-0-tipo": Refeicao.Tipo.CAFE_DA_MANHA,
                "refeicoes-0-data": inicio.strftime("%Y-%m-%d"),
                "refeicoes-0-horario": "08:00",
                "refeicoes-1-tipo": Refeicao.Tipo.ALMOCO,
                "refeicoes-1-data": inicio.strftime("%Y-%m-%d"),
                "refeicoes-1-horario": "12:00",
            },
        )

        self.assertRedirects(response, reverse("atividade_list"))
        atividade = Atividade.objects.get(titulo="Encontro com refeições")
        self.assertEqual(atividade.refeicoes.count(), 2)
        self.assertTrue(
            atividade.refeicoes.filter(tipo=Refeicao.Tipo.CAFE_DA_MANHA).exists()
        )

    def test_superuser_can_add_room_programs_and_link_them_to_activity(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.salas.atividade@example.com",
            email="admin.salas.atividade@example.com",
            password="SenhaForte2026!",
        )
        self.client.force_login(admin)
        atividade = self.create_activity()
        tematica = TematicaSala.objects.create(nome="Alfabetização na EJA")
        data_programacao = timezone.localdate(atividade.data_inicio)
        url = reverse("atividade_add_room", args=[atividade.pk])

        page = self.client.get(reverse("atividade_update", args=[atividade.pk]))
        response = self.client.post(
            url,
            {
                "nova_sala-nome": "Sala de práticas",
                "nova_programacoes-TOTAL_FORMS": "2",
                "nova_programacoes-INITIAL_FORMS": "0",
                "nova_programacoes-MIN_NUM_FORMS": "1",
                "nova_programacoes-MAX_NUM_FORMS": "1000",
                "nova_programacoes-0-data": data_programacao.isoformat(),
                "nova_programacoes-0-turno": ProgramacaoSala.Turno.MANHA,
                "nova_programacoes-0-modalidade": ProgramacaoSala.Modalidade.PRESENCIAL,
                "nova_programacoes-0-link": "",
                "nova_programacoes-0-tematica": str(tematica.pk),
                "nova_programacoes-0-descricao": "Roda de conversa.",
                "nova_programacoes-0-quantidade_max_participantes": "30",
                "nova_programacoes-1-data": data_programacao.isoformat(),
                "nova_programacoes-1-turno": ProgramacaoSala.Turno.TARDE,
                "nova_programacoes-1-modalidade": ProgramacaoSala.Modalidade.ONLINE,
                "nova_programacoes-1-link": "https://example.com/sala-praticas",
                "nova_programacoes-1-tematica": str(tematica.pk),
                "nova_programacoes-1-descricao": "Oficina on-line.",
                "nova_programacoes-1-quantidade_max_participantes": "50",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertContains(page, "Adicionar sala e programação")
        self.assertContains(page, 'id="activity-room-modal"')
        self.assertContains(page, "Salas e programações vinculadas")
        self.assertContains(page, "Nenhuma sala ou programação vinculada")
        self.assertNotContains(
            page,
            "Selecione as programações que os participantes poderão escolher na inscrição.",
        )
        self.assertEqual(response.status_code, 201)
        sala = Sala.objects.get(nome="Sala de práticas")
        self.assertEqual(sala.programacoes.count(), 2)
        self.assertQuerySetEqual(
            atividade.programacoes.order_by("pk"),
            sala.programacoes.order_by("pk"),
        )
        self.assertEqual(len(response.json()["programacoes"]), 2)

        updated_page = self.client.get(reverse("atividade_update", args=[atividade.pk]))
        self.assertContains(updated_page, "Sala de práticas")
        self.assertContains(updated_page, "Alfabetização na EJA")
        self.assertContains(updated_page, f'data-program-id="{sala.programacoes.first().pk}"')
        self.assertContains(updated_page, "2 programações")

        update_response = self.client.post(
            reverse("atividade_update", args=[atividade.pk]),
            {
                "tipo": atividade.tipo,
                "modalidade": atividade.modalidade,
                "titulo": atividade.titulo,
                "descricao": atividade.descricao,
                "local": atividade.local,
                "data_inicio": timezone.localtime(atividade.data_inicio).strftime("%Y-%m-%dT%H:%M"),
                "data_fim": timezone.localtime(atividade.data_fim).strftime("%Y-%m-%dT%H:%M"),
                "inscricoes_inicio": "",
                "inscricoes_fim": timezone.localtime(atividade.inscricoes_fim).strftime("%Y-%m-%dT%H:%M"),
                "vagas": "",
                "modelo_submissao": atividade.modelo_submissao,
                "submissoes_fim": "",
                "ativo": "on",
            },
        )
        self.assertRedirects(update_response, reverse("atividade_list"))
        self.assertEqual(atividade.programacoes.count(), 2)

    def test_add_room_rejects_schedule_with_unavailable_modality(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.modalidade.sala@example.com",
            email="admin.modalidade.sala@example.com",
            password="SenhaForte2026!",
        )
        self.client.force_login(admin)
        atividade = self.create_activity(Atividade.ModalidadeParticipacao.PRESENCIAL)
        tematica = TematicaSala.objects.create(nome="Tecnologias educacionais")

        response = self.client.post(
            reverse("atividade_add_room", args=[atividade.pk]),
            {
                "nova_sala-nome": "Sala incompatível",
                "nova_programacoes-TOTAL_FORMS": "1",
                "nova_programacoes-INITIAL_FORMS": "0",
                "nova_programacoes-MIN_NUM_FORMS": "1",
                "nova_programacoes-MAX_NUM_FORMS": "1000",
                "nova_programacoes-0-data": timezone.localdate(atividade.data_inicio).isoformat(),
                "nova_programacoes-0-turno": ProgramacaoSala.Turno.MANHA,
                "nova_programacoes-0-modalidade": ProgramacaoSala.Modalidade.ONLINE,
                "nova_programacoes-0-link": "https://example.com/incompativel",
                "nova_programacoes-0-tematica": str(tematica.pk),
                "nova_programacoes-0-descricao": "",
                "nova_programacoes-0-quantidade_max_participantes": "20",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("modalidade disponível", response.json()["errors"][0])
        self.assertFalse(Sala.objects.filter(nome="Sala incompatível").exists())

    def test_superuser_can_manage_schedules_from_linked_room_list(self):
        admin = get_user_model().objects.create_superuser(
            username="admin.programacoes.atividade@example.com",
            email="admin.programacoes.atividade@example.com",
            password="SenhaForte2026!",
        )
        self.client.force_login(admin)
        atividade = self.create_activity()
        sala = Sala.objects.create(nome="Sala de oficinas")
        tematica = TematicaSala.objects.create(nome="Práticas pedagógicas")
        data_programacao = timezone.localdate(atividade.data_inicio)
        programacao_existente = ProgramacaoSala.objects.create(
            sala=sala,
            data=data_programacao,
            turno=ProgramacaoSala.Turno.MANHA,
            modalidade=ProgramacaoSala.Modalidade.PRESENCIAL,
            tematica=tematica,
            quantidade_max_participantes=25,
        )
        atividade.programacoes.add(programacao_existente)
        payload = {
            "programacao-data": data_programacao.isoformat(),
            "programacao-turno": ProgramacaoSala.Turno.TARDE,
            "programacao-modalidade": ProgramacaoSala.Modalidade.ONLINE,
            "programacao-link": "https://example.com/oficina",
            "programacao-tematica": str(tematica.pk),
            "programacao-descricao": "Oficina inicial.",
            "programacao-quantidade_max_participantes": "40",
        }

        page = self.client.get(reverse("atividade_update", args=[atividade.pk]))
        add_response = self.client.post(
            reverse("atividade_add_room_schedule", args=[atividade.pk, sala.pk]),
            payload,
        )

        self.assertContains(page, "Adicionar programação")
        self.assertContains(page, "Editar")
        self.assertContains(page, "Excluir")
        self.assertEqual(add_response.status_code, 201)
        nova_programacao = ProgramacaoSala.objects.get(
            pk=add_response.json()["programacao"]["id"]
        )
        self.assertTrue(atividade.programacoes.filter(pk=nova_programacao.pk).exists())

        edit_response = self.client.post(
            reverse(
                "atividade_edit_room_schedule",
                args=[atividade.pk, nova_programacao.pk],
            ),
            payload
            | {
                "programacao-turno": ProgramacaoSala.Turno.NOITE,
                "programacao-descricao": "Oficina atualizada.",
                "programacao-quantidade_max_participantes": "55",
            },
        )
        self.assertEqual(edit_response.status_code, 200)
        nova_programacao.refresh_from_db()
        self.assertEqual(nova_programacao.turno, ProgramacaoSala.Turno.NOITE)
        self.assertEqual(nova_programacao.quantidade_max_participantes, 55)

        delete_response = self.client.post(
            reverse(
                "atividade_delete_room_schedule",
                args=[atividade.pk, nova_programacao.pk],
            )
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(delete_response.json()["room_empty"])
        self.assertFalse(ProgramacaoSala.objects.filter(pk=nova_programacao.pk).exists())
        self.assertTrue(
            atividade.programacoes.filter(pk=programacao_existente.pk).exists()
        )

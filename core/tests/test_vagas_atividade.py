from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from core.admin.atividade_admin import AtividadeAdmin
from core.forms import AtividadeForm, DadosPessoaisInscricaoForm
from core.models import Atividade, Inscricao
from core.tests import test_atividades


class VagasAtividadeTests(TestCase):
    personal_data = test_atividades.AtividadeFlowTests.personal_data
    create_programacao = test_atividades.AtividadeFlowTests.create_programacao

    def setUp(self):
        test_atividades.AtividadeFlowTests.setUp(self)
        self.atividade.modalidade = "ambas"
        self.atividade.vagas = 1
        self.atividade.vagas_online = 10
        self.atividade.save()
        self.manha = self.create_programacao("presencial", "Manhã", turno="manha")
        self.tarde = self.create_programacao("presencial", "Tarde", turno="tarde")
        self.online_manha = self.create_programacao("online", "Online manhã", turno="manha")
        self.online_tarde = self.create_programacao("online", "Online tarde", turno="tarde")
        self.atividade.programacoes.add(self.manha, self.tarde, self.online_manha, self.online_tarde)

    def lotar_presencial(self):
        inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.coauthor_user)
        inscricao.programacoes.add(self.manha, self.tarde)
        return inscricao

    def test_one_place_per_registration_and_independent_room_capacity(self):
        inscricao = self.lotar_presencial()
        self.assertEqual(self.atividade.vagas_restantes, 0)
        self.assertEqual(self.atividade.vagas_online_restantes, 10)
        self.assertGreater(self.manha.vagas_disponiveis, 0)
        self.assertTrue(self.atividade.inscricoes_abertas)
        self.atividade.programacoes.clear()
        self.assertEqual(self.atividade.vagas, 1)
        inscricao.delete()
        self.assertEqual(self.atividade.vagas_restantes, 1)

    def test_full_modality_rejects_post_even_with_free_rooms(self):
        self.lotar_presencial()
        response = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), self.personal_data() | {
            "acao": "inscrever", "dados-programacoes": [self.manha.pk, self.tarde.pk],
        })
        self.assertContains(response, "A quantidade de vagas para esta modalidade foi atingida.")
        self.assertFalse(Inscricao.objects.filter(usuario=self.user).exists())
        self.assertContains(response, 'data-modalidades-lotadas="presencial"')

    def test_other_modality_accepts_registration(self):
        self.lotar_presencial()
        response = self.client.post(reverse("atividade_inscricao", args=[self.atividade.pk]), self.personal_data() | {
            "acao": "inscrever", "dados-modalidade_inscricao": "online",
            "dados-programacoes": [self.online_manha.pk, self.online_tarde.pk],
        })
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.atividade.vagas_online_restantes, 9)

    def test_existing_registration_keeps_own_place(self):
        inscricao = self.lotar_presencial()
        form = DadosPessoaisInscricaoForm(atividade=self.atividade, inscricao=inscricao)
        self.assertNotIn("presencial", form.modalidades_lotadas)
        self.atividade.vagas_online = 0
        self.atividade.save()
        form = DadosPessoaisInscricaoForm(atividade=self.atividade, inscricao=inscricao)
        self.assertIn("online", form.modalidades_lotadas)
        self.assertFalse(self.atividade.inscricoes_abertas)

    def test_manual_fields_and_dashboard(self):
        form = AtividadeForm(instance=self.atividade)
        self.assertIn("vagas", form.fields)
        self.assertIn("vagas_online", form.fields)
        self.assertNotIn("vagas", AtividadeAdmin(Atividade, admin.site).readonly_fields)
        self.lotar_presencial()
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "<strong>Vagas presenciais restantes:</strong> 0")
        atividade = response.context["atividades_disponiveis"][0]
        with self.assertNumQueries(0):
            self.assertEqual(atividade.vagas_online_restantes, 10)

    def test_registration_page_marks_full_modality_before_submission(self):
        self.lotar_presencial()
        response = self.client.get(reverse("atividade_inscricao", args=[self.atividade.pk]))
        self.assertContains(response, 'data-modalidades-lotadas="presencial"')
        self.assertContains(response, '/static/js/atividade_inscricao.js?v=20261014-2')
        from html.parser import HTMLParser

        class ProgramInputs(HTMLParser):
            fields = None

            def __init__(self):
                super().__init__()
                self.fields = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "input" and attrs.get("name") == "dados-programacoes":
                    self.fields.append(attrs)

        parser = ProgramInputs()
        parser.feed(response.content.decode())
        presencial = [f for f in parser.fields if f.get("data-modalidade") == "presencial"]
        online = [f for f in parser.fields if f.get("data-modalidade") == "online"]
        self.assertTrue(presencial)
        self.assertTrue(online)
        self.assertTrue(all("disabled" in f for f in presencial))
        self.assertTrue(all("disabled" not in f for f in online))

from django.contrib import admin
from django.test import TestCase
from django.urls import reverse

from core.admin.atividade_admin import AtividadeAdmin
from core.forms import AtividadeForm
from core.models import Atividade, Inscricao
from core.tests import test_atividades


class VagasAtividadeTests(TestCase):
    personal_data = test_atividades.AtividadeFlowTests.personal_data
    create_programacao = test_atividades.AtividadeFlowTests.create_programacao

    def setUp(self):
        test_atividades.AtividadeFlowTests.setUp(self)
        self.atividade.modalidade = Atividade.ModalidadeParticipacao.AMBAS
        self.atividade.save(update_fields=("modalidade",))
        self.presencial_manha = self.programacao("presencial", "manha", 10)
        self.presencial_tarde = self.programacao("presencial", "tarde", 20)
        self.online_manha = self.programacao("online", "manha", 7)
        self.online_tarde = self.programacao("online", "tarde", 8)
        self.atividade.programacoes.add(
            self.presencial_manha, self.presencial_tarde, self.online_manha, self.online_tarde
        )

    def programacao(self, modalidade, turno, capacidade):
        programacao = self.create_programacao(modalidade, f"Sala {modalidade} {turno}", turno=turno)
        programacao.quantidade_max_participantes = capacidade
        programacao.save(update_fields=("quantidade_max_participantes",))
        return programacao

    def test_totals_separated_by_modality_and_read_only(self):
        self.assertEqual(self.atividade.vagas, 30)
        self.assertEqual(self.atividade.vagas_online, 15)
        self.assertEqual(self.atividade.vagas_restantes, 30)
        self.assertEqual(self.atividade.vagas_online_restantes, 15)
        with self.assertRaises(AttributeError):
            self.atividade.vagas = 999
        with self.assertRaises(AttributeError):
            self.atividade.vagas_online = 999

    def test_totals_update_when_linking_editing_unlinking_and_deleting(self):
        nova = self.create_programacao("presencial", "Nova sala")
        self.atividade.programacoes.add(nova)
        self.assertEqual(self.atividade.vagas, 80)
        nova.quantidade_max_participantes = 12
        nova.save(update_fields=("quantidade_max_participantes",))
        self.assertEqual(self.atividade.vagas, 42)
        nova.modalidade = "online"
        nova.save(update_fields=("modalidade",))
        self.assertEqual(self.atividade.vagas, 30)
        self.assertEqual(self.atividade.vagas_online, 27)
        self.atividade.programacoes.remove(nova)
        self.assertEqual(self.atividade.vagas_online, 15)
        self.presencial_manha.delete()
        self.assertEqual(self.atividade.vagas, 20)
        self.atividade.programacoes.clear()
        self.assertEqual(self.atividade.vagas, 0)
        self.assertEqual(self.atividade.vagas_online, 0)

    def test_reverse_links_and_room_deletion_update_totals(self):
        self.presencial_manha.atividades.remove(self.atividade)
        self.assertEqual(self.atividade.vagas, 20)
        self.presencial_manha.atividades.add(self.atividade)
        self.assertEqual(self.atividade.vagas, 30)
        self.presencial_manha.sala.delete()
        self.assertEqual(self.atividade.vagas, 20)

    def test_remaining_places_discount_each_selected_program(self):
        inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.coauthor_user)
        inscricao.programacoes.add(self.presencial_manha, self.presencial_tarde)
        self.assertEqual(self.atividade.vagas_restantes, 28)
        self.assertEqual(self.atividade.vagas_online_restantes, 15)
        inscricao.programacoes.set((self.online_manha, self.online_tarde))
        self.assertEqual(self.atividade.vagas_restantes, 30)
        self.assertEqual(self.atividade.vagas_online_restantes, 13)
        inscricao.delete()
        self.assertEqual(self.atividade.vagas_online_restantes, 15)

    def test_shared_program_remaining_places_include_other_events(self):
        outra = Atividade.objects.get(pk=self.atividade.pk)
        outra.pk = None
        outra.save()
        outra.programacoes.add(self.online_manha, self.online_tarde)
        inscricao = Inscricao.objects.create(atividade=outra, usuario=self.coauthor_user, modalidade="online")
        inscricao.programacoes.add(self.online_manha, self.online_tarde)
        self.assertEqual(self.atividade.vagas_online_restantes, 13)
        self.assertEqual(self.atividade.vagas_restantes, 30)

    def test_full_presential_programs_do_not_close_online_registration(self):
        self.presencial_manha.quantidade_max_participantes = 1
        self.presencial_tarde.quantidade_max_participantes = 1
        self.presencial_manha.save()
        self.presencial_tarde.save()
        inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.coauthor_user)
        inscricao.programacoes.add(self.presencial_manha, self.presencial_tarde)
        self.assertEqual(self.atividade.vagas_restantes, 0)
        self.assertTrue(self.atividade.inscricoes_abertas)
        response = self.client.post(
            reverse("atividade_inscricao", args=[self.atividade.pk]),
            self.personal_data() | {
                "acao": "inscrever",
                "dados-modalidade_inscricao": "online",
                "dados-programacoes": [str(self.online_manha.pk), str(self.online_tarde.pk)],
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.atividade.vagas_online_restantes, 13)

    def test_availability_requires_free_morning_and_afternoon_in_same_modality(self):
        inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.coauthor_user)
        for programacao in (self.presencial_manha, self.online_tarde):
            programacao.quantidade_max_participantes = 1
            programacao.save()
            inscricao.programacoes.add(programacao)
        self.assertFalse(self.atividade.inscricoes_abertas)
        self.assertGreater(self.atividade.vagas_restantes, 0)
        self.assertGreater(self.atividade.vagas_online_restantes, 0)

    def test_over_capacity_does_not_subtract_places_from_other_programs(self):
        self.presencial_manha.quantidade_max_participantes = 1
        self.presencial_manha.save()
        for usuario in (self.user, self.coauthor_user):
            inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=usuario)
            inscricao.programacoes.add(self.presencial_manha)
        self.assertEqual(self.atividade.vagas_restantes, 20)

    def test_dashboard_displays_presential_then_online_remaining_places(self):
        inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.coauthor_user)
        inscricao.programacoes.add(self.presencial_manha, self.presencial_tarde)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "<strong>Vagas presenciais restantes:</strong> 28", html=False)
        self.assertContains(response, "<strong>Vagas on-line restantes:</strong> 15", html=False)
        html = response.content.decode()
        self.assertLess(html.index("Vagas presenciais restantes:"), html.index("Vagas on-line restantes:"))
        atividade = response.context["atividades_disponiveis"][0]
        with self.assertNumQueries(0):
            self.assertEqual(atividade.vagas_restantes, 28)
            self.assertEqual(atividade.vagas_online_restantes, 15)

    def test_activity_form_and_admin_prevent_manual_capacity(self):
        form = AtividadeForm(instance=self.atividade)
        self.assertNotIn("vagas", form.fields)
        self.assertNotIn("vagas_online", form.fields)
        atividade_admin = AtividadeAdmin(Atividade, admin.site)
        self.assertIn("vagas", atividade_admin.readonly_fields)
        self.assertIn("vagas_online", atividade_admin.readonly_fields)
        self.assertEqual(Atividade().vagas, 0)
        self.assertEqual(Atividade().vagas_online, 0)

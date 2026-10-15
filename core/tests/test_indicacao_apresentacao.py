from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Atividade, Inscricao


class IndicacaoApresentacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="gestor-apresentacao", is_staff=True)
        cls.admin.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="core", codename__in=["view_inscricao", "change_inscricao"],
        ))
        cls.participante = get_user_model().objects.create_user(username="apresentador-sem-arquivo")
        agora = timezone.now()
        cls.atividade = Atividade.objects.create(titulo="Apresentações", data_inicio=agora, data_fim=agora, inscricoes_fim=agora)
        cls.inscricao = Inscricao.objects.create(atividade=cls.atividade, usuario=cls.participante)
        cls.url = reverse("atividade_inscricoes", args=[cls.atividade.pk])

    def setUp(self):
        self.client.force_login(self.admin)

    def indicar(self, decisao="sim", **kwargs):
        return self.client.post(self.url, {
            "acao": "definir_apresentacao", "inscricao_id": self.inscricao.pk,
            "vai_apresentar_trabalho": decisao,
        }, **kwargs)

    def test_coluna_e_botao_sem_trabalho_enviado(self):
        response = self.client.get(self.url)
        self.assertContains(response, "<th>Apresentação de trabalho</th>", html=True)
        self.assertNotContains(response, "<th>Trabalho</th>", html=True)
        self.assertNotContains(response, "<th>Autores e coautores</th>", html=True)
        self.assertContains(response, 'aria-pressed="false"')
        self.assertFalse(self.inscricao.vai_apresentar_trabalho)

    def test_confirma_persiste_autoria_e_permite_desfazer(self):
        response = self.indicar(HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["vai_apresentar_trabalho"], True)
        self.inscricao.refresh_from_db()
        self.assertTrue(self.inscricao.vai_apresentar_trabalho)
        self.assertEqual(self.inscricao.apresentacao_indicada_por, self.admin)
        horario = self.inscricao.apresentacao_indicada_em
        self.assertIsNotNone(horario)
        response = self.client.get(self.url)
        self.assertContains(response, 'class="btn btn-sm btn-success"')
        self.assertContains(response, 'aria-pressed="true"')
        self.indicar()
        self.inscricao.refresh_from_db()
        self.assertEqual(self.inscricao.apresentacao_indicada_em, horario)
        self.assertEqual(self.indicar("nao").status_code, 302)
        self.inscricao.refresh_from_db()
        self.assertFalse(self.inscricao.vai_apresentar_trabalho)

    def test_exige_permissao_de_alteracao(self):
        self.admin.user_permissions.remove(Permission.objects.get(content_type__app_label="core", codename="change_inscricao"))
        self.assertNotContains(self.client.get(self.url), '<form method="post" data-apresentacao-form>')
        self.assertEqual(self.indicar().status_code, 403)
        self.inscricao.refresh_from_db()
        self.assertFalse(self.inscricao.vai_apresentar_trabalho)

    def test_rejeita_inscricao_de_outro_evento_e_decisao_invalida(self):
        agora = timezone.now()
        outra = Atividade.objects.create(titulo="Outro", data_inicio=agora, data_fim=agora, inscricoes_fim=agora)
        inscricao = Inscricao.objects.create(atividade=outra, usuario=self.participante)
        response = self.client.post(self.url, {"acao": "definir_apresentacao", "inscricao_id": inscricao.pk, "vai_apresentar_trabalho": "sim"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.indicar("invalido").status_code, 400)

    def test_exige_csrf_e_get_nao_altera(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url, {"acao": "definir_apresentacao"}).status_code, 403)
        self.client.get(self.url, {"acao": "definir_apresentacao", "inscricao_id": self.inscricao.pk, "vai_apresentar_trabalho": "sim"})
        self.inscricao.refresh_from_db()
        self.assertFalse(self.inscricao.vai_apresentar_trabalho)

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Atividade, Credenciamento, Inscricao
from core.services.credenciamento_pdf import gerar_lista_credenciamento
from reportlab.platypus import Table


class CredenciamentoTests(TestCase):
    def setUp(self):
        self.operador = get_user_model().objects.create_user(username="operador", is_staff=True)
        self.operador.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="core", codename__in=("view_credenciamento", "add_credenciamento", "view_atividade"),
        ))
        agora = timezone.now()
        self.atividade = Atividade.objects.create(
            titulo="Encontro presencial", descricao="Evento", modalidade="ambas",
            data_inicio=agora, data_fim=agora + timedelta(days=1), inscricoes_fim=agora,
        )
        self.presencial = Inscricao.objects.create(
            atividade=self.atividade,
            usuario=get_user_model().objects.create_user(username="presencial", first_name="Maria"),
        )
        self.online = Inscricao.objects.create(
            atividade=self.atividade, modalidade="online",
            usuario=get_user_model().objects.create_user(username="remoto", first_name="Remoto"),
        )
        self.url = reverse("atividade_credenciamento", args=[self.atividade.pk])
        self.client.force_login(self.operador)

    def test_listagem_somente_presenciais_e_botao_nova_aba(self):
        resposta = self.client.get(self.url)
        self.assertContains(resposta, "Maria")
        self.assertNotContains(resposta, "Remoto")
        self.assertEqual(resposta.context["total"], 1)
        self.assertContains(self.client.get(reverse("atividade_list")), f'href="{self.url}" target="_blank"')

    def test_confirmacao_idempotente_com_auditoria(self):
        self.client.post(self.url, {"inscricao": self.presencial.pk})
        original = Credenciamento.objects.get(inscricao=self.presencial)
        self.client.post(self.url, {"inscricao": self.presencial.pk})
        self.assertEqual(Credenciamento.objects.count(), 1)
        self.assertEqual(Credenciamento.objects.get().registrado_em, original.registrado_em)
        self.assertEqual(original.registrado_por, self.operador)
        resposta = self.client.get(self.url, {"status": "credenciado", "q": "Maria"})
        self.assertEqual(resposta.context["credenciados"], 1)
        self.assertEqual(resposta.context["pendentes"], 0)
        self.assertContains(resposta, "Maria")
        self.assertNotContains(self.client.get(self.url, {"status": "pendente"}), "Confirmar credenciamento")

    def test_rejeita_online_e_inscricao_de_outro_evento(self):
        self.assertEqual(self.client.post(self.url, {"inscricao": self.online.pk}).status_code, 404)
        self.atividade.pk = None
        self.atividade.save()
        outro = reverse("atividade_credenciamento", args=[self.atividade.pk])
        self.assertEqual(self.client.post(outro, {"inscricao": self.presencial.pk}).status_code, 404)
        self.assertFalse(Credenciamento.objects.exists())

    def test_evento_inativo_e_get_nao_confirmam(self):
        self.client.get(self.url, {"inscricao": self.presencial.pk})
        self.atividade.ativo = False
        self.atividade.save()
        self.client.post(self.url, {"inscricao": self.presencial.pk})
        self.assertFalse(Credenciamento.objects.exists())

    def test_permissoes_de_consulta_e_operacao(self):
        self.operador.user_permissions.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.operador.user_permissions.add(Permission.objects.get(codename="view_credenciamento"))
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, {"inscricao": self.presencial.pk}).status_code, 403)

    def test_nao_cancela_inscricao_credenciada(self):
        self.client.post(self.url, {"inscricao": self.presencial.pk})
        self.atividade.inscricoes_fim = timezone.now() + timedelta(days=1)
        self.atividade.save()
        self.client.force_login(self.presencial.usuario)
        self.client.post(reverse("atividade_inscricao_cancelar", args=[self.atividade.pk]))
        self.assertTrue(Inscricao.objects.filter(pk=self.presencial.pk).exists())

    def test_pdf_completo_presencial_mesmo_com_filtros(self):
        url = reverse("atividade_credenciamento_pdf", args=[self.atividade.pk])
        self.assertContains(self.client.get(self.url), url)
        with patch("core.views.credenciamento.gerar_lista_credenciamento", wraps=gerar_lista_credenciamento) as gerar:
            resposta = self.client.get(url, {"q": "inexistente", "status": "credenciado"})
            self.assertEqual(resposta["Content-Type"], "application/pdf")
            self.assertIn("attachment", resposta["Content-Disposition"])
            self.assertTrue(b"".join(resposta.streaming_content).startswith(b"%PDF-"))
            self.assertEqual(list(gerar.call_args.args[1]), [self.presencial])
        self.operador.user_permissions.clear()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_pdf_ordem_alfabetica_e_campos_para_preenchimento(self):
        ana = Inscricao.objects.create(atividade=self.atividade, usuario=get_user_model().objects.create_user(username="ana", first_name="Ána"))
        with patch("core.services.credenciamento_pdf.Table", wraps=Table) as tabela:
            gerar_lista_credenciamento(self.atividade, [self.presencial, ana])
        dados = tabela.call_args.args[0]
        self.assertEqual(dados[0], ["Nome", "CPF", "Assinatura", "Data"])
        self.assertEqual([linha[0].text for linha in dados[1:]], ["Ána", "Maria"])
        self.assertTrue(all(linha[2:] == ["", ""] for linha in dados[1:]))

    def test_cancelamento_confirma_e_permite_novo_credenciamento(self):
        self.client.post(self.url, {"inscricao": self.presencial.pk})
        self.assertContains(self.client.get(self.url), "Cancelar credenciamento")
        resposta = self.client.post(self.url, {"inscricao": self.presencial.pk, "acao": "confirmar_cancelamento"})
        self.assertContains(resposta, "Confirmar cancelamento")
        self.assertTrue(Credenciamento.objects.exists())
        self.client.get(self.url, {"inscricao": self.presencial.pk, "acao": "cancelar"})
        self.assertTrue(Credenciamento.objects.exists())
        self.client.post(self.url, {"inscricao": self.presencial.pk, "acao": "cancelar"})
        self.assertFalse(Credenciamento.objects.exists())
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context["pendentes"], 1)
        self.assertEqual(resposta.context["credenciados"], 0)
        self.client.post(self.url, {"inscricao": self.presencial.pk, "acao": "cancelar"})
        self.assertFalse(Credenciamento.objects.exists())
        self.client.post(self.url, {"inscricao": self.presencial.pk})
        self.assertTrue(Credenciamento.objects.exists())

    def test_cancelamento_exige_permissao_e_evento_correto(self):
        self.client.post(self.url, {"inscricao": self.presencial.pk})
        self.operador.user_permissions.remove(Permission.objects.get(codename="add_credenciamento"))
        self.assertEqual(self.client.post(self.url, {"inscricao": self.presencial.pk, "acao": "cancelar"}).status_code, 403)
        self.assertTrue(Credenciamento.objects.exists())
        self.operador.user_permissions.add(Permission.objects.get(codename="add_credenciamento"))
        self.atividade.pk = None
        self.atividade.save()
        outro = reverse("atividade_credenciamento", args=[self.atividade.pk])
        self.assertEqual(self.client.post(outro, {"inscricao": self.presencial.pk, "acao": "cancelar"}).status_code, 404)
        self.assertTrue(Credenciamento.objects.exists())

    def test_acao_invalida_nao_credencia(self):
        self.assertEqual(self.client.post(self.url, {"inscricao": self.presencial.pk, "acao": "invalida"}).status_code, 400)
        self.assertFalse(Credenciamento.objects.exists())

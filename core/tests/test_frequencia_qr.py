from datetime import timedelta
from unittest.mock import patch

from django.core import signing
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse, set_script_prefix
from django.utils import timezone

from core.models import ChamadaFrequencia, Frequencia
from core.services.frequencia import registrar_direto
from core.tests import test_frequencia


class FrequenciaQRTests(TestCase):
    setUp = test_frequencia.FrequenciaTests.setUp

    def token(self, programacao=None):
        return signing.Signer(salt="frequencia.programacao").sign(
            f"{self.atividade.pk}:{(programacao or self.presencial).pk}")

    def url(self, programacao=None):
        return reverse("frequencia_confirmar_presencial", args=[self.token(programacao)])

    def pdf_url(self, programacao=None):
        return reverse("frequencia_qr_pdf", args=[self.atividade.pk, (programacao or self.presencial).pk])

    @override_settings(PUBLIC_BASE_URL="https://exemplo.org/eventos")
    def test_pdf_botao_e_url_publica_com_prefixo(self):
        self.client.force_login(self.responsavel)
        pagina = self.client.get(reverse("frequencia_index"))
        self.assertContains(pagina, self.pdf_url(), count=1)
        self.assertNotContains(pagina, self.pdf_url(self.online))
        from core.services.frequencia_qr_pdf import gerar_frequencia_qr_pdf
        from core.views.frequencia import frequencia_qr_pdf
        request = RequestFactory().get(self.pdf_url())
        request.user = self.responsavel
        with patch("core.views.frequencia.gerar_frequencia_qr_pdf", wraps=gerar_frequencia_qr_pdf) as gerar:
            try:
                set_script_prefix("/eventos/")
                resposta = frequencia_qr_pdf(request, self.atividade.pk, self.presencial.pk)
            finally:
                set_script_prefix("/")
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta["Content-Type"], "application/pdf")
            self.assertTrue(b"".join(resposta.streaming_content).startswith(b"%PDF-"))
            self.assertEqual(gerar.call_args.args[2], "https://exemplo.org/eventos" + self.url())

    def test_download_restrito_e_apenas_presencial(self):
        self.assertEqual(self.client.get(self.pdf_url()).status_code, 302)
        self.client.force_login(self.participante)
        self.assertEqual(self.client.get(self.pdf_url()).status_code, 403)
        self.client.force_login(self.responsavel)
        self.assertEqual(self.client.get(self.pdf_url(self.online)).status_code, 404)

    def test_login_leitura_sem_registro_confirmacao_e_duplicidade(self):
        resposta = self.client.get(self.url())
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("next=", resposta.url)
        self.client.force_login(self.participante)
        self.assertContains(self.client.get(self.url()), "Confirmar minha presença")
        self.assertFalse(Frequencia.objects.exists())
        antes = ChamadaFrequencia.objects.count()
        for _ in range(2):
            self.assertEqual(self.client.post(self.url()).status_code, 302)
        registro = Frequencia.objects.get()
        self.assertEqual(registro.inscricao, self.inscricao)
        self.assertEqual(registro.programacao, self.presencial)
        self.assertEqual(registro.registrada_por, self.participante)
        self.assertEqual(registro.metodo, Frequencia.Metodo.QR_PROPRIO)
        self.assertEqual(ChamadaFrequencia.objects.count(), antes + 1)
        self.assertContains(self.client.get(self.url()), "já está confirmada")

    def test_rejeita_token_adulterado_online_e_nao_inscrito(self):
        self.client.force_login(self.participante)
        self.assertEqual(self.client.get(reverse("frequencia_confirmar_presencial", args=[self.token() + "x"])).status_code, 400)
        self.assertEqual(self.client.post(self.url(self.online)).status_code, 404)
        self.client.force_login(self.outro)
        self.assertEqual(self.client.post(self.url(), {"inscricao": self.inscricao.pk}).status_code, 403)
        self.inscricao.modalidade = "online"
        self.inscricao.save()
        self.client.force_login(self.participante)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
        self.assertFalse(Frequencia.objects.exists())

    def test_evento_inativo_fora_periodo_ou_data_errada(self):
        self.client.force_login(self.participante)
        for campo, valor in (("ativo", False), ("data_inicio", timezone.now() + timedelta(days=1)),
                             ("data_fim", timezone.now() - timedelta(seconds=1))):
            original = getattr(self.atividade, campo)
            setattr(self.atividade, campo, valor)
            self.atividade.save()
            resposta = self.client.post(self.url())
            self.assertContains(resposta, "alert-danger")
            self.assertFalse(Frequencia.objects.exists())
            setattr(self.atividade, campo, original)
            self.atividade.save()
        self.presencial.data += timedelta(days=1)
        self.presencial.save()
        self.assertContains(self.client.post(self.url()), "somente na data")
        with self.assertRaises(ValidationError):
            registrar_direto(self.inscricao, self.presencial, self.participante, Frequencia.Metodo.QR_PROPRIO)
        self.assertFalse(Frequencia.objects.exists())

    def test_servico_nao_permite_confirmar_por_outro_usuario(self):
        with self.assertRaises(ValidationError):
            registrar_direto(self.inscricao, self.presencial, self.outro, Frequencia.Metodo.QR_PROPRIO)
        self.inscricao.programacoes.clear()
        with self.assertRaises(ValidationError):
            registrar_direto(self.inscricao, self.presencial, self.participante, Frequencia.Metodo.QR_PROPRIO)
        self.assertFalse(Frequencia.objects.exists())

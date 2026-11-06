from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.http import Http404
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import get_script_prefix, reverse, set_script_prefix
from django.utils import timezone

from core.models import Atividade
from core.services.atividade_inscricao_pdf import gerar_atividade_inscricao_pdf
from core.views.atividade_inscricao_pdf import atividade_inscricao_pdf, atividade_programacao_pdf


@override_settings(PUBLIC_BASE_URL="https://www.ce.ufpb.br/catedraunescoeja/eventos")
class AtividadeInscricaoPdfTests(SimpleTestCase):
    def setUp(self):
        self.atividade = Atividade(
            pk=42, titulo="Seminário de Educação & Cidadania", endereco="Auditório central",
            data_inicio=timezone.now() + timedelta(days=10),
            inscricoes_fim=timezone.now() + timedelta(days=5),
        )

    def request(self, permissao=None):
        request = RequestFactory().get(reverse("atividade_inscricao_pdf", args=[42]), secure=True)
        request.user = SimpleNamespace(is_authenticated=True, has_perm=lambda nome: nome == permissao)
        return request

    def test_pdf_contains_registration_url_in_qr(self):
        url = "https://example.com/atividades/42/inscricao/"
        with patch("core.services.atividade_inscricao_pdf.QrCodeWidget", wraps=__import__(
            "reportlab.graphics.barcode.qr", fromlist=["QrCodeWidget"]
        ).QrCodeWidget) as qr:
            arquivo = gerar_atividade_inscricao_pdf(self.atividade, url)
        qr.assert_called_once_with(url, barLevel="M")
        self.assertTrue(arquivo.read().startswith(b"%PDF-"))

    def test_download_uses_absolute_registration_url_and_management_permissions(self):
        for permissao in ("core.view_atividade", "core.change_atividade"):
            with self.subTest(permissao=permissao), patch(
                "core.views.atividade_inscricao_pdf.get_object_or_404", return_value=self.atividade
            ), patch("core.views.atividade_inscricao_pdf.gerar_atividade_inscricao_pdf", wraps=gerar_atividade_inscricao_pdf) as gerar:
                response = atividade_inscricao_pdf(self.request(permissao), 42)
                self.assertEqual(response["Content-Type"], "application/pdf")
                self.assertIn('attachment; filename="inscricao-seminario-de-educacao-cidadania.pdf"', response["Content-Disposition"])
                gerar.assert_called_once_with(self.atividade, "https://www.ce.ufpb.br/catedraunescoeja/eventos/atividades/42/inscricao/")
                response.close()

    def test_public_url_for_each_activity_with_proxy_prefix(self):
        prefixo = get_script_prefix()
        self.addCleanup(set_script_prefix, prefixo)
        set_script_prefix("/catedraunescoeja/eventos/")
        for pk in (1, 42, 123):
            self.atividade.pk = pk
            with self.subTest(pk=pk), patch(
                "core.views.atividade_inscricao_pdf.get_object_or_404", return_value=self.atividade
            ), patch("core.views.atividade_inscricao_pdf.gerar_atividade_inscricao_pdf", wraps=gerar_atividade_inscricao_pdf) as gerar:
                response = atividade_inscricao_pdf(self.request("core.view_atividade"), pk)
                gerar.assert_called_once_with(self.atividade, f"https://www.ce.ufpb.br/catedraunescoeja/eventos/atividades/{pk}/inscricao/")
                response.close()

    @override_settings(PUBLIC_BASE_URL="https://outro.example/eventos/")
    def test_public_base_is_configurable(self):
        with patch("core.views.atividade_inscricao_pdf.get_object_or_404", return_value=self.atividade), patch(
            "core.views.atividade_inscricao_pdf.gerar_atividade_inscricao_pdf", wraps=gerar_atividade_inscricao_pdf
        ) as gerar:
            response = atividade_inscricao_pdf(self.request("core.view_atividade"), 42)
            gerar.assert_called_once_with(self.atividade, "https://outro.example/eventos/atividades/42/inscricao/")
            response.close()

    def test_denies_user_without_management_permission(self):
        with self.assertRaises(PermissionDenied):
            atividade_inscricao_pdf(self.request(), 42)

    def test_anonymous_user_is_redirected_to_login(self):
        request = self.request()
        request.user.is_authenticated = False
        response = atividade_inscricao_pdf(request, 42)
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response.url)

    def test_schedule_pdf_encodes_the_attachment_download_url(self):
        self.atividade.arquivo_programacao = "atividades/programacoes/programacao.pdf"
        with patch("core.views.atividade_inscricao_pdf.get_object_or_404", return_value=self.atividade), patch(
            "core.views.atividade_inscricao_pdf.gerar_atividade_inscricao_pdf", wraps=gerar_atividade_inscricao_pdf
        ) as gerar:
            response = atividade_programacao_pdf(self.request("core.view_atividade"), 42)
        self.addCleanup(response.close)
        gerar.assert_called_once_with(
            self.atividade,
            f"https://www.ce.ufpb.br/catedraunescoeja/eventos/atividades/programacao/{self.atividade.token_programacao_publica}/",
            programacao=True,
        )
        self.assertIn('attachment; filename="programacao-seminario-de-educacao-cidadania.pdf"', response["Content-Disposition"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))

    def test_schedule_pdf_requires_an_attachment(self):
        with patch("core.views.atividade_inscricao_pdf.get_object_or_404", return_value=self.atividade):
            with self.assertRaises(Http404):
                atividade_programacao_pdf(self.request("core.view_atividade"), 42)

    def test_public_schedule_download_without_login(self):
        arquivo = ContentFile(b"Programacao", name="programacao.txt")
        atividade = SimpleNamespace(arquivo_programacao=arquivo)
        url = reverse("atividade_programacao_publica", args=[self.atividade.token_programacao_publica])
        with patch("core.views.dashboard.get_object_or_404", return_value=atividade) as buscar:
            response = self.client.get(url)
        self.addCleanup(response.close)
        self.assertEqual(buscar.call_args.kwargs["pk"], "42")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="programacao.txt"')
        self.assertEqual(b"".join(response.streaming_content), b"Programacao")

    def test_public_schedule_rejects_an_invalid_signature(self):
        url = reverse("atividade_programacao_publica", args=[f"{self.atividade.token_programacao_publica}x"])
        self.assertEqual(self.client.get(url).status_code, 404)

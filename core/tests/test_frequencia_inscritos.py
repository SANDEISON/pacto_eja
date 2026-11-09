from unittest.mock import patch

from django.urls import reverse
from django.test import TestCase
from django.utils.text import slugify

from core.models import Inscricao
from core.tests import test_frequencia


class ListaInscritosTests(TestCase):
    setUp = test_frequencia.FrequenciaTests.setUp

    def pdf_url(self, modalidade="presencial", programacao=None):
        return reverse("frequencia_inscritos_pdf", args=[
            self.atividade.pk, (programacao or self.presencial).pk, modalidade,
        ])

    def test_download_e_botoes(self):
        self.client.force_login(self.responsavel)
        pagina = self.client.get(reverse("frequencia_index"))
        self.assertContains(pagina, "Baixar inscritos (PDF)", count=2)
        for programacao in (self.presencial, self.online):
            url = self.pdf_url(programacao.modalidade, programacao)
            self.assertContains(pagina, url, count=1)
            outra_modalidade = "online" if programacao.modalidade == "presencial" else "presencial"
            self.assertNotContains(pagina, self.pdf_url(outra_modalidade, programacao))
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta["Content-Type"], "application/pdf")
            self.assertIn("attachment;", resposta["Content-Disposition"])
            self.assertIn(f'filename="inscritos-{slugify(str(programacao))}.pdf"',
                          resposta["Content-Disposition"])
            self.assertTrue(b"".join(resposta.streaming_content).startswith(b"%PDF-"))

    def test_restringe_acesso_e_modalidade(self):
        self.assertEqual(self.client.get(self.pdf_url()).status_code, 302)
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(self.pdf_url()).status_code, 403)
        self.client.force_login(self.responsavel)
        self.assertEqual(self.client.get(self.pdf_url("invalida")).status_code, 404)
        self.atividade.programacoes.remove(self.presencial)
        self.assertEqual(self.client.get(self.pdf_url()).status_code, 404)

    def test_filtra_evento_programacao_e_modalidade(self):
        online = Inscricao.objects.create(usuario=self.outro, atividade=self.atividade, modalidade="online")
        online.programacoes.add(self.online)
        self.client.force_login(self.responsavel)
        from core.services.lista_inscritos import gerar_lista_inscritos

        with patch("core.views.frequencia.gerar_lista_inscritos", wraps=gerar_lista_inscritos) as gerar:
            for modalidade, programacao, esperados in (
                ("presencial", self.presencial, [self.inscricao]),
                ("online", self.presencial, []),
                ("online", self.online, [online]),
            ):
                resposta = self.client.get(self.pdf_url(modalidade, programacao))
                self.assertEqual(list(gerar.call_args.args[3]), esperados)
                resposta.close()

    def test_pdf_online_inclui_inscrito_presencial_que_acessou_sala_publica(self):
        self.online.publica = True
        self.online.link = "https://example.com/sala"
        self.online.save(update_fields=["publica", "link"])
        self.client.force_login(self.participante)
        acesso = reverse("atividade_acessar_sala_online_publica", args=[self.atividade.pk, self.online.pk])
        self.assertRedirects(self.client.post(acesso), self.online.link, fetch_redirect_response=False)
        self.client.force_login(self.responsavel)

        from core.services.lista_inscritos import gerar_lista_inscritos

        with patch("core.views.frequencia.gerar_lista_inscritos", wraps=gerar_lista_inscritos) as gerar:
            resposta = self.client.get(self.pdf_url("online", self.online))
            self.assertEqual(list(gerar.call_args.args[3]), [self.inscricao])
            resposta.close()

    def test_ordena_nomes_com_acentos_e_escapa_marcacao(self):
        from types import SimpleNamespace
        from core.services.lista_inscritos import gerar_lista_inscritos
        from reportlab.platypus import SimpleDocTemplate

        nomes = ["zilda", "Bruno", "Ágata <Silva>", "ana"]
        inscricoes = [SimpleNamespace(usuario=SimpleNamespace(get_full_name=lambda n=n: n)) for n in nomes]
        with patch.object(SimpleDocTemplate, "build") as build:
            gerar_lista_inscritos(self.atividade, self.presencial, "presencial", inscricoes)
        tabela = build.call_args.args[0][-1]
        self.assertEqual([linha[1].getPlainText() for linha in tabela._cellvalues[1:]],
                         ["Ágata <Silva>", "ana", "Bruno", "zilda"])

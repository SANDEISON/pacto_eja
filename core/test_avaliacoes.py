from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    Avaliacao,
    Atividade,
    CandidaturaAvaliador,
    ChamadaAvaliadores,
    Coautor,
    DesignacaoAvaliacao,
    Inscricao,
    Trabalho,
)


class AvaliacaoFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.autor = User.objects.create_user(username="autor@example.com", password="SenhaForte2026!")
        self.avaliador = User.objects.create_user(
            username="avaliador@example.com", first_name="Ana", last_name="Avaliadora", password="SenhaForte2026!"
        )
        self.outro = User.objects.create_user(username="outro@example.com", password="SenhaForte2026!")
        self.admin = User.objects.create_superuser(username="admin@example.com", password="SenhaForte2026!")
        agora = timezone.now()
        self.atividade = Atividade.objects.create(
            tipo=Atividade.Tipo.EVENTO,
            titulo="Encontro de práticas da EJA",
            descricao="Evento com submissão de experiências.",
            local="Auditório",
            data_inicio=agora + timedelta(days=30),
            data_fim=agora + timedelta(days=31),
            inscricoes_inicio=agora - timedelta(days=5),
            inscricoes_fim=agora + timedelta(days=5),
            permite_submissao=True,
            submissoes_fim=agora + timedelta(days=10),
        )
        self.chamada = ChamadaAvaliadores.objects.create(
            atividade=self.atividade,
            titulo="Chamada de avaliadores 2026",
            descricao="Seleção de pareceristas.",
            requisitos="Experiência com educação de jovens e adultos.",
            inscricoes_inicio=agora - timedelta(days=1),
            inscricoes_fim=agora + timedelta(days=3),
            avaliacoes_fim=agora + timedelta(days=20),
        )

    def criar_trabalho(self):
        inscricao = Inscricao.objects.create(atividade=self.atividade, usuario=self.autor)
        return Trabalho.objects.create(
            inscricao=inscricao,
            titulo="Saberes construídos na EJA",
            arquivo=SimpleUploadedFile("trabalho.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"),
        )

    def aprovar_avaliador(self, usuario=None):
        return CandidaturaAvaliador.objects.create(
            chamada=self.chamada,
            usuario=usuario or self.avaliador,
            area_atuacao="Educação",
            experiencia="Pesquisa e docência na EJA.",
            temas_interesse="Práticas pedagógicas",
            status=CandidaturaAvaliador.Status.APROVADA,
        )

    def test_usuario_pode_enviar_apenas_uma_candidatura(self):
        self.client.force_login(self.avaliador)
        dados = {
            "area_atuacao": "Educação",
            "experiencia": "Cinco anos de docência.",
            "temas_interesse": "Alfabetização",
            "conflitos_de_interesse": "",
            "declaracao": "on",
        }
        primeira = self.client.post(reverse("candidatar_avaliador", args=[self.chamada.pk]), dados)
        segunda = self.client.post(reverse("candidatar_avaliador", args=[self.chamada.pk]), dados)
        self.assertRedirects(primeira, reverse("chamadas_avaliadores"))
        self.assertRedirects(segunda, reverse("chamadas_avaliadores"))
        self.assertEqual(CandidaturaAvaliador.objects.filter(usuario=self.avaliador).count(), 1)

    def test_coordenacao_registra_aprovacao_e_responsavel(self):
        candidatura = self.aprovar_avaliador()
        candidatura.status = CandidaturaAvaliador.Status.PENDENTE
        candidatura.save()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("decidir_candidatura", args=[candidatura.pk]),
            {"acao": "aprovada", "justificativa_decisao": "Perfil compatível."},
        )
        self.assertRedirects(response, reverse("candidatura_avaliador_list", args=[self.chamada.pk]))
        candidatura.refresh_from_db()
        self.assertEqual(candidatura.status, CandidaturaAvaliador.Status.APROVADA)
        self.assertEqual(candidatura.analisada_por, self.admin)
        self.assertIsNotNone(candidatura.analisada_em)

    def test_autor_ou_coautor_nao_pode_receber_o_proprio_trabalho(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            trabalho = self.criar_trabalho()
            self.aprovar_avaliador(self.autor)
            designacao = DesignacaoAvaliacao(trabalho=trabalho, avaliador=self.autor, liberada_por=self.admin)
            with self.assertRaises(ValidationError):
                designacao.full_clean()

            Coautor.objects.create(trabalho=trabalho, usuario=self.avaliador, nome="Ana Avaliadora", email="avaliador@example.com")
            self.aprovar_avaliador(self.avaliador)
            designacao = DesignacaoAvaliacao(trabalho=trabalho, avaliador=self.avaliador, liberada_por=self.admin)
            with self.assertRaises(ValidationError):
                designacao.full_clean()

    def test_somente_avaliador_designado_acessa_trabalho_e_parecer(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            trabalho = self.criar_trabalho()
            self.aprovar_avaliador()
            designacao = DesignacaoAvaliacao.objects.create(
                trabalho=trabalho, avaliador=self.avaliador, liberada_por=self.admin, prazo=self.chamada.avaliacoes_fim
            )
            self.client.force_login(self.outro)
            self.assertEqual(self.client.get(reverse("trabalho_download", args=[trabalho.pk])).status_code, 404)
            self.assertEqual(self.client.get(reverse("preencher_avaliacao", args=[designacao.pk])).status_code, 404)

            self.client.force_login(self.avaliador)
            download = self.client.get(reverse("trabalho_download", args=[trabalho.pk]))
            self.assertEqual(download.status_code, 200)
            for closer in download._resource_closers:
                closer()
            download._resource_closers.clear()
            self.assertEqual(self.client.get(reverse("preencher_avaliacao", args=[designacao.pk])).status_code, 200)

    def test_avaliador_salva_rascunho_e_conclui_parecer(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            trabalho = self.criar_trabalho()
            self.aprovar_avaliador()
            designacao = DesignacaoAvaliacao.objects.create(
                trabalho=trabalho, avaliador=self.avaliador, prazo=self.chamada.avaliacoes_fim
            )
            self.client.force_login(self.avaliador)
            rascunho = self.client.post(
                reverse("preencher_avaliacao", args=[designacao.pk]),
                {"acao": "rascunho", "parecer": "Análise iniciada."},
            )
            self.assertRedirects(rascunho, reverse("preencher_avaliacao", args=[designacao.pk]))
            self.assertEqual(designacao.avaliacao.status, Avaliacao.Status.RASCUNHO)

            dados = {
                "acao": "concluir",
                "nota_relevancia": "5",
                "nota_metodologia": "4",
                "nota_clareza": "5",
                "nota_contribuicao": "5",
                "parecer": "Trabalho consistente e relevante.",
                "observacoes_autor": "Explicitar melhor os procedimentos.",
                "recomendacao": Avaliacao.Recomendacao.ACEITAR_AJUSTES,
            }
            concluida = self.client.post(reverse("preencher_avaliacao", args=[designacao.pk]), dados)
            self.assertRedirects(concluida, reverse("minhas_avaliacoes"))
            designacao.avaliacao.refresh_from_db()
            self.assertEqual(designacao.avaliacao.status, Avaliacao.Status.CONCLUIDA)
            self.assertEqual(designacao.avaliacao.media, 4.75)
            self.assertIsNotNone(designacao.avaliacao.concluida_em)

    def test_telas_publicas_e_administrativas_renderizam_o_fluxo(self):
        self.client.force_login(self.avaliador)
        chamadas = self.client.get(reverse("chamadas_avaliadores"))
        self.assertEqual(chamadas.status_code, 200)
        self.assertContains(chamadas, "Quero ser avaliador(a)")
        self.assertContains(self.client.get(reverse("candidatar_avaliador", args=[self.chamada.pk])), "Experiência e áreas")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            trabalho = self.criar_trabalho()
            self.aprovar_avaliador()
            designacao = DesignacaoAvaliacao.objects.create(
                trabalho=trabalho, avaliador=self.avaliador, prazo=self.chamada.avaliacoes_fim
            )
            avaliacao = Avaliacao.objects.create(designacao=designacao, parecer="Parecer em elaboração.")
            self.client.force_login(self.admin)
            for url in (
                reverse("chamada_avaliadores_list"),
                reverse("chamada_avaliadores_update", args=[self.chamada.pk]),
                reverse("candidatura_avaliador_list", args=[self.chamada.pk]),
                reverse("designacao_avaliacao_manage", args=[self.chamada.pk]),
                reverse("avaliacao_management_detail", args=[avaliacao.pk]),
            ):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_dashboard_do_usuario_comum_exibe_chamada_para_avaliadores(self):
        self.client.force_login(self.avaliador)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inscrições e chamadas abertas")
        self.assertContains(response, self.chamada.titulo)
        self.assertContains(response, "Quero ser avaliador(a)")
        self.assertContains(response, 'id="atividades-tab"')
        self.assertContains(response, 'data-bs-target="#atividades-pane"')
        self.assertContains(response, 'id="avaliadores-tab"')
        self.assertContains(response, 'data-bs-target="#avaliadores-pane"')

        self.admin.is_staff = True
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, 'id="chamadas-avaliadores-title"')

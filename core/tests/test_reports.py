from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Atividade, Formacao, Inscricao, Nivel, Situacao


class ReportsViewTests(TestCase):
    """Garante acesso e serialização segura dos dados dos relatórios."""

    def test_reports_require_staff_user(self):
        usuario = get_user_model().objects.create_user(
            username="52998224725",
            password="SenhaForte2026!",
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse("reports"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:signin')}?next={reverse('reports')}",
            fetch_redirect_response=False,
        )

    def test_reports_prepare_participants_and_safe_json(self):
        usuario = get_user_model().objects.create_user(
            username="52998224725",
            password="SenhaForte2026!",
            is_staff=True,
            first_name="Maria </script>",
        )
        usuario.educador.nome_completo = "Maria </script>"
        usuario.educador.save()

        nivel, _ = Nivel.objects.get_or_create(codigo="mestrado", defaults={"nome": "Mestrado"})
        situacao, _ = Situacao.objects.get_or_create(codigo="concluido", defaults={"nome": "Concluído"})
        Formacao.objects.create(
            educador=usuario.educador,
            nivel=nivel,
            nome_curso="Educação e Sociedade",
            instituicao="Universidade Federal",
            situacao=situacao,
        )

        self.client.force_login(usuario)

        response = self.client.get(reverse("reports"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_educadores"], 1)
        self.assertEqual(
            response.context["participantes_detalhados"][0]["nome"],
            "Maria </script>",
        )
        self.assertEqual(
            response.context["participantes_detalhados"][0]["escolaridade"],
            "Mestrado",
        )
        self.assertEqual(
            response.context["participantes_detalhados"][0]["representante_undime_consed"],
            "Não informado",
        )
        self.assertIn("escolaridade_dados", response.context)
        self.assertEqual(
            response.context["escolaridade_dados"][0]["label"],
            "Mestrado",
        )
        self.assertEqual(
            response.context["escolaridade_dados"][0]["qtd"],
            1,
        )
        self.assertContains(response, r"Maria \u003C/script\u003E")
        self.assertNotContains(response, "Maria </script>")

    def test_reports_include_activities_and_inscricoes(self):
        usuario = get_user_model().objects.create_user(
            username="52998224726",
            password="SenhaForte2026!",
            is_staff=True,
            first_name="João",
        )
        usuario.educador.nome_completo = "João da Silva"
        usuario.educador.save()

        agora = timezone.now()
        atividade = Atividade.objects.create(
            titulo="Oficina EJA 2026",
            descricao="Treinamento pedagógico",
            tipo=Atividade.Tipo.CURSO,
            modalidade=Atividade.ModalidadeParticipacao.PRESENCIAL,
            data_inicio=agora + timezone.timedelta(days=10),
            data_fim=agora + timezone.timedelta(days=12),
            inscricoes_fim=agora + timezone.timedelta(days=5),
            local="Centro de Formação",
        )
        Inscricao.objects.create(
            atividade=atividade,
            usuario=usuario,
            modalidade=Inscricao.Modalidade.PRESENCIAL,
        )

        self.client.force_login(usuario)
        response = self.client.get(reverse("reports"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("atividades_catalogo", response.context)
        self.assertIn("atividade_dados", response.context)
        self.assertEqual(len(response.context["atividades_catalogo"]), 1)
        self.assertEqual(response.context["atividades_catalogo"][0]["titulo"], "Oficina EJA 2026")

        participantes = response.context["participantes_detalhados"]
        self.assertEqual(len(participantes), 1)
        self.assertIn(atividade.id, participantes[0]["atividades_ids"])
        self.assertEqual(participantes[0]["atividades"][0]["titulo"], "Oficina EJA 2026")

    def test_reports_filter_by_specific_activity(self):
        agora = timezone.now()
        staff_user = get_user_model().objects.create_user(
            username="52998224727",
            password="SenhaForte2026!",
            is_staff=True,
            first_name="Admin",
        )

        user_inscrito = get_user_model().objects.create_user(
            username="52998224728",
            password="SenhaForte2026!",
            first_name="Aluno",
        )
        user_inscrito.educador.nome_completo = "Aluno Inscrito"
        user_inscrito.educador.save()

        user_nao_inscrito = get_user_model().objects.create_user(
            username="52998224729",
            password="SenhaForte2026!",
            first_name="Outro",
        )
        user_nao_inscrito.educador.nome_completo = "Educador Fora"
        user_nao_inscrito.educador.save()

        atividade = Atividade.objects.create(
            titulo="Seminário EJA Exclusivo",
            descricao="Foco EJA",
            tipo=Atividade.Tipo.EVENTO,
            modalidade=Atividade.ModalidadeParticipacao.ONLINE,
            data_inicio=agora + timezone.timedelta(days=10),
            data_fim=agora + timezone.timedelta(days=11),
            inscricoes_fim=agora + timezone.timedelta(days=5),
            local="https://meet.google.com/exclusivo",
        )

        Inscricao.objects.create(
            atividade=atividade,
            usuario=user_inscrito,
            modalidade=Inscricao.Modalidade.ONLINE,
        )

        self.client.force_login(staff_user)
        # Request with ?atividade=<id>
        response = self.client.get(reverse("reports") + f"?atividade={atividade.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["atividade_selecionada"])
        self.assertEqual(response.context["atividade_selecionada"]["id"], atividade.id)
        self.assertEqual(response.context["total_educadores"], 1)

        participantes = response.context["participantes_detalhados"]
        self.assertEqual(len(participantes), 1)
        self.assertEqual(participantes[0]["nome"], "Aluno Inscrito")
        self.assertEqual(participantes[0]["modalidade_inscrito_atual"], "On-line")
        self.assertIsNotNone(participantes[0]["data_inscricao_atual"])



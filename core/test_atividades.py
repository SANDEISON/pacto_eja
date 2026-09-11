from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Atividade, Coautor, Inscricao, Trabalho


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
        return {
            "usuario-full_name": "Participante da Silva",
            "usuario-email": "participante@example.com",
            "dados-cpf": "529.982.247-25",
            "dados-data_nascimento": "1990-05-12",
            "dados-telefone": "(82) 99999-9999",
        }

    def test_dashboard_shows_activity_with_open_registration(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.atividade.titulo)
        self.assertContains(response, "Inscrever-se")
        self.assertContains(response, "google.com/maps/search/")

    def test_registration_page_links_address_to_maps(self):
        response = self.client.get(reverse("atividade_inscricao", args=[self.atividade.pk]))
        self.assertContains(response, "Inscrição em evento")
        self.assertContains(response, "Continuar")
        self.assertContains(response, "Deseja cadastrar um trabalho neste evento?")
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

    def test_work_submission_requires_a_real_pdf(self):
        data = self.personal_data() | {
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
            data = self.personal_data() | {
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
            self.assertTrue(Coautor.objects.filter(trabalho=trabalho, nome="Pessoa Coautora").exists())
            download = self.client.get(reverse("trabalho_download", args=[trabalho.pk]))
            self.assertEqual(download.status_code, 200)
            for closer in download._resource_closers:
                closer()
            download._resource_closers.clear()

    def test_work_rejects_coauthor_not_registered_on_platform(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            data = self.personal_data() | {
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
        self.assertContains(response, "Use este campo somente para o acesso ao evento on-line.")

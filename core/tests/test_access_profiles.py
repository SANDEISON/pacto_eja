from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.constants import SENHA_INICIAL
from core.models import Atividade, Credenciamento, Inscricao, ProgramacaoSala, Sala, TematicaSala


class AccessProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for profile in ("Administrador", "Coordenador", "Analista", "Educador"):
            user = get_user_model().objects.create_user(username=profile.lower())
            user.groups.add(Group.objects.get(name=profile))
            cls.users[profile] = user

    def test_access_to_management_and_reports(self):
        expected_status = {
            "Administrador": (200, 200, 200, 200),
            "Coordenador": (403, 403, 200, 200),
            "Analista": (403, 403, 403, 200),
            "Educador": (403, 403, 403, 302),
        }
        routes = ("user_list", "group_list", "atividade_create", "reports")
        for profile, statuses in expected_status.items():
            self.client.force_login(self.users[profile])
            for route, status in zip(routes, statuses, strict=True):
                with self.subTest(profile=profile, route=route):
                    self.assertEqual(self.client.get(reverse(route)).status_code, status)

    def test_administrator_can_assign_a_profile_without_django_admin_access(self):
        self.client.force_login(self.users["Administrador"])
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "529.982.247-25",
                "password1": "SenhaForte2026!",
                "password2": "SenhaForte2026!",
                "is_active": "on",
                "is_staff": "on",
                "groups": [Group.objects.get(name="Analista").pk],
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        created = get_user_model().objects.get(username="52998224725")
        self.assertFalse(created.is_staff)
        self.assertTrue(created.has_perm("core.view_relatorios"))
        self.assertFalse(created.has_perm("auth.change_user"))

    def test_analyst_can_view_educators_and_activities_without_mutation_links(self):
        self.client.force_login(self.users["Analista"])
        educator = self.users["Educador"].educador
        now = timezone.now()
        activity = Atividade.objects.create(
            titulo="Evento de formação",
            data_inicio=now,
            data_fim=now,
            inscricoes_fim=now,
        )

        educators = self.client.get(reverse("educator_model_list"))
        delete_url = reverse("catalog_delete", args=["cadastros-educadores", educator.pk])
        self.assertContains(educators, educator.nome_completo)
        self.assertNotContains(educators, delete_url)
        edit_url = reverse("catalog_update", args=["cadastros-educadores", educator.pk])
        reset_url = reverse("educator_password_reset", args=[educator.pk])
        self.assertContains(educators, edit_url)
        self.assertContains(educators, reset_url)
        edit_response = self.client.get(edit_url)
        self.assertEqual(edit_response.status_code, 200)
        self.assertNotIn("usuario", edit_response.context["form"].fields)
        self.assertRedirects(self.client.post(reset_url), reverse("educator_model_list"))
        educator.usuario.refresh_from_db()
        self.assertTrue(educator.usuario.check_password(SENHA_INICIAL))
        admin_educator = self.users["Administrador"].educador
        self.assertEqual(
            self.client.post(reverse("educator_password_reset", args=[admin_educator.pk])).status_code,
            403,
        )
        self.assertEqual(self.client.post(delete_url).status_code, 403)

        activities = self.client.get(reverse("atividade_list"))
        update_url = reverse("atividade_update", args=[activity.pk])
        self.assertContains(activities, activity.titulo)
        self.assertNotContains(activities, update_url)
        self.assertEqual(self.client.get(update_url).status_code, 403)
        self.assertEqual(self.client.post(update_url).status_code, 403)

    def test_analyst_can_consult_registrations_and_operate_check_in_and_attendance(self):
        self.client.force_login(self.users["Analista"])
        now = timezone.now()
        activity = Atividade.objects.create(
            titulo="Encontro presencial", data_inicio=now, data_fim=now, inscricoes_fim=now,
        )
        schedule = ProgramacaoSala.objects.create(
            sala=Sala.objects.create(nome="Sala presencial"),
            tematica=TematicaSala.objects.create(nome="Formação"),
            data=timezone.localdate(),
            turno="manha",
            modalidade="presencial",
            quantidade_max_participantes=30,
            responsavel=self.users["Coordenador"],
        )
        activity.programacoes.add(schedule)
        registration = Inscricao.objects.create(atividade=activity, usuario=self.users["Educador"])
        registration.programacoes.add(schedule)

        registrations_url = reverse("atividade_inscricoes", args=[activity.pk])
        self.assertEqual(self.client.get(registrations_url).status_code, 200)
        self.assertEqual(self.client.post(registrations_url).status_code, 403)

        check_in_url = reverse("atividade_credenciamento", args=[activity.pk])
        self.assertContains(self.client.get(check_in_url), "Confirmar credenciamento")
        self.assertEqual(self.client.post(check_in_url, {"inscricao": registration.pk}).status_code, 302)
        self.assertTrue(Credenciamento.objects.filter(inscricao=registration).exists())
        self.assertContains(self.client.get(check_in_url), "Cancelar credenciamento")
        response = self.client.post(check_in_url, {"acao": "cancelar", "inscricao": registration.pk})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Credenciamento.objects.filter(inscricao=registration).exists())

        attendance_url = reverse("frequencia_sala", args=[activity.pk, schedule.pk])
        self.assertContains(self.client.get(reverse("frequencia_index")), attendance_url)
        self.assertEqual(self.client.get(attendance_url).status_code, 200)
        response = self.client.post(attendance_url, {"acao": "manual", "inscricao": registration.pk})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(registration.frequencias.filter(programacao=schedule).exists())
        response = self.client.post(attendance_url, {"acao": "cancelar", "inscricao": registration.pk})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(registration.frequencias.filter(programacao=schedule).exists())

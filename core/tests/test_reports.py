from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Atividade,
    Cidade,
    EducadorEscola,
    Escola,
    Estado,
    Formacao,
    Funcao,
    FuncaoCaracterizacaoTurma,
    FuncaoEducador,
    Inscricao,
    Nivel,
    ProgramacaoSala,
    Refeicao,
    Sala,
    Situacao,
    TematicaSala,
)


class ReportsQueryCountTests(TestCase):
    def test_consultas_nao_crescem_com_participantes_da_mesma_atividade(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from core.views.reports import listar_participantes_detalhados

        agora = timezone.now()
        atividade = Atividade.objects.create(
            titulo="Relatório de desempenho", vagas=100,
            data_inicio=agora, data_fim=agora,
            inscricoes_fim=agora + timezone.timedelta(days=1),
        )
        sala = Sala.objects.create(nome="Sala de teste")
        tematica = TematicaSala.objects.create(nome="Temática de teste")
        for turno in ("manha", "tarde"):
            atividade.programacoes.add(ProgramacaoSala.objects.create(
                sala=sala, tematica=tematica, data=agora.date(), turno=turno,
                modalidade="presencial",
                quantidade_max_participantes=100,
            ))

        def inscrever(indice):
            usuario = get_user_model().objects.create_user(username=f"desempenho-{indice}")
            inscricao = Inscricao.objects.create(usuario=usuario, atividade=atividade)
            inscricao.programacoes.set(atividade.programacoes.all())

        inscrever(0)
        with CaptureQueriesContext(connection) as consultas_iniciais:
            participantes = listar_participantes_detalhados()
        self.assertTrue(participantes[0]["atividades"][0]["inscricoes_abertas"])

        for indice in range(1, 6):
            inscrever(indice)
        with CaptureQueriesContext(connection) as consultas_ampliadas:
            participantes = listar_participantes_detalhados()
        self.assertEqual(len(participantes), 6)
        self.assertEqual(len(consultas_iniciais), len(consultas_ampliadas))
        self.assertTrue(all(p["atividades"][0]["inscricoes_abertas"] for p in participantes))


class ReportsViewTests(TestCase):
    """Garante acesso e serialização segura dos dados dos relatórios."""

    def test_certificate_reports_include_registered_educators(self):
        from core.models import CursoCertificado

        usuario = get_user_model().objects.create_user(
            username="52998224725", is_staff=True, first_name="Educadora de Teste",
        )
        curso = CursoCertificado.objects.first()
        usuario.educador.cursos_certificados.add(curso)
        self.client.force_login(usuario)
        response = self.client.get(reverse("reports_certificados"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_solicitantes"], 1)
        self.assertEqual(response.context["participantes_detalhados"][0]["nome"], "Educadora de Teste")
        self.assertContains(response, 'id="participants-data"')
        self.assertContains(response, 'id="report-visualization-warning"')

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
            vagas=50,
            vagas_online=0,
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
        catalogo = response.context["atividades_catalogo"][0]
        for campo in ("data_inicio", "data_fim", "inscricoes_fim"):
            self.assertEqual(
                catalogo[campo],
                timezone.localtime(getattr(atividade, campo)).strftime("%d/%m/%Y %H:%M"),
            )

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
            vagas=50,
            vagas_online=0,
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

    def test_reports_include_programacoes_disponiveis_and_participants_selection(self):
        agora = timezone.now()
        staff_user = get_user_model().objects.create_user(
            username="52998224730",
            password="SenhaForte2026!",
            is_staff=True,
            first_name="Admin",
        )

        user_com_prog = get_user_model().objects.create_user(
            username="52998224731",
            password="SenhaForte2026!",
            first_name="Educador Com Programação",
        )
        user_com_prog.educador.nome_completo = "Educador Com Programação"
        user_com_prog.educador.save()

        sala = Sala.objects.create(nome="Auditório Principal")
        tematica = TematicaSala.objects.create(nome="Práticas em EJA")
        prog = ProgramacaoSala.objects.create(
            sala=sala,
            tematica=tematica,
            data=(agora + timezone.timedelta(days=10)).date(),
            turno=ProgramacaoSala.Turno.MANHA,
            modalidade=ProgramacaoSala.Modalidade.PRESENCIAL,
            quantidade_max_participantes=50,
        )

        atividade = Atividade.objects.create(
            vagas=50,
            vagas_online=0,
            titulo="Congresso EJA 2026",
            descricao="Congresso",
            tipo=Atividade.Tipo.EVENTO,
            modalidade=Atividade.ModalidadeParticipacao.PRESENCIAL,
            data_inicio=agora + timezone.timedelta(days=10),
            data_fim=agora + timezone.timedelta(days=11),
            inscricoes_fim=agora + timezone.timedelta(days=5),
            local="Centro de Convenções",
        )
        atividade.programacoes.add(prog)

        inscricao = Inscricao.objects.create(
            atividade=atividade,
            usuario=user_com_prog,
            modalidade=Inscricao.Modalidade.PRESENCIAL,
        )
        inscricao.programacoes.add(prog)
        refeicao = Refeicao.objects.create(
            atividade=atividade, tipo="almoco", data=prog.data, horario="12:00",
        )
        inscricao.refeicoes.add(refeicao)

        self.client.force_login(staff_user)
        response = self.client.get(reverse("reports") + f"?atividade={atividade.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("programacoes_catalogo", response.context)
        progs_cat = response.context["programacoes_catalogo"]
        self.assertEqual(len(progs_cat), 1)
        self.assertEqual(progs_cat[0]["id"], prog.id)
        self.assertIn("Auditório Principal", progs_cat[0]["label"])

        participantes = response.context["participantes_detalhados"]
        self.assertEqual(len(participantes), 1)
        self.assertIn(prog.id, participantes[0]["programacoes_ids"])
        self.assertEqual(len(participantes[0]["programacoes"]), 1)
        self.assertEqual(participantes[0]["programacoes"][0]["id"], prog.id)
        self.assertEqual(participantes[0]["atividades"][0]["datas"], [prog.data.isoformat()])
        self.assertEqual(participantes[0]["atividades"][0]["refeicoes_ids"], [refeicao.id])
        self.assertEqual(response.context["atividade_selecionada"]["datas"], [prog.data.isoformat()])
        self.assertEqual(response.context["atividade_selecionada"]["refeicoes"][0]["id"], refeicao.id)
        vagas = response.context["atividade_selecionada"]
        self.assertEqual(vagas["vagas_totais"], 50)
        self.assertEqual(vagas["vagas_preenchidas"], 1)
        self.assertEqual(vagas["vagas_disponiveis"], 49)
        self.assertEqual(vagas["vagas_presenciais_preenchidas"], 1)
        self.assertEqual(vagas["vagas_online_preenchidas"], 0)
        self.assertNotContains(response, "Distribuição de vagas")
        self.assertContains(response, 'id="filterDataAtividade"')
        self.assertContains(response, 'id="filterRefeicao"')
        self.assertEqual(participantes[0]["data_inscricao_atual"], timezone.localtime(inscricao.inscrito_em).strftime("%d/%m/%Y %H:%M"))
        self.assertEqual(participantes[0]["data_alteracao_atual"], "")
        self.assertContains(response, "Inscrito em:")
        inscricao.alterado_em = timezone.now()
        inscricao.save(update_fields=("alterado_em",))
        response_alterada = self.client.get(reverse("reports") + f"?atividade={atividade.id}")
        self.assertEqual(response_alterada.context["participantes_detalhados"][0]["data_alteracao_atual"], timezone.localtime(inscricao.alterado_em).strftime("%d/%m/%Y %H:%M"))
        self.assertContains(response, 'id="filterProgramacao"')
        # Tela inicial (Catálogo de Atividades)
        response_catalogo = self.client.get(reverse("reports"))
        self.assertEqual(response_catalogo.status_code, 200)
        self.assertNotContains(response_catalogo, "Distribuição de vagas")
        self.assertContains(response_catalogo, 'id="catalogFilterProgramacao"')
        self.assertEqual(response_catalogo.context["atividades_catalogo"][0]["total_programacoes"], 1)
        self.assertEqual(response_catalogo.context["atividades_catalogo"][0]["programacoes"][0]["id"], prog.id)

    def test_educator_with_multiple_school_assignments_does_not_duplicate_row_and_aggregates_schools(self):
        staff_user = get_user_model().objects.create_user(
            username="52998224799",
            password="SenhaForte2026!",
            is_staff=True,
            first_name="Admin",
        )
        user_educador = get_user_model().objects.create_user(
            username="52998224788",
            password="SenhaForte2026!",
            first_name="Educador Multi Escolas",
        )
        educador = user_educador.educador
        educador.nome_completo = "Educador Multi Escolas"
        educador.cpf = "01234567890"
        educador.save()

        estado, _ = Estado.objects.get_or_create(sigla="PB", defaults={"nome_estado": "Paraíba"})
        cidade, _ = Cidade.objects.get_or_create(nome_cidade="João Pessoa", estado=estado, defaults={"codigo_ibge": 2507507})
        escola1 = Escola.objects.create(id_escola=1001, nome="Escola Municipal Alpha", id_municipio=cidade.codigo_ibge, sigla_uf=estado.sigla)
        escola2 = Escola.objects.create(id_escola=1002, nome="Escola Estadual Beta", id_municipio=cidade.codigo_ibge, sigla_uf=estado.sigla)
        funcao = Funcao.objects.create(nome="Professor")
        caract = FuncaoCaracterizacaoTurma.objects.create(nome="EJA Regular")

        ee1 = EducadorEscola.objects.create(
            escola=escola1,
            cidade=cidade,
            funcao=funcao,
            funcao_caracterizacao_turmas=caract,
            tempo_atuacao=EducadorEscola.TempoAtuacao.ZERO_A_TRES_ANOS,
        )
        ee2 = EducadorEscola.objects.create(
            escola=escola2,
            cidade=cidade,
            funcao=funcao,
            funcao_caracterizacao_turmas=caract,
            tempo_atuacao=EducadorEscola.TempoAtuacao.QUATRO_A_SEIS_ANOS,
        )
        FuncaoEducador.objects.create(educador=educador, educador_escola=ee1)
        FuncaoEducador.objects.create(educador=educador, educador_escola=ee2)

        self.client.force_login(staff_user)
        response = self.client.get(reverse("reports"))

        self.assertEqual(response.status_code, 200)
        participantes = [p for p in response.context["participantes_detalhados"] if p["nome"] == "Educador Multi Escolas"]
        self.assertEqual(len(participantes), 1, "O educador não deve ter linhas duplicadas na lista de participantes")
        self.assertIn("Escola Municipal Alpha", participantes[0]["escola"])
        self.assertIn("Escola Estadual Beta", participantes[0]["escola"])
        self.assertEqual(participantes[0]["cpf"], "01234567890")





class ConfirmacaoUndimeTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="admin-undime", is_staff=True)
        self.usuario = get_user_model().objects.create_user(username="representante-undime")
        self.educador = self.usuario.educador
        self.educador.representante_estado_undime_consed = True
        self.educador.save()
        from django.contrib.auth.models import Permission
        self.permissao = Permission.objects.get(content_type__app_label="core", codename="view_inscricao")
        self.admin.user_permissions.add(self.permissao)
        agora = timezone.now()
        self.atividade = Atividade.objects.create(
            titulo="Evento Undime", data_inicio=agora, data_fim=agora, inscricoes_fim=agora,
        )
        Inscricao.objects.create(usuario=self.usuario, atividade=self.atividade)
        self.url = reverse("atividade_inscricoes", args=[self.atividade.pk])

    def test_confirma_e_preserva_primeiro_responsavel_e_horario(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "sim"})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.educador.refresh_from_db()
        self.assertEqual(self.educador.undime_confirmado_por, self.admin)
        self.assertIs(self.educador.undime_confirmada, True)
        horario = self.educador.undime_confirmado_em
        self.assertIsNotNone(horario)
        outro = get_user_model().objects.create_user(username="outro-admin", is_staff=True)
        outro.user_permissions.add(self.permissao)
        self.client.force_login(outro)
        self.client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "sim"})
        self.educador.refresh_from_db()
        self.assertEqual(self.educador.undime_confirmado_por, self.admin)
        self.assertEqual(self.educador.undime_confirmado_em, horario)
        from core.views.reports import dados_basicos_educador
        dados = dados_basicos_educador(self.educador)
        self.assertEqual(dados["undime_confirmado_por"], self.admin.username)
        self.assertTrue(dados["undime_confirmado_em"])

    def test_usuario_comum_nao_confirma(self):
        self.client.force_login(self.usuario)
        response = self.client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "sim"})
        self.assertEqual(response.status_code, 403)
        self.educador.refresh_from_db()
        self.assertIsNone(self.educador.undime_confirmado_em)

    def test_exige_resposta_sim(self):
        self.client.force_login(self.admin)
        for resposta in (False, None):
            self.educador.representante_estado_undime_consed = resposta
            self.educador.save()
            response = self.client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "sim"})
            self.assertEqual(response.status_code, 400)
        self.educador.refresh_from_db()
        self.assertIsNone(self.educador.undime_confirmado_em)

    def test_exige_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "sim"})
        self.assertEqual(response.status_code, 403)

    def test_registra_decisao_negativa(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "nao"})
        self.assertEqual(response.status_code, 302)
        self.educador.refresh_from_db()
        self.assertIs(self.educador.undime_confirmada, False)
        self.assertEqual(self.educador.undime_confirmado_por, self.admin)
        self.assertIsNotNone(self.educador.undime_confirmado_em)
        self.assertIs(self.educador.representante_estado_undime_consed, True)

    def test_exige_decisao_valida(self):
        self.client.force_login(self.admin)
        for decisao in (None, "", "invalida"):
            data = {"educador_id": self.educador.pk}
            if decisao is not None:
                data["undime_confirmada"] = decisao
            self.assertEqual(self.client.post(self.url, data).status_code, 400)
        self.educador.refresh_from_db()
        self.assertIsNone(self.educador.undime_confirmado_em)

    def test_salvamento_json_nao_recarrega_relatorio(self):
        from unittest.mock import patch
        self.client.force_login(self.admin)
        with patch("core.views.reports.ReportsView.get_context_data", side_effect=AssertionError("Relatório não deve ser recalculado")):
            response = self.client.post(
                self.url,
                {"educador_id": self.educador.pk, "undime_confirmada": "nao"},
                HTTP_ACCEPT="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["undime_confirmada"], False)
        self.assertEqual(response.json()["undime_confirmado_por"], self.admin.username)
        self.assertTrue(response.json()["undime_confirmado_em"])
        self.assertEqual(response.json()["educador_id"], self.educador.pk)

    def test_relatorio_somente_consulta(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("reports"), {"educador_id": self.educador.pk, "undime_confirmada": "sim"})
        self.assertEqual(response.status_code, 405)
        response = self.client.get(reverse("reports"))
        self.assertNotContains(response, 'id="confirmacaoUndimeModal"')
        self.assertNotContains(response, 'data-bs-target="#confirmacaoUndimeModal"')
        self.educador.refresh_from_db()
        self.assertIsNone(self.educador.undime_confirmado_em)

    def test_botao_nas_inscricoes_e_resultado_apos_avaliar(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertContains(response, "Avaliar vínculo com a Undime")
        self.assertContains(response, 'id="confirmacaoUndimeModal"')
        self.assertNotContains(response, 'name="exportar"')
        self.client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "nao"})
        response = self.client.get(self.url)
        self.assertNotContains(response, "Avaliar vínculo com a Undime")
        self.assertContains(response, "Decisão administrativa — Undime: Não")

    def test_nao_avalia_educador_sem_inscricao_na_atividade(self):
        self.client.force_login(self.admin)
        outro = get_user_model().objects.create_user(username="sem-inscricao-undime")
        outro.educador.representante_estado_undime_consed = True
        outro.educador.save()
        response = self.client.post(self.url, {"educador_id": outro.educador.pk, "undime_confirmada": "sim"})
        self.assertEqual(response.status_code, 404)

    def test_consulta_sem_staff_nao_pode_avaliar(self):
        self.usuario.user_permissions.add(self.permissao)
        self.client.force_login(self.usuario)
        self.assertNotContains(self.client.get(self.url), "Avaliar vínculo com a Undime")
        response = self.client.post(self.url, {"educador_id": self.educador.pk, "undime_confirmada": "sim"})
        self.assertEqual(response.status_code, 403)

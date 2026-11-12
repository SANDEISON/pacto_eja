from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Atividade, ChamadaFrequencia, Frequencia, Inscricao, ProgramacaoSala, Sala, TematicaSala
from core.services.frequencia import registrar, token_inscricao, url_validacao


class FrequenciaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.responsavel = User.objects.create_user(username="responsavel", password="senha")
        self.participante = User.objects.create_user(username="participante", password="senha")
        self.outro = User.objects.create_user(username="outro", password="senha")
        agora = timezone.now()
        self.atividade = Atividade.objects.create(titulo="Evento", descricao="Teste", modalidade="ambas", local="Auditório", data_inicio=agora, data_fim=agora + timedelta(hours=8), inscricoes_fim=agora)
        tematica = TematicaSala.objects.create(nome="Tema")
        self.presencial = ProgramacaoSala.objects.create(sala=Sala.objects.create(nome="Sala 1"), tematica=tematica, data=timezone.localdate(), turno="manha", modalidade="presencial", quantidade_max_participantes=50, responsavel=self.responsavel)
        self.online = ProgramacaoSala.objects.create(sala=Sala.objects.create(nome="Sala virtual"), tematica=tematica, data=timezone.localdate(), hora_inicio=time.min, turno="tarde", modalidade="online", quantidade_max_participantes=50, responsavel=self.responsavel)
        self.atividade.programacoes.add(self.presencial, self.online)
        self.inscricao = Inscricao.objects.create(usuario=self.participante, atividade=self.atividade)
        self.inscricao.programacoes.add(self.presencial)
        self.chamada = ChamadaFrequencia.objects.create(atividade=self.atividade, programacao=self.presencial, responsavel=self.responsavel, expira_em=agora + timedelta(minutes=30))

    def sala_url(self, programacao=None):
        return reverse("frequencia_sala", args=[self.atividade.pk, (programacao or self.presencial).pk])

    def test_cancelar_presenca_restaura_estado_e_permite_nova_confirmacao(self):
        registrar(self.inscricao, self.chamada, self.responsavel, "manual")
        self.client.force_login(self.responsavel)
        self.assertContains(self.client.get(self.sala_url()), "Cancelar presença")
        resposta = self.client.post(self.sala_url(), {"acao": "cancelar", "inscricao": self.inscricao.pk})
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(self.inscricao.frequencias.exists())
        self.assertTrue(ChamadaFrequencia.objects.filter(pk=self.chamada.pk).exists())
        self.assertTrue(self.inscricao.programacoes.filter(pk=self.presencial.pk).exists())
        self.assertContains(self.client.get(self.sala_url()), "Não confirmada")
        self.client.post(self.sala_url(), {"acao": "cancelar", "inscricao": self.inscricao.pk})
        self.client.post(self.sala_url(), {"acao": "manual", "inscricao": self.inscricao.pk})
        self.assertEqual(self.inscricao.frequencias.count(), 1)

    def test_cancelar_presenca_exige_permissao_e_evento_correto(self):
        from core.services.frequencia import cancelar_presenca
        registrar(self.inscricao, self.chamada, self.responsavel, "manual")
        self.client.force_login(self.outro)
        self.assertEqual(self.client.post(self.sala_url(), {"acao": "cancelar", "inscricao": self.inscricao.pk}).status_code, 403)
        with self.assertRaises(ValidationError):
            cancelar_presenca(self.inscricao, self.presencial, self.outro)
        self.client.force_login(self.responsavel)
        self.assertEqual(self.client.post(self.sala_url(self.online), {"acao": "cancelar", "inscricao": self.inscricao.pk}).status_code, 404)
        self.atividade.ativo = False
        self.atividade.save(update_fields=["ativo"])
        self.client.post(self.sala_url(), {"acao": "cancelar", "inscricao": self.inscricao.pk})
        self.assertEqual(self.inscricao.frequencias.count(), 1)

    def test_busca_participantes_por_nome_ou_cpf(self):
        from core.models import Educador

        self.participante.first_name = "Maria"
        self.participante.last_name = "Silva Santos"
        self.participante.save()
        Educador.objects.filter(usuario=self.participante).update(nome_completo="Maria Silva Santos", cpf="52998224725")
        Educador.objects.filter(usuario=self.outro).update(nome_completo="Outra Pessoa", cpf="11144477735")
        self.client.force_login(self.responsavel)
        for busca in ("maria", "Silva Santos", "Maria Silva", "52998224725", "529.982.247-25", "  Maria   Silva  ", "   "):
            with self.subTest(busca=busca):
                resposta = self.client.get(self.sala_url(), {"q": busca})
                self.assertEqual([i.pk for i, _ in resposta.context["participantes"]], [self.inscricao.pk])
        for busca in ("111.444.777-35", "Nome inexistente", "Pessoa 529", "99999999999"):
            with self.subTest(busca=busca):
                resposta = self.client.get(self.sala_url(), {"q": busca})
                self.assertEqual(resposta.context["participantes"], [])

    def test_dashboard_responsavel_acessa_chamada_sem_inscricao_e_com_inscricoes_encerradas(self):
        self.client.force_login(self.responsavel)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.atividade.titulo)
        self.assertContains(response, "Você é responsável pela frequência")
        self.assertContains(response, f'href="{self.sala_url()}"', count=1)
        self.assertContains(response, f'href="{self.sala_url(self.online)}"', count=1)
        self.assertEqual(self.client.get(self.sala_url()).status_code, 200)
        self.presencial.responsavel = self.outro
        self.presencial.save(update_fields=["responsavel"])
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, f'href="{self.sala_url()}"')
        self.assertContains(response, f'href="{self.sala_url(self.online)}"')
        self.client.force_login(self.participante)
        self.assertNotContains(self.client.get(reverse("dashboard")), "Gerenciar frequência")

    def test_dashboard_oculta_botao_de_frequencia_online(self):
        self.client.force_login(self.participante)
        self.inscricao.modalidade = "online"
        self.inscricao.save(update_fields=["modalidade"])
        self.inscricao.programacoes.set([self.online])
        resposta = self.client.get(reverse("dashboard"))
        self.assertContains(resposta, "Acessar salas on-line")
        self.assertNotContains(resposta, "Confirmar presença e acessar evento")

    def test_index_exibe_capacidade_e_saldo_para_responsavel_e_participante(self):
        self.client.force_login(self.responsavel)
        response = self.client.get(reverse("frequencia_index"))
        self.assertContains(response, "<strong>Vagas:</strong> 50 · <strong>Vagas disponíveis:</strong> 49")
        self.assertContains(response, "<strong>Vagas:</strong> 50 · <strong>Vagas disponíveis:</strong> 50")
        for chamada in response.context["chamadas"]:
            programacao = chamada["programacao"]
            self.assertEqual(chamada["inscritos"], int(programacao.pk == self.presencial.pk))
            self.assertEqual(chamada["presencas"], 0)
            with self.assertNumQueries(0):
                self.assertIn(programacao.vagas_disponiveis, (49, 50))
        self.client.force_login(self.participante)
        response = self.client.get(reverse("frequencia_index"))
        self.assertContains(response, "<strong>Vagas:</strong> 50 · <strong>Vagas disponíveis:</strong> 49")

    def test_saldo_por_programacao_inclui_eventos_compartilhados(self):
        outra = Atividade.objects.get(pk=self.atividade.pk)
        outra.pk = None
        outra.save()
        outra.programacoes.add(self.presencial)
        segunda = Inscricao.objects.create(atividade=outra, usuario=self.outro)
        segunda.programacoes.add(self.presencial)
        outro_turno = ProgramacaoSala.objects.create(
            sala=self.presencial.sala, tematica=self.presencial.tematica,
            data=self.presencial.data, turno="tarde", modalidade="presencial",
            responsavel=self.responsavel, quantidade_max_participantes=12,
        )
        self.atividade.programacoes.add(outro_turno)
        self.client.force_login(self.responsavel)
        response = self.client.get(reverse("frequencia_index"))
        self.assertContains(response, "<strong>Vagas:</strong> 50 · <strong>Vagas disponíveis:</strong> 48", count=2)
        self.assertContains(response, "<strong>Vagas:</strong> 12 · <strong>Vagas disponíveis:</strong> 12")
        self.presencial.quantidade_max_participantes = 1
        self.presencial.save(update_fields=("quantidade_max_participantes",))
        response = self.client.get(reverse("frequencia_index"))
        self.assertContains(response, "<strong>Vagas:</strong> 1 · <strong>Vagas disponíveis:</strong> 0", count=2)

    def test_qr_exige_responsavel_e_post_e_nao_duplica(self):
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(url_validacao(self.inscricao)).status_code, 403)
        self.client.force_login(self.participante)
        self.assertEqual(self.client.get(url_validacao(self.inscricao)).status_code, 403)
        self.client.force_login(self.responsavel)
        self.assertContains(self.client.get(url_validacao(self.inscricao)), "Sala 1")
        self.assertEqual(Frequencia.objects.count(), 0)
        for _ in range(2):
            self.assertEqual(self.client.post(url_validacao(self.inscricao), {"programacao": self.presencial.pk}).status_code, 302)
        registro = Frequencia.objects.get()
        self.assertEqual(registro.programacao, self.presencial)
        self.assertEqual(registro.registrada_por, self.responsavel)
        self.assertEqual(registro.metodo, "qr")

    def test_token_legado_estavel_e_adulteracao(self):
        self.assertEqual(token_inscricao(self.inscricao), token_inscricao(Inscricao.objects.get(pk=self.inscricao.pk)))
        self.client.force_login(self.responsavel)
        self.assertEqual(self.client.get(reverse("frequencia_validar", args=[token_inscricao(self.inscricao) + "x"])).status_code, 400)

    def test_servico_rejeita_expiracao_inscricao_errada_e_operador(self):
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, self.chamada, self.outro, "manual")
        self.chamada.expira_em = timezone.now() - timedelta(seconds=1)
        self.chamada.save()
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, self.chamada, self.responsavel, "manual")
        self.chamada.expira_em = timezone.now() + timedelta(minutes=30)
        self.chamada.save()
        self.inscricao.programacoes.clear()
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, self.chamada, self.responsavel, "manual")
        self.assertEqual(Frequencia.objects.count(), 0)

    def test_presenca_separada_por_sala_e_rejeita_chamada_de_outro_evento(self):
        segunda = ProgramacaoSala.objects.create(sala=self.presencial.sala, tematica=self.presencial.tematica, data=self.presencial.data, turno="tarde", modalidade="presencial", responsavel=self.responsavel, quantidade_max_participantes=50)
        self.atividade.programacoes.add(segunda)
        self.inscricao.programacoes.add(segunda)
        chamada = ChamadaFrequencia.objects.create(atividade=self.atividade, programacao=segunda, responsavel=self.responsavel, expira_em=timezone.now() + timedelta(minutes=30))
        registrar(self.inscricao, self.chamada, self.responsavel, "manual")
        registrar(self.inscricao, chamada, self.responsavel, "manual")
        self.assertEqual(self.inscricao.frequencias.count(), 2)
        outro = Atividade.objects.create(titulo="Outro evento", descricao="Teste", data_inicio=timezone.now(), data_fim=timezone.now(), inscricoes_fim=timezone.now())
        chamada.atividade = outro
        chamada.save()
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, chamada, self.responsavel, "manual")

    def test_historico_impede_alteracao_da_identidade_da_programacao(self):
        self.presencial.turno = "tarde"
        with self.assertRaises(ValidationError):
            self.presencial.full_clean()
        self.presencial.refresh_from_db()
        self.presencial.responsavel = self.outro
        self.presencial.full_clean()

    def test_codigo_online_validado_tambem_no_servico(self):
        self.inscricao.modalidade = "online"
        self.inscricao.save()
        self.inscricao.programacoes.set([self.online])
        chamada = ChamadaFrequencia.objects.create(atividade=self.atividade, programacao=self.online, responsavel=self.responsavel, codigo="1234ABCD", expira_em=timezone.now() + timedelta(minutes=30))
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, chamada, self.participante, "online", codigo="ERRADO")
        self.assertEqual(Frequencia.objects.count(), 0)

    def test_painel_e_pdf_sem_qr_inscricao_existente(self):
        self.client.force_login(self.participante)
        pagina = self.client.get(reverse("frequencia_index"))
        self.assertContains(pagina, "Minha participação")
        self.assertNotContains(pagina, "com QR Code")
        response = self.client.get(reverse("inscricao_comprovante", args=[self.atividade.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))

    def test_confirmacao_direta_presencial_e_online_sem_abertura(self):
        ChamadaFrequencia.objects.all().delete()
        self.client.force_login(self.responsavel)
        for programacao in (self.presencial, self.online):
            self.inscricao.modalidade = programacao.modalidade
            self.inscricao.save(update_fields=["modalidade"])
            self.inscricao.programacoes.set([programacao])
            ProgramacaoSala.objects.filter(pk=programacao.pk).update(data=timezone.localdate() - timedelta(days=2))
            pagina = self.client.get(self.sala_url(programacao))
            self.assertContains(pagina, 'value="manual"')
            for texto in ('value="abrir"', 'value="encerrar"', 'name="codigo"', 'name="minutos"'):
                self.assertNotContains(pagina, texto)
            for _ in range(2):
                self.client.post(self.sala_url(programacao), {"acao": "manual", "inscricao": self.inscricao.pk})
            registro = Frequencia.objects.get(programacao=programacao)
            self.assertEqual(registro.registrada_por, self.responsavel)
            self.assertEqual(registro.metodo, "manual")
            self.assertFalse(registro.chamada.codigo)
        self.assertEqual(Frequencia.objects.count(), 2)
        self.assertEqual(ChamadaFrequencia.objects.count(), 2)

    def test_online_sem_codigo_e_sem_abertura(self):
        ChamadaFrequencia.objects.all().delete()
        self.inscricao.modalidade = "online"
        self.inscricao.save(update_fields=["modalidade"])
        self.inscricao.programacoes.set([self.online])
        url = reverse("frequencia_online", args=[self.atividade.pk, self.online.pk])
        self.client.force_login(self.outro)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.participante)
        self.assertNotContains(self.client.get(url), 'name="codigo"')
        self.assertFalse(ChamadaFrequencia.objects.exists())
        for _ in range(2):
            resposta = self.client.post(url)
            self.assertContains(resposta, "Inscrição confirmada.")
            self.assertContains(resposta, "O link de acesso on-line ainda não foi cadastrado.")
        registro = Frequencia.objects.get()
        self.assertEqual(registro.metodo, "online")
        self.assertEqual(registro.registrada_por, self.participante)
        self.assertEqual(ChamadaFrequencia.objects.count(), 1)
        self.assertFalse(registro.chamada.codigo)

    def test_salas_online_mostram_participacao_e_ocultam_link_do_canal(self):
        self.inscricao.modalidade = "online"
        self.inscricao.save(update_fields=["modalidade"])
        self.inscricao.programacoes.set([self.online])
        sala_publica = ProgramacaoSala.objects.create(
            sala=Sala.objects.create(nome="Sala da transmissão pública"),
            tematica=self.online.tematica,
            data=self.online.data,
            hora_inicio=self.online.hora_inicio,
            turno=self.online.turno,
            modalidade="online",
            publica=True,
            quantidade_max_participantes=50,
            link="https://example.com/transmissao",
        )
        self.atividade.programacoes.add(sala_publica)
        pagina_url = reverse("atividade_salas_online_publicas", args=[self.atividade.pk])
        confirmar_url = reverse("frequencia_online", args=[self.atividade.pk, self.online.pk])

        self.client.force_login(self.participante)
        resposta = self.client.get(pagina_url)
        self.assertContains(resposta, f'action="{confirmar_url}"')
        self.assertContains(resposta, "Confirmar presença e acessar evento")
        self.assertContains(resposta, sala_publica.sala.nome)
        acesso_url = reverse("atividade_acessar_sala_online_publica", args=[self.atividade.pk, sala_publica.pk])
        self.assertContains(resposta, f'action="{acesso_url}" target="_blank" rel="noopener"')
        html = resposta.content.decode()
        self.assertLess(html.index("Minha participação"), html.index("Programação pública"))

        sala_publica.link = "https://www.youtube.com/@C%C3%81TEDRAUNESCODEEJA"
        sala_publica.save(update_fields=["link"])
        resposta = self.client.get(pagina_url)
        self.assertContains(resposta, sala_publica.sala.nome)
        self.assertNotContains(resposta, acesso_url)
        self.assertEqual(self.client.post(acesso_url).status_code, 404)

        self.client.post(confirmar_url)
        self.assertContains(self.client.get(pagina_url), "Acessar evento on-line")

        self.client.force_login(self.responsavel)
        resposta = self.client.get(pagina_url)
        self.assertNotContains(resposta, "Minha participação")
        self.assertNotContains(resposta, confirmar_url)

        self.inscricao.modalidade = "presencial"
        self.inscricao.save(update_fields=["modalidade"])
        self.inscricao.programacoes.set([self.presencial])
        self.client.force_login(self.participante)
        resposta = self.client.get(pagina_url)
        self.assertNotContains(resposta, "Minha participação")
        self.assertNotContains(resposta, confirmar_url)

    def test_salas_online_liberam_acesso_no_inicio_da_programacao(self):
        inicio = timezone.localtime(timezone.now()).replace(second=0, microsecond=0)
        self.online.data = inicio.date()
        self.online.hora_inicio = inicio.time()
        self.online.hora_fim = time(23, 59)
        self.online.publica = True
        self.online.link = "https://example.com/sala"
        self.online.save()
        self.inscricao.modalidade = "online"
        self.inscricao.save(update_fields=["modalidade"])
        self.inscricao.programacoes.set([self.online])
        self.client.force_login(self.participante)
        args = [self.atividade.pk, self.online.pk]
        pagina = reverse("atividade_salas_online_publicas", args=args[:1])
        acesso = reverse("atividade_acessar_sala_online_publica", args=args)
        confirmar = reverse("frequencia_online", args=args)

        with patch("django.utils.timezone.now", return_value=inicio - timedelta(seconds=1)):
            resposta = self.client.get(pagina)
            self.assertContains(resposta, 'type="button" disabled')
            self.assertContains(resposta, inicio.strftime("%d/%m/%Y"))
            self.assertContains(resposta, inicio.strftime("%H:%M"))
            self.assertContains(resposta, "23:59")
            self.assertNotContains(resposta, acesso)
            self.assertNotContains(resposta, confirmar)
            self.assertEqual(self.client.post(acesso).status_code, 404)
            self.assertEqual(self.client.post(confirmar).status_code, 403)
            self.assertFalse(self.inscricao.frequencias.exists())

        with patch("django.utils.timezone.now", return_value=inicio):
            self.assertContains(self.client.get(pagina), f'action="{acesso}"')
        self.assertRedirects(self.client.post(acesso), self.online.link, fetch_redirect_response=False)

    def test_acesso_publico_cria_ou_reutiliza_inscricao_e_registra_presenca_uma_vez(self):
        self.online.publica = True
        self.online.link = "https://example.com/sala"
        self.online.save(update_fields=["publica", "link"])
        args = [self.atividade.pk, self.online.pk]
        url = reverse("atividade_acessar_sala_online_publica", args=args)
        pagina = reverse("atividade_salas_online_publicas", args=args[:1])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(Inscricao.objects.count(), 1)
        Inscricao.objects.create(atividade=self.atividade, usuario=self.responsavel, modalidade="online")

        for usuario, modalidade in (
            (self.outro, "online"), (self.participante, "presencial"), (self.responsavel, "online"),
        ):
            with self.subTest(modalidade=modalidade):
                self.client.force_login(usuario)
                self.assertContains(self.client.get(pagina), f'action="{url}"')
                self.assertEqual(self.client.get(url).status_code, 405)
                self.assertFalse(Frequencia.objects.filter(inscricao__usuario=usuario).exists())
                for _ in range(2):
                    self.assertRedirects(self.client.post(url), self.online.link, fetch_redirect_response=False)
                inscricao = Inscricao.objects.get(atividade=self.atividade, usuario=usuario)
                self.assertEqual(inscricao.modalidade, modalidade)
                self.assertTrue(inscricao.programacoes.filter(pk=self.online.pk).exists())
                self.assertEqual(inscricao.frequencias.filter(programacao=self.online, metodo="online").count(), 1)
                resposta = self.client.get(pagina)
                self.assertContains(resposta, "Minha participação")
                self.assertContains(resposta, "Presença registrada")

        self.assertTrue(self.inscricao.programacoes.filter(pk=self.presencial.pk).exists())
        self.client.force_login(self.responsavel)
        chamada = self.client.get(self.sala_url(self.online))
        self.assertEqual(len(chamada.context["participantes"]), 3)
        self.assertContains(chamada, "Registros de frequência (3)")

    def test_acesso_publico_aceita_post_https_com_csrf_e_referer_da_programacao(self):
        self.online.publica = True
        self.online.link = "https://example.com/sala"
        self.online.save(update_fields=["publica", "link"])
        pagina = reverse("atividade_salas_online_publicas", args=[self.atividade.pk])
        acesso = reverse("atividade_acessar_sala_online_publica", args=[self.atividade.pk, self.online.pk])
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.outro)
        resposta = cliente.get(pagina, secure=True)
        referer = resposta.wsgi_request.build_absolute_uri()
        dados = {"csrfmiddlewaretoken": cliente.cookies["csrftoken"].value}

        self.assertEqual(cliente.post(acesso, dados, secure=True).status_code, 403)
        self.assertFalse(Inscricao.objects.filter(usuario=self.outro).exists())
        resposta = cliente.post(acesso, dados, secure=True, HTTP_REFERER=referer)
        self.assertRedirects(resposta, self.online.link, fetch_redirect_response=False)
        self.assertTrue(Frequencia.objects.filter(inscricao__usuario=self.outro, programacao=self.online).exists())

    def test_acesso_publico_rejeita_sala_privada_ou_sem_link(self):
        self.client.force_login(self.outro)
        url = reverse("atividade_acessar_sala_online_publica", args=[self.atividade.pk, self.online.pk])
        self.online.link = "https://example.com/sala"
        self.online.save(update_fields=["link"])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.online.publica = True
        self.online.link = ""
        self.online.save(update_fields=["publica", "link"])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertFalse(Inscricao.objects.filter(usuario=self.outro).exists())

    def test_acesso_online_prioriza_link_da_programacao_e_atualiza_botao(self):
        self.inscricao.modalidade = "online"
        self.inscricao.save(update_fields=["modalidade"])
        self.inscricao.programacoes.set([self.online])
        self.atividade.link = "https://example.com/evento"
        self.atividade.save(update_fields=["link"])
        self.client.force_login(self.participante)
        url = reverse("frequencia_online", args=[self.atividade.pk, self.online.pk])
        self.assertContains(self.client.get(reverse("frequencia_index")), "Confirmar presença e acessar evento")
        self.assertFalse(Frequencia.objects.exists())
        resposta = self.client.post(url)
        self.assertEqual(resposta.context["link_evento"], self.atividade.link)
        self.assertContains(resposta, "window.location.replace")
        self.online.link = "https://example.com/sala"
        self.online.save(update_fields=["link"])
        resposta = self.client.post(url)
        self.assertEqual(resposta.context["link_evento"], self.online.link)
        self.assertEqual(Frequencia.objects.filter(inscricao=self.inscricao, programacao=self.online).count(), 1)
        pagina = self.client.get(reverse("frequencia_index"))
        self.assertContains(pagina, "Acessar evento on-line")
        self.assertNotContains(pagina, "Confirmar presença e acessar evento")

    def test_registro_direto_exige_permissao_evento_ativo_e_inscricao_correta(self):
        from core.services.frequencia import registrar_direto
        ChamadaFrequencia.objects.all().delete()
        for usuario, programacao, metodo in (
            (self.outro, self.presencial, "manual"),
            (self.participante, self.presencial, "qr"),
            (self.responsavel, self.online, "manual"),
        ):
            with self.assertRaises(ValidationError):
                registrar_direto(self.inscricao, programacao, usuario, metodo)
        self.atividade.ativo = False
        self.atividade.save(update_fields=["ativo"])
        with self.assertRaises(ValidationError):
            registrar_direto(self.inscricao, self.presencial, self.responsavel, "manual")
        self.assertFalse(Frequencia.objects.exists())
        self.assertFalse(ChamadaFrequencia.objects.exists())

    def test_qr_sem_abertura_previa(self):
        ChamadaFrequencia.objects.all().delete()
        self.client.force_login(self.responsavel)
        url = url_validacao(self.inscricao)
        self.assertContains(self.client.get(url), "Sala 1")
        self.assertFalse(ChamadaFrequencia.objects.exists())
        self.client.post(url, {"programacao": self.presencial.pk})
        self.assertEqual(Frequencia.objects.get().metodo, "qr")

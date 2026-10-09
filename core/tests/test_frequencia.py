from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
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
        self.online = ProgramacaoSala.objects.create(sala=Sala.objects.create(nome="Sala virtual"), tematica=tematica, data=timezone.localdate(), turno="tarde", modalidade="online", quantidade_max_participantes=50, responsavel=self.responsavel)
        self.atividade.programacoes.add(self.presencial, self.online)
        self.inscricao = Inscricao.objects.create(usuario=self.participante, atividade=self.atividade)
        self.inscricao.programacoes.add(self.presencial)
        self.chamada = ChamadaFrequencia.objects.create(atividade=self.atividade, programacao=self.presencial, responsavel=self.responsavel, expira_em=agora + timedelta(minutes=30))

    def sala_url(self, programacao=None):
        return reverse("frequencia_sala", args=[self.atividade.pk, (programacao or self.presencial).pk])

    def test_qr_exige_responsavel_e_post_e_nao_duplica(self):
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(url_validacao(self.inscricao)).status_code, 403)
        self.client.force_login(self.participante)
        self.assertEqual(self.client.get(url_validacao(self.inscricao)).status_code, 403)
        self.client.force_login(self.responsavel)
        self.assertContains(self.client.get(url_validacao(self.inscricao)), "Sala 1")
        self.assertEqual(Frequencia.objects.count(), 0)
        for _ in range(2):
            self.assertEqual(self.client.post(url_validacao(self.inscricao), {"chamada": self.chamada.pk}).status_code, 302)
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

    def test_chamada_permissao_data_e_manual(self):
        self.client.force_login(self.outro)
        self.assertEqual(self.client.post(self.sala_url(), {"acao": "abrir"}).status_code, 403)
        self.client.force_login(self.responsavel)
        self.assertContains(self.client.get(self.sala_url()), "Chamada aberta")
        self.client.post(self.sala_url(), {"acao": "manual", "chamada": self.chamada.pk, "inscricao": self.inscricao.pk})
        self.assertEqual(Frequencia.objects.get().metodo, "manual")
        self.presencial.data = timezone.localdate() + timedelta(days=1)
        self.presencial.save()
        self.client.post(self.sala_url(), {"acao": "abrir"})
        self.assertEqual(ChamadaFrequencia.objects.count(), 1)

    def test_codigo_online_expira_e_nao_aceita_outra_sala(self):
        self.inscricao.modalidade = "online"
        self.inscricao.save()
        self.inscricao.programacoes.set([self.online])
        self.client.force_login(self.responsavel)
        self.client.post(self.sala_url(self.online), {"acao": "abrir", "minutos": "5"})
        chamada = ChamadaFrequencia.objects.get(programacao=self.online)
        self.assertTrue(chamada.codigo)
        url = reverse("frequencia_online", args=[self.atividade.pk, self.online.pk])
        self.client.force_login(self.outro)
        self.assertEqual(self.client.post(url, {"codigo": chamada.codigo}).status_code, 404)
        self.client.force_login(self.participante)
        self.assertContains(self.client.post(url, {"codigo": "ERRADO"}), "Código inválido")
        self.assertEqual(Frequencia.objects.count(), 0)
        self.client.post(url, {"codigo": chamada.codigo.lower()})
        self.client.post(url, {"codigo": chamada.codigo})
        self.assertEqual(Frequencia.objects.count(), 1)
        self.assertEqual(Frequencia.objects.get().metodo, "online")
        chamada.expira_em = timezone.now() - timedelta(seconds=1)
        chamada.save()
        self.assertContains(self.client.post(url, {"codigo": chamada.codigo}), "Código inválido")

    def test_renovacao_invalida_chamada_anterior(self):
        self.client.force_login(self.responsavel)
        self.client.post(self.sala_url(), {"acao": "abrir", "minutos": "5"})
        self.chamada.refresh_from_db()
        self.assertIsNotNone(self.chamada.encerrada_em)
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, self.chamada, self.responsavel, "qr")

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

    def test_chamada_encerrada_nao_registra_e_get_nao_abre_chamada(self):
        self.client.force_login(self.responsavel)
        self.client.get(self.sala_url(), {"acao": "abrir"})
        self.assertEqual(ChamadaFrequencia.objects.count(), 1)
        self.client.post(self.sala_url(), {"acao": "encerrar", "chamada": self.chamada.pk})
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, self.chamada, self.responsavel, "manual")

    def test_codigo_online_validado_tambem_no_servico(self):
        self.inscricao.modalidade = "online"
        self.inscricao.save()
        self.inscricao.programacoes.set([self.online])
        chamada = ChamadaFrequencia.objects.create(atividade=self.atividade, programacao=self.online, responsavel=self.responsavel, codigo="1234ABCD", expira_em=timezone.now() + timedelta(minutes=30))
        with self.assertRaises(ValidationError):
            registrar(self.inscricao, chamada, self.participante, "online", codigo="ERRADO")
        self.assertEqual(Frequencia.objects.count(), 0)

    def test_painel_e_pdf_com_qr_inscricao_existente(self):
        from unittest.mock import patch
        from core.services.comprovante_inscricao import QrCodeWidget
        self.client.force_login(self.participante)
        self.assertContains(self.client.get(reverse("frequencia_index")), "Minha participação")
        with patch("core.services.comprovante_inscricao.QrCodeWidget", wraps=QrCodeWidget) as qr:
            response = self.client.get(reverse("inscricao_comprovante", args=[self.atividade.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))
        self.assertEqual(qr.call_args.args[0], "http://testserver" + url_validacao(self.inscricao))

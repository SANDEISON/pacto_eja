import csv
import io
from datetime import timedelta
from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Atividade, Cidade, EducadorGenero, Endereco, Inscricao, Refeicao, ProgramacaoSala, Sala, TematicaSala


class InscricaoRelatoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username="gestor-filtros")
        cls.admin.user_permissions.add(Permission.objects.get(content_type__app_label="core", codename="view_inscricao"))
        agora = timezone.now()
        dados = dict(data_inicio=agora + timedelta(days=10), data_fim=agora + timedelta(days=11), inscricoes_fim=agora, vagas=100)
        cls.atividade = Atividade.objects.create(titulo="Evento filtrado", modalidade="ambas", **dados)
        cls.outra = Atividade.objects.create(titulo="Outro evento", **dados)
        cls.maria = User.objects.create_user(username="maria-filtros", first_name="Maria", email="maria@example.com")
        cls.joao = User.objects.create_user(username="joao-filtros", first_name="João")
        cls.maria.educador.representante_estado_undime_consed = True
        cls.maria.educador.undime_confirmada = True
        cls.maria.educador.telefone = "82988887777"
        cls.maria.educador.save()
        cls.inscricao = Inscricao.objects.create(atividade=cls.atividade, usuario=cls.maria)
        Inscricao.objects.create(atividade=cls.atividade, usuario=cls.joao, modalidade="online")
        Inscricao.objects.create(atividade=cls.outra, usuario=cls.admin)
        data = timezone.localtime(cls.atividade.data_inicio).date()
        cls.refeicao = Refeicao.objects.create(atividade=cls.atividade, tipo="almoco", data=data, horario=time(12))
        cls.inscricao.refeicoes.add(cls.refeicao)
        cls.programacao = ProgramacaoSala.objects.create(
            sala=Sala.objects.create(nome="Sala dos filtros"),
            tematica=TematicaSala.objects.create(nome="Educação"),
            data=data, turno="manha", modalidade="presencial", quantidade_max_participantes=50,
        )
        cls.atividade.programacoes.add(cls.programacao)
        cls.inscricao.programacoes.add(cls.programacao)

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("atividade_inscricoes", args=[self.atividade.pk])

    def csv(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))

    def test_filtros_combinados_e_busca_telefone(self):
        response = self.client.get(self.url, {
            "modalidade": "presencial", "representante": "Sim", "undime": "sim",
            "q": "82988887777", "programacao": self.programacao.pk,
            "refeicao": self.refeicao.pk, "data": self.programacao.data.isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["inscricoes"]), [self.inscricao])
        self.assertNotContains(response, 'name="exportar"')

    def test_csv_mesmos_filtros_e_somente_atividade_atual(self):
        rows = self.csv(exportar="participantes", modalidade="presencial")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "Maria")
        self.assertIn("Evento filtrado", rows[1])
        self.assertIn(str(self.refeicao), rows[1])
        self.assertIn("maria@example.com", rows[1])

    def test_resumo_agrupado_usa_filtros(self):
        rows = self.csv(exportar="resumo", dimensao="modalidade_inscrito_atual")
        self.assertEqual(rows[0], ["Modalidade do inscrito", "Quantidade", "Percentual"])
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row[1:] == ["1", "50.00%"] for row in rows[1:]))
        rows = self.csv(exportar="resumo", dimensao="modalidade_inscrito_atual", undime="sim")
        self.assertEqual(rows[1], ["Presencial", "1", "100.00%"])

    def test_apresentacao_filtra_por_inscricao_da_atividade_e_exporta(self):
        self.inscricao.vai_apresentar_trabalho = True
        self.inscricao.save(update_fields=["vai_apresentar_trabalho"])
        Inscricao.objects.create(atividade=self.outra, usuario=self.joao, vai_apresentar_trabalho=True)
        response = self.client.get(self.url, {"apresentacao": "sim"})
        self.assertEqual(list(response.context["inscricoes"]), [self.inscricao])
        self.assertContains(response, 'name="apresentacao"')
        response = self.client.get(self.url, {"apresentacao": "nao"})
        self.assertEqual(list(response.context["inscricoes"].values_list("usuario_id", flat=True)), [self.joao.pk])
        self.assertEqual(len(self.csv(exportar="participantes", apresentacao="sim")), 2)
        self.assertEqual(len(self.csv(exportar="participantes")), 3)

    def test_relatorio_exibe_coluna_e_status_da_atividade_selecionada(self):
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.inscricao.vai_apresentar_trabalho = True
        self.inscricao.save(update_fields=["vai_apresentar_trabalho"])
        Inscricao.objects.create(atividade=self.outra, usuario=self.maria, vai_apresentar_trabalho=False)
        response = self.client.get(reverse("reports"), {"atividade": self.atividade.pk})
        self.assertContains(response, "<th>Refeições</th>\n              <th>Apresentação de trabalho</th>", html=True)
        self.assertContains(response, 'id="filterApresentacao"')
        registro = next(r for r in response.context["participantes_detalhados"] if r["email"] == "maria@example.com")
        estados = {a["id"]: a["vai_apresentar_trabalho"] for a in registro["atividades"]}
        self.assertIs(estados[self.atividade.pk], True)
        self.assertIs(estados[self.outra.pk], False)

    def test_filtros_estado_municipio_genero_e_pendencia(self):
        cidade = Cidade.objects.select_related("estado").first()
        genero = EducadorGenero.objects.create(nome="Gênero dos filtros")
        self.maria.educador.genero = genero
        self.maria.educador.save()
        Endereco.objects.create(educador=self.maria.educador, cidade=cidade)
        response = self.client.get(self.url, {
            "estado": cidade.estado.nome_estado, "municipio": cidade.nome_cidade,
            "genero": genero.nome,
        })
        self.assertEqual(list(response.context["inscricoes"]), [self.inscricao])
        response = self.client.get(self.url, {"undime": "pendente"})
        self.assertEqual(list(response.context["inscricoes"].values_list("usuario_id", flat=True)), [self.joao.pk])

    def test_exporta_todas_paginas_e_preserva_filtros(self):
        for indice in range(22):
            user = get_user_model().objects.create_user(username=f"inscrito-{indice}")
            Inscricao.objects.create(atividade=self.atividade, usuario=user)
        response = self.client.get(self.url, {"modalidade": "presencial"})
        self.assertTrue(response.context["is_paginated"])
        self.assertContains(response, "modalidade=presencial&amp;page=2")
        self.assertEqual(len(self.csv(exportar="participantes", modalidade="presencial", page=2)), 24)

    def test_permissao_filtros_invalidos_e_csv_seguro(self):
        response = self.client.get(self.url, {"refeicao": "999999"})
        self.assertTrue(response.context["filtros_form"].errors)
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.maria.educador.nome_completo = "=1+1"
        self.maria.educador.save()
        rows = self.csv(exportar="participantes", modalidade="presencial")
        self.assertEqual(rows[1][0], "'=1+1")
        self.client.force_login(self.joao)
        self.assertEqual(self.client.get(self.url, {"exportar": "participantes"}).status_code, 403)

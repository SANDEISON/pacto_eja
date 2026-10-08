from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import (
    Cidade,
    CorRaca,
    CursoCertificado,
    Educador,
    EducadorEscola,
    EducadorGenero,
    Endereco,
    Escola,
    Estado,
    Funcao,
    FuncaoCaracterizacaoTurma,
    FuncaoEducador,
)


class ReportsCertificadosViewTests(TestCase):
    """Garante segurança de acesso, integridade dos cálculos e serialização no relatório de certificados."""

    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username="11111111111",
            password="SenhaForte2026!",
            is_staff=True,
            first_name="Admin",
            email="admin@pactoeja.gov.br",
        )

        self.common_user = get_user_model().objects.create_user(
            username="22222222222",
            password="SenhaForte2026!",
            is_staff=False,
            first_name="Comum",
            email="comum@pactoeja.gov.br",
        )

        # Cursos para certificado
        self.curso_alfabetizacao, _ = CursoCertificado.objects.get_or_create(
            nome="Alfabetização de Jovens e Adultos - 80h"
        )
        self.curso_formadores, _ = CursoCertificado.objects.get_or_create(
            nome="Formação em Serviço para Formadores - 360h"
        )

        # Gênero e Cor/Raça
        self.genero_fem, _ = EducadorGenero.objects.get_or_create(nome="Feminino")
        self.cor_parda, _ = CorRaca.objects.get_or_create(nome="Parda")

        # Estado e Cidades
        self.estado_pb, _ = Estado.objects.get_or_create(sigla="PB", defaults={"nome_estado": "Paraíba"})
        self.cidade_jp, _ = Cidade.objects.get_or_create(
            codigo_ibge=2507507,
            defaults={"nome_cidade": "João Pessoa", "estado": self.estado_pb}
        )
        self.cidade_cg, _ = Cidade.objects.get_or_create(
            codigo_ibge=2504009,
            defaults={"nome_cidade": "Campina Grande", "estado": self.estado_pb}
        )

        # Escola, Função e Caracterização
        self.escola_1, _ = Escola.objects.get_or_create(
            id_escola=25000001,
            defaults={
                "nome": "Escola Municipal Paulo Freire",
                "id_municipio": 2507507,
                "sigla_uf": "PB",
            }
        )
        self.funcao_prof, _ = Funcao.objects.get_or_create(nome="Professor(a)")
        self.carac_turma, _ = FuncaoCaracterizacaoTurma.objects.get_or_create(nome="Turma Regular")

        # Educador 1 (com cursos e vínculo)
        self.user_educador_1 = get_user_model().objects.create_user(
            username="33333333333",
            password="SenhaForte2026!",
            first_name="Ana",
            last_name="Silva",
            email="ana@exemplo.com",
        )
        self.educador_1 = self.user_educador_1.educador
        self.educador_1.nome_completo = "Ana Silva"
        self.educador_1.cpf = "33333333333"
        self.educador_1.telefone = "(83) 98888-1111"
        self.educador_1.data_nascimento = date(1985, 5, 20)
        self.educador_1.genero = self.genero_fem
        self.educador_1.cor_raca = self.cor_parda
        self.educador_1.save()
        self.educador_1.cursos_certificados.add(self.curso_alfabetizacao, self.curso_formadores)

        Endereco.objects.create(
            educador=self.educador_1,
            cep="58000000",
            logradouro="Rua das Acácias",
            numero="123",
            bairro="Centro",
            cidade=self.cidade_jp,
        )

        vinculo_1 = EducadorEscola.objects.create(
            cidade=self.cidade_jp,
            escola=self.escola_1,
            funcao=self.funcao_prof,
            funcao_caracterizacao_turmas=self.carac_turma,
            tempo_atuacao="4_6_anos",
        )
        FuncaoEducador.objects.create(
            educador=self.educador_1,
            educador_escola=vinculo_1,
        )

    def test_acesso_negado_para_usuario_nao_autenticado_ou_sem_staff(self):
        # Usuário anônimo
        res_anonimo = self.client.get(reverse("reports_certificados"))
        self.assertEqual(res_anonimo.status_code, 302)
        self.assertIn("conta/entrar/", res_anonimo.url)

        # Usuário comum (sem is_staff)
        self.client.force_login(self.common_user)
        res_comum = self.client.get(reverse("reports_certificados"))
        self.assertEqual(res_comum.status_code, 302)
        self.assertIn("conta/entrar/", res_comum.url)

    def test_acesso_permitido_para_equipe_staff_com_contexto_valido(self):
        self.client.force_login(self.staff_user)
        res = self.client.get(reverse("reports_certificados"))

        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "reports_certificados.html")

        ctx = res.context
        self.assertEqual(ctx["total_solicitantes"], 1)
        self.assertEqual(ctx["total_certificados_pedidos"], 2)
        self.assertEqual(ctx["total_municipios_atuacao"], 1)
        self.assertEqual(ctx["total_municipios_residencia"], 1)
        self.assertEqual(ctx["total_escolas"], 1)
        self.assertEqual(ctx["total_vinculos"], 1)

        # Validação da lista de participantes detalhados
        participantes = ctx["participantes_detalhados"]
        self.assertEqual(len(participantes), 1)
        p = participantes[0]
        self.assertEqual(p["nome"], "Ana Silva")
        self.assertEqual(p["cpf"], "33333333333")
        self.assertEqual(p["email"], "ana@exemplo.com")
        self.assertEqual(p["municipio_residencia"], "João Pessoa")
        self.assertEqual(p["escola"], "Escola Municipal Paulo Freire")
        self.assertEqual(p["funcao"], "Professor(a)")
        self.assertEqual(p["tempo"], "4 a 6 anos")
        self.assertEqual(len(p["cursos_certificados"]), 2)

    def test_filtro_por_curso_especifico(self):
        self.client.force_login(self.staff_user)

        # Educador 2 que só pediu Formadores
        user_2 = get_user_model().objects.create_user(
            username="44444444444",
            password="SenhaForte2026!",
            first_name="Carlos",
        )
        ed_2 = user_2.educador
        ed_2.nome_completo = "Carlos Alberto"
        ed_2.cpf = "44444444444"
        ed_2.save()
        ed_2.cursos_certificados.add(self.curso_formadores)

        # Requisição filtrando apenas curso de alfabetização
        url = f"{reverse('reports_certificados')}?curso={self.curso_alfabetizacao.id}"
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["total_solicitantes"], 1)
        self.assertEqual(res.context["curso_selecionado"]["id"], self.curso_alfabetizacao.id)
        self.assertEqual(res.context["participantes_detalhados"][0]["nome"], "Ana Silva")

    def test_educador_com_multiplos_vinculos_agrega_dados_e_nao_duplica_linhas(self):
        self.client.force_login(self.staff_user)

        # Adicionar segundo vínculo para Ana Silva em outra escola e outra função
        escola_2, _ = Escola.objects.get_or_create(
            id_escola=25000002,
            defaults={
                "nome": "Escola Estadual Castro Alves",
                "id_municipio": 2507507,
                "sigla_uf": "PB",
            }
        )
        funcao_coord, _ = Funcao.objects.get_or_create(codigo="coordenador", defaults={"nome": "Coordenador(a)"})
        vinculo_2 = EducadorEscola.objects.create(
            cidade=self.cidade_jp,
            escola=escola_2,
            funcao=funcao_coord,
            funcao_caracterizacao_turmas=self.carac_turma,
            tempo_atuacao="mais_6_anos",
        )
        FuncaoEducador.objects.create(
            educador=self.educador_1,
            educador_escola=vinculo_2,
        )

        # 1. Testar resposta da tela inicial / contexto
        res = self.client.get(reverse("reports_certificados"))
        self.assertEqual(res.status_code, 200)
        participantes = [p for p in res.context["participantes_detalhados"] if p["nome"] == "Ana Silva"]
        self.assertEqual(len(participantes), 1, "Não deve duplicar linhas para o mesmo educador na tela")
        p = participantes[0]
        self.assertIn("Escola Municipal Paulo Freire", p["escola"])
        self.assertIn("Escola Estadual Castro Alves", p["escola"])
        self.assertIn("Professor(a)", p["funcao"])
        self.assertIn("Coordenador(a)", p["funcao"])
        self.assertIn("4 a 6 anos", p["tempo"])
        self.assertIn("Mais de 6 anos", p["tempo"])

        # 2. Testar API AJAX de paginação
        res_api = self.client.get(reverse("reports_certificados_participantes"))
        self.assertEqual(res_api.status_code, 200)
        data = res_api.json()
        participantes_api = [p for p in data["participants"] if p["nome"] == "Ana Silva"]
        self.assertEqual(len(participantes_api), 1, "Não deve duplicar linhas na API paginada")

        # 3. Testar exportação CSV
        res_csv = self.client.get(reverse("reports_certificados_export_csv"))
        self.assertEqual(res_csv.status_code, 200)
        content = res_csv.streaming_content
        full_csv = "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in content)
        linhas_ana = [line for line in full_csv.splitlines() if "Ana Silva" in line]
        self.assertEqual(len(linhas_ana), 1, "Deve exportar exatamente 1 linha por educador no CSV de certificados")
        self.assertIn("Escola Municipal Paulo Freire", linhas_ana[0])
        self.assertIn("Escola Estadual Castro Alves", linhas_ana[0])
        self.assertIn("Professor(a)", linhas_ana[0])
        self.assertIn("Coordenador(a)", linhas_ana[0])


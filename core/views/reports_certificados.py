from collections import Counter
from datetime import date

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.models import (
    CursoCertificado,
    Educador,
    EducadorEscola,
    Endereco,
    FuncaoEducador,
)


ROTULOS_TEMPO_ATUACAO = {
    "0_3_anos": "0 a 3 anos",
    "4_6_anos": "4 a 6 anos",
    "mais_6_anos": "Mais de 6 anos",
}


def usuario_e_staff(usuario):
    """Restringe os relatórios a usuários autenticados da equipe administrativa."""
    return bool(usuario and usuario.is_authenticated and usuario.is_staff)


staff_required = user_passes_test(usuario_e_staff)


def calcular_idade(data_nascimento):
    """Calcula a idade em anos completos a partir da data de nascimento."""
    if not data_nascimento:
        return None
    hoje = timezone.now().date()
    return hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))


def obter_faixa_etaria(idade):
    """Classifica a idade em faixas estatísticas."""
    if idade is None:
        return "Não informada"
    if idade < 25:
        return "Menos de 25 anos"
    if idade <= 34:
        return "25 a 34 anos"
    if idade <= 44:
        return "35 a 44 anos"
    if idade <= 54:
        return "45 a 54 anos"
    return "55 anos ou mais"


def normalizar_distribuicao(registros, campo_rotulo, rotulos=None, campos_extras=None):
    """Converte agregações do ORM em formato uniforme para gráficos e tabelas."""
    rotulos = rotulos or {}
    campos_extras = campos_extras or {}
    distribuicao = []

    for registro in registros:
        valor_original = registro.get(campo_rotulo)
        rotulo = rotulos.get(
            valor_original,
            str(valor_original) if valor_original else "Não informado",
        )
        item = {"label": rotulo, "qtd": registro["qtd"]}
        for campo_origem, campo_destino in campos_extras.items():
            item[campo_destino] = registro.get(campo_origem) or ""
        distribuicao.append(item)

    return distribuicao


@method_decorator(staff_required, name="dispatch")
class ReportsCertificadosView(TemplateView):
    """Painel analítico e relatórios dos educadores solicitantes de certificados."""

    template_name = "reports_certificados.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Catálogo de cursos para certificado com contagem total
        todos_cursos = list(CursoCertificado.objects.all().order_by("nome"))
        cursos_catalogo = []
        for curso in todos_cursos:
            total_solic = curso.educadores_solicitantes.distinct().count()
            cursos_catalogo.append({
                "id": curso.id,
                "nome": curso.nome,
                "total_solicitantes": total_solic,
            })

        # 2. Filtragem opcional por curso selecionado via query param (?curso=<id>)
        curso_id_param = self.request.GET.get("curso")
        curso_selecionado = None
        if curso_id_param:
            try:
                curso_id = int(curso_id_param)
                curso_selecionado = next((c for c in cursos_catalogo if c["id"] == curso_id), None)
            except (ValueError, TypeError):
                curso_selecionado = None

        # Base de educadores que preencheram o formulário de certificado
        # (possuem cursos selecionados ou funções/atuações cadastradas)
        educadores_base = Educador.objects.filter(
            Q(cursos_certificados__isnull=False) | Q(funcoes__isnull=False)
        ).distinct()

        if curso_selecionado:
            educadores_base = educadores_base.filter(cursos_certificados__id=curso_selecionado["id"])

        educadores_qs = educadores_base.select_related(
            "usuario", "genero", "cor_raca", "endereco__cidade__estado"
        ).prefetch_related(
            "cursos_certificados",
            "funcoes__educador_escola__cidade__estado",
            "funcoes__educador_escola__escola",
            "funcoes__educador_escola__funcao",
            "funcoes__educador_escola__funcao_caracterizacao_turmas",
        )

        # 3. Construção detalhada dos participantes e linhas da tabela
        participantes_detalhados = []
        contagem_faixas_etarias = Counter()
        municipios_residencia_set = set()
        municipios_atuacao_set = set()
        escolas_set = set()
        estados_atuacao_counter = Counter()
        estados_atuacao_siglas = {}
        municipios_atuacao_counter = Counter()
        municipios_atuacao_estados = {}

        municipios_residencia_counter = Counter()
        municipios_residencia_estados = {}
        estados_residencia_counter = Counter()
        estados_residencia_siglas = {}

        funcoes_counter = Counter()
        caracterizacoes_counter = Counter()
        tempo_counter = Counter()
        total_certificados_pedidos = 0

        for educador in educadores_qs:
            usuario = educador.usuario
            nome = (
                educador.nome_completo
                or (usuario.get_full_name() if usuario else "")
                or (usuario.username if usuario else "")
                or "Educador sem nome"
            )
            cpf = educador.cpf or ""
            email = usuario.email if usuario else ""
            telefone = educador.telefone or ""
            genero_str = educador.genero.nome if educador.genero else "Não informado"
            cor_str = educador.cor_raca.nome if educador.cor_raca else "Não informado"

            nascimento = educador.data_nascimento
            nascimento_str = nascimento.strftime("%d/%m/%Y") if nascimento else "Não informado"
            idade = calcular_idade(nascimento)
            faixa = obter_faixa_etaria(idade)
            contagem_faixas_etarias[faixa] += 1

            cursos = list(educador.cursos_certificados.all())
            cursos_nomes = [c.nome for c in cursos]
            cursos_ids = [c.id for c in cursos]
            total_certificados_pedidos += len(cursos)

            # Endereço residencial
            end = getattr(educador, "endereco", None)
            if end:
                cep = end.cep or ""
                logradouro = end.logradouro or ""
                numero = end.numero or ""
                complemento = end.complemento or ""
                bairro = end.bairro or ""
                cid_res = end.cidade
                mun_res = cid_res.nome_cidade if cid_res else "Não informado"
                est_res = cid_res.estado.nome_estado if (cid_res and cid_res.estado) else "Não informado"
                sigla_res = cid_res.estado.sigla if (cid_res and cid_res.estado) else ""
            else:
                cep = ""
                logradouro = ""
                numero = ""
                complemento = ""
                bairro = ""
                mun_res = "Não informado"
                est_res = "Não informado"
                sigla_res = ""

            if mun_res != "Não informado":
                municipios_residencia_set.add(mun_res)
                municipios_residencia_counter[mun_res] += 1
                municipios_residencia_estados[mun_res] = sigla_res
            if est_res != "Não informado":
                estados_residencia_counter[est_res] += 1
                estados_residencia_siglas[est_res] = sigla_res

            # Vínculos escolares / atuações
            vinculos = [
                funcao_ed.educador_escola
                for funcao_ed in educador.funcoes.all()
                if funcao_ed.educador_escola
            ]

            info_comum = {
                "educador_id": educador.id,
                "nome": nome,
                "cpf": cpf,
                "email": email,
                "telefone": telefone,
                "data_nascimento": nascimento_str,
                "idade": idade if idade is not None else "",
                "faixa_etaria": faixa,
                "genero": genero_str,
                "cor": cor_str,
                "cursos_certificados": cursos_nomes,
                "cursos_certificados_ids": cursos_ids,
                "cep": cep,
                "logradouro": logradouro,
                "numero": numero,
                "complemento": complemento,
                "bairro": bairro,
                "municipio_residencia": mun_res,
                "estado_residencia": est_res,
                "sigla_uf_residencia": sigla_res,
            }

            if not vinculos:
                reg = dict(info_comum)
                reg.update(
                    escola="Não informado",
                    funcao="Não informado",
                    caracterizacao="Não informado",
                    tempo="Não informado",
                    municipio_atuacao=mun_res,
                    estado_atuacao=est_res,
                    sigla_uf_atuacao=sigla_res,
                )
                participantes_detalhados.append(reg)
            else:
                for v in vinculos:
                    escola_nome = v.escola.nome if getattr(v, "escola", None) else "Não informado"
                    funcao_nome = v.funcao.nome if getattr(v, "funcao", None) else "Não informado"
                    carac_nome = (
                        v.funcao_caracterizacao_turmas.nome
                        if getattr(v, "funcao_caracterizacao_turmas", None)
                        else "Não informado"
                    )
                    tempo_rotulo = ROTULOS_TEMPO_ATUACAO.get(v.tempo_atuacao, v.tempo_atuacao or "Não informado")

                    cidade_at = getattr(v, "cidade", None)
                    if cidade_at:
                        mun_at = cidade_at.nome_cidade or "Não informado"
                        est_at = cidade_at.estado.nome_estado if getattr(cidade_at, "estado", None) else "Não informado"
                        sigla_at = cidade_at.estado.sigla if (getattr(cidade_at, "estado", None) and cidade_at.estado.sigla) else ""
                    else:
                        mun_at = mun_res
                        est_at = est_res
                        sigla_at = sigla_res

                    if mun_at != "Não informado":
                        municipios_atuacao_set.add(mun_at)
                        municipios_atuacao_counter[mun_at] += 1
                        municipios_atuacao_estados[mun_at] = sigla_at
                    if est_at != "Não informado":
                        estados_atuacao_counter[est_at] += 1
                        estados_atuacao_siglas[est_at] = sigla_at
                    if escola_nome != "Não informado":
                        escolas_set.add(escola_nome)

                    if funcao_nome != "Não informado":
                        funcoes_counter[funcao_nome] += 1
                    if carac_nome != "Não informado":
                        caracterizacoes_counter[carac_nome] += 1
                    if tempo_rotulo != "Não informado":
                        tempo_counter[tempo_rotulo] += 1

                    reg = dict(info_comum)
                    reg.update(
                        escola=escola_nome,
                        funcao=funcao_nome,
                        caracterizacao=carac_nome,
                        tempo=tempo_rotulo,
                        municipio_atuacao=mun_at,
                        estado_atuacao=est_at,
                        sigla_uf_atuacao=sigla_at,
                    )
                    participantes_detalhados.append(reg)

        # 4. Agrupamentos para gráficos e mapas
        # Distribuição por Cursos
        curso_dados = []
        for c in cursos_catalogo:
            qtd = sum(1 for p in participantes_detalhados if c["id"] in p.get("cursos_certificados_ids", []))
            curso_dados.append({"label": c["nome"], "qtd": qtd, "id": c["id"]})
        curso_dados.sort(key=lambda x: x["qtd"], reverse=True)

        # Distribuição por Município de Atuação
        municipio_atuacao_dados = [
            {"label": m, "qtd": qtd, "state": municipios_atuacao_estados.get(m, "")}
            for m, qtd in municipios_atuacao_counter.most_common()
        ]

        # Distribuição por Estado de Atuação
        estado_atuacao_dados = [
            {"label": e, "qtd": qtd, "sigla": estados_atuacao_siglas.get(e, "")}
            for e, qtd in estados_atuacao_counter.most_common()
        ]

        # Distribuição por Município Residencial
        municipio_residencia_dados = [
            {"label": m, "qtd": qtd, "state": municipios_residencia_estados.get(m, "")}
            for m, qtd in municipios_residencia_counter.most_common()
        ]

        # Distribuição por Estado Residencial
        estado_residencia_dados = [
            {"label": e, "qtd": qtd, "sigla": estados_residencia_siglas.get(e, "")}
            for e, qtd in estados_residencia_counter.most_common()
        ]

        # Demografia: Gênero
        genero_dados = normalizar_distribuicao(
            educadores_base.values(label=F("genero__nome"))
            .annotate(qtd=Count("pk"))
            .order_by("-qtd"),
            "label",
        )

        # Demografia: Cor / Raça
        cor_dados = normalizar_distribuicao(
            educadores_base.values(label=F("cor_raca__nome"))
            .annotate(qtd=Count("pk"))
            .order_by("-qtd"),
            "label",
        )

        # Demografia: Faixas Etárias
        ordem_faixas = [
            "Menos de 25 anos",
            "25 a 34 anos",
            "35 a 44 anos",
            "45 a 54 anos",
            "55 anos ou mais",
            "Não informada",
        ]
        faixa_etaria_dados = [
            {"label": f, "qtd": contagem_faixas_etarias.get(f, 0)}
            for f in ordem_faixas
            if contagem_faixas_etarias.get(f, 0) > 0
        ]

        # Funções na EJA
        funcao_dados = [
            {"label": func, "qtd": qtd}
            for func, qtd in funcoes_counter.most_common()
        ]

        # Caracterização de turmas
        caracterizacao_dados = [
            {"label": carac, "qtd": qtd}
            for carac, qtd in caracterizacoes_counter.most_common()
        ]

        # Tempo de atuação
        tempo_dados = [
            {"label": t, "qtd": qtd}
            for t, qtd in tempo_counter.most_common()
        ]

        # Escolas
        vinculos_base = EducadorEscola.objects.filter(
            funcao_educador__educador__in=educadores_base
        ).distinct()
        escola_dados = normalizar_distribuicao(
            vinculos_base.values(nome_escola=F("escola__nome"))
            .annotate(qtd=Count("pk"))
            .order_by("-qtd"),
            "nome_escola",
        )

        total_educadores = educadores_base.count()
        total_vinculos = vinculos_base.count()

        context.update(
            cursos_catalogo=cursos_catalogo,
            curso_selecionado=curso_selecionado,
            total_solicitantes=total_educadores,
            total_certificados_pedidos=total_certificados_pedidos,
            total_municipios_atuacao=len(municipios_atuacao_set),
            total_municipios_residencia=len(municipios_residencia_set),
            total_escolas=len(escolas_set),
            total_vinculos=total_vinculos,
            participantes_detalhados=participantes_detalhados,
            curso_dados=curso_dados,
            municipio_atuacao_dados=municipio_atuacao_dados,
            estado_atuacao_dados=estado_atuacao_dados,
            municipio_residencia_dados=municipio_residencia_dados,
            estado_residencia_dados=estado_residencia_dados,
            genero_dados=genero_dados,
            cor_dados=cor_dados,
            faixa_etaria_dados=faixa_etaria_dados,
            funcao_dados=funcao_dados,
            caracterizacao_dados=caracterizacao_dados,
            tempo_dados=tempo_dados,
            escola_dados=escola_dados,
        )
        return context


reports_certificados = ReportsCertificadosView.as_view()

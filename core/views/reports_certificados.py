import csv
from collections import Counter
from datetime import date

from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, CharField, Count, F, Q, Value, When
from django.http import JsonResponse, StreamingHttpResponse
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


def montar_registro_participante(educador, vinculo=None, cursos=None):
    """Formata um dicionário plano para renderização na tabela ou exportação CSV."""
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

    if cursos is None:
        cursos = list(educador.cursos_certificados.all())
    cursos_nomes = [c.nome for c in cursos]
    cursos_ids = [c.id for c in cursos]

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

    info = {
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

    if vinculo:
        escola_nome = vinculo.escola.nome if getattr(vinculo, "escola", None) else "Não informado"
        funcao_nome = vinculo.funcao.nome if getattr(vinculo, "funcao", None) else "Não informado"
        carac_nome = (
            vinculo.funcao_caracterizacao_turmas.nome
            if getattr(vinculo, "funcao_caracterizacao_turmas", None)
            else "Não informado"
        )
        tempo_rotulo = ROTULOS_TEMPO_ATUACAO.get(vinculo.tempo_atuacao, vinculo.tempo_atuacao or "Não informado")
        cidade_at = getattr(vinculo, "cidade", None)
        if cidade_at:
            mun_at = cidade_at.nome_cidade or "Não informado"
            est_at = cidade_at.estado.nome_estado if getattr(cidade_at, "estado", None) else "Não informado"
            sigla_at = cidade_at.estado.sigla if (getattr(cidade_at, "estado", None) and cidade_at.estado.sigla) else ""
        else:
            mun_at = mun_res
            est_at = est_res
            sigla_at = sigla_res
        info.update(
            escola=escola_nome,
            funcao=funcao_nome,
            caracterizacao=carac_nome,
            tempo=tempo_rotulo,
            municipio_atuacao=mun_at,
            estado_atuacao=est_at,
            sigla_uf_atuacao=sigla_at,
        )
    else:
        info.update(
            escola="Não informado",
            funcao="Não informado",
            caracterizacao="Não informado",
            tempo="Não informado",
            municipio_atuacao=mun_res,
            estado_atuacao=est_res,
            sigla_uf_atuacao=sigla_res,
        )
    return info


def serializar_participantes(educadores_list):
    """Converte lista de objetos Educador em lista detalhada de registros."""
    participantes = []
    for educador in educadores_list:
        cursos = list(educador.cursos_certificados.all())
        vinculos = [
            f.educador_escola for f in educador.funcoes.all() if f.educador_escola
        ]
        if not vinculos:
            participantes.append(montar_registro_participante(educador, vinculo=None, cursos=cursos))
        else:
            for v in vinculos:
                participantes.append(montar_registro_participante(educador, vinculo=v, cursos=cursos))
    return participantes


def filtrar_educadores_relatorio(educadores_base, search=None, curso_id=None, curso_nome=None, estado=None, municipio=None, funcao=None):
    """Aplica filtros dinâmicos sobre a base de educadores."""
    qs = educadores_base

    if curso_id:
        try:
            cid = int(curso_id)
            qs = qs.filter(cursos_certificados__id=cid)
        except (ValueError, TypeError):
            qs = qs.filter(cursos_certificados__nome__iexact=curso_id)
    elif curso_nome:
        qs = qs.filter(cursos_certificados__nome__iexact=curso_nome)

    if search:
        search = search.strip()
        digits = "".join(filter(str.isdigit, search))
        q_search = (
            Q(nome_completo__icontains=search)
            | Q(usuario__first_name__icontains=search)
            | Q(usuario__last_name__icontains=search)
            | Q(usuario__email__icontains=search)
            | Q(telefone__icontains=search)
            | Q(endereco__cidade__nome_cidade__icontains=search)
            | Q(funcoes__educador_escola__escola__nome__icontains=search)
            | Q(funcoes__educador_escola__cidade__nome_cidade__icontains=search)
            | Q(cursos_certificados__nome__icontains=search)
        )
        if digits:
            q_search |= Q(cpf__icontains=digits)
        qs = qs.filter(q_search)

    if estado:
        estado = estado.strip()
        qs = qs.filter(
            Q(funcoes__educador_escola__cidade__estado__sigla__iexact=estado)
            | Q(funcoes__educador_escola__cidade__estado__nome_estado__iexact=estado)
            | Q(endereco__cidade__estado__sigla__iexact=estado)
            | Q(endereco__cidade__estado__nome_estado__iexact=estado)
        )

    if municipio:
        municipio = municipio.strip()
        qs = qs.filter(
            Q(funcoes__educador_escola__cidade__nome_cidade__iexact=municipio)
            | Q(endereco__cidade__nome_cidade__iexact=municipio)
        )

    if funcao:
        funcao = funcao.strip()
        qs = qs.filter(funcoes__educador_escola__funcao__nome__iexact=funcao)

    return qs.distinct()


@method_decorator(staff_required, name="dispatch")
class ReportsCertificadosView(TemplateView):
    """Painel analítico e relatórios dos educadores solicitantes de certificados."""

    template_name = "reports_certificados.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Catálogo de cursos para certificado com contagem total em 1 query agregada
        cursos_catalogo = list(
            CursoCertificado.objects.annotate(
                total_solicitantes=Count("educadores_solicitantes", distinct=True)
            ).values("id", "nome", "total_solicitantes").order_by("nome")
        )

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
        educadores_base = Educador.objects.filter(
            Q(cursos_certificados__isnull=False) | Q(funcoes__isnull=False)
        ).distinct()

        if curso_selecionado:
            educadores_base = educadores_base.filter(cursos_certificados__id=curso_selecionado["id"])

        # Vínculos escolares associados aos educadores da base
        vinculos_base = EducadorEscola.objects.filter(
            funcao_educador__educador__in=educadores_base
        ).distinct()

        # Amostra inicial de participantes (máximo 50) para renderização rápida do HTML
        educadores_iniciais_qs = educadores_base.select_related(
            "usuario", "genero", "cor_raca", "endereco__cidade__estado"
        ).prefetch_related(
            "cursos_certificados",
            "funcoes__educador_escola__cidade__estado",
            "funcoes__educador_escola__escola",
            "funcoes__educador_escola__funcao",
            "funcoes__educador_escola__funcao_caracterizacao_turmas",
        )[:50]

        participantes_detalhados = serializar_participantes(educadores_iniciais_qs)

        # 3. Totais e Indicadores calculados via banco de dados
        total_educadores = educadores_base.count()
        total_vinculos = vinculos_base.count()
        total_municipios_atuacao = (
            vinculos_base.filter(cidade__isnull=False).values("cidade").distinct().count()
        )
        total_municipios_residencia = (
            educadores_base.filter(endereco__cidade__isnull=False).values("endereco__cidade").distinct().count()
        )
        total_escolas = vinculos_base.filter(escola__isnull=False).values("escola").distinct().count()

        total_certificados_pedidos = (
            Educador.cursos_certificados.through.objects.filter(educador__in=educadores_base).count()
        )

        # 4. Agrupamentos para gráficos e mapas diretamente no banco
        # Distribuição por Cursos
        curso_qs = (
            CursoCertificado.objects.filter(educadores_solicitantes__in=educadores_base)
            .values("id", label=F("nome"))
            .annotate(qtd=Count("educadores_solicitantes", distinct=True))
            .order_by("-qtd")
        )
        curso_qtd_map = {item["id"]: item["qtd"] for item in curso_qs}
        curso_dados = [
            {"label": c["nome"], "qtd": curso_qtd_map.get(c["id"], 0), "id": c["id"]}
            for c in cursos_catalogo
        ]
        curso_dados.sort(key=lambda x: x["qtd"], reverse=True)

        # Distribuição por Município de Atuação
        municipio_atuacao_dados = list(
            vinculos_base.filter(cidade__isnull=False)
            .values(label=F("cidade__nome_cidade"), state=F("cidade__estado__sigla"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd")
        )

        # Distribuição por Estado de Atuação
        estado_atuacao_dados = list(
            vinculos_base.filter(cidade__estado__isnull=False)
            .values(label=F("cidade__estado__nome_estado"), sigla=F("cidade__estado__sigla"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd")
        )

        # Distribuição por Município Residencial
        municipio_residencia_dados = list(
            educadores_base.filter(endereco__cidade__isnull=False)
            .values(label=F("endereco__cidade__nome_cidade"), state=F("endereco__cidade__estado__sigla"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd")
        )

        # Distribuição por Estado Residencial
        estado_residencia_dados = list(
            educadores_base.filter(endereco__cidade__estado__isnull=False)
            .values(label=F("endereco__cidade__estado__nome_estado"), sigla=F("endereco__cidade__estado__sigla"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd")
        )

        # Demografia: Gênero
        genero_dados = normalizar_distribuicao(
            educadores_base.values(label=F("genero__nome"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd"),
            "label",
        )

        # Demografia: Cor / Raça
        cor_dados = normalizar_distribuicao(
            educadores_base.values(label=F("cor_raca__nome"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd"),
            "label",
        )

        # Demografia: Faixas Etárias
        hoje = timezone.now().date()
        d25 = hoje.replace(year=hoje.year - 25)
        d35 = hoje.replace(year=hoje.year - 35)
        d45 = hoje.replace(year=hoje.year - 45)
        d55 = hoje.replace(year=hoje.year - 55)

        faixas_db = educadores_base.annotate(
            faixa=Case(
                When(data_nascimento__isnull=True, then=Value("Não informada")),
                When(data_nascimento__gt=d25, then=Value("Menos de 25 anos")),
                When(data_nascimento__gt=d35, then=Value("25 a 34 anos")),
                When(data_nascimento__gt=d45, then=Value("35 a 44 anos")),
                When(data_nascimento__gt=d55, then=Value("45 a 54 anos")),
                default=Value("55 anos ou mais"),
                output_field=CharField(),
            )
        ).values("faixa").annotate(qtd=Count("pk", distinct=True))

        faixa_map = {row["faixa"]: row["qtd"] for row in faixas_db}
        ordem_faixas = [
            "Menos de 25 anos",
            "25 a 34 anos",
            "35 a 44 anos",
            "45 a 54 anos",
            "55 anos ou mais",
            "Não informada",
        ]
        faixa_etaria_dados = [
            {"label": f, "qtd": faixa_map.get(f, 0)}
            for f in ordem_faixas
            if faixa_map.get(f, 0) > 0
        ]

        # Funções na EJA
        funcao_dados = list(
            vinculos_base.filter(funcao__isnull=False)
            .values(label=F("funcao__nome"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd")
        )

        # Caracterização de turmas
        caracterizacao_dados = list(
            vinculos_base.filter(funcao_caracterizacao_turmas__isnull=False)
            .values(label=F("funcao_caracterizacao_turmas__nome"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd")
        )

        # Tempo de atuação
        tempo_qs = (
            vinculos_base.exclude(tempo_atuacao="")
            .values(label=F("tempo_atuacao"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd")
        )
        tempo_dados = [
            {"label": ROTULOS_TEMPO_ATUACAO.get(t["label"], t["label"]), "qtd": t["qtd"]}
            for t in tempo_qs
        ]

        # Escolas
        escola_dados = normalizar_distribuicao(
            vinculos_base.filter(escola__isnull=False)
            .values(nome_escola=F("escola__nome"))
            .annotate(qtd=Count("pk", distinct=True))
            .order_by("-qtd"),
            "nome_escola",
        )

        context.update(
            cursos_catalogo=cursos_catalogo,
            curso_selecionado=curso_selecionado,
            total_solicitantes=total_educadores,
            total_certificados_pedidos=total_certificados_pedidos,
            total_municipios_atuacao=total_municipios_atuacao,
            total_municipios_residencia=total_municipios_residencia,
            total_escolas=total_escolas,
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


@staff_required
def reports_certificados_participantes(request):
    """Endpoint AJAX para paginação e busca dinâmica da tabela de solicitantes."""
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(5, int(request.GET.get("page_size", 10))))
    except (ValueError, TypeError):
        page_size = 10

    curso_id = request.GET.get("curso")
    curso_nome = request.GET.get("curso_nome")
    search = request.GET.get("search")
    estado = request.GET.get("estado")
    municipio = request.GET.get("municipio")
    funcao = request.GET.get("funcao")

    educadores_base = Educador.objects.filter(
        Q(cursos_certificados__isnull=False) | Q(funcoes__isnull=False)
    ).distinct()

    qs = filtrar_educadores_relatorio(
        educadores_base,
        search=search,
        curso_id=curso_id,
        curso_nome=curso_nome,
        estado=estado,
        municipio=municipio,
        funcao=funcao,
    ).select_related(
        "usuario", "genero", "cor_raca", "endereco__cidade__estado"
    ).prefetch_related(
        "cursos_certificados",
        "funcoes__educador_escola__cidade__estado",
        "funcoes__educador_escola__escola",
        "funcoes__educador_escola__funcao",
        "funcoes__educador_escola__funcao_caracterizacao_turmas",
    )

    paginator = Paginator(qs, page_size)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages) if paginator.num_pages > 0 else []

    participantes = serializar_participantes(page_obj.object_list) if page_obj else []

    return JsonResponse({
        "success": True,
        "page": page_obj.number if page_obj else 1,
        "page_size": page_size,
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "participants": participantes,
    })


class Echo:
    """Implementa o protocolo de escrita para csv.writer."""
    def write(self, value):
        return value


@staff_required
def reports_certificados_export_csv(request):
    """Gera streaming de CSV com codificação UTF-8 BOM e baixo consumo de memória."""
    curso_id = request.GET.get("curso")
    curso_nome = request.GET.get("curso_nome")
    search = request.GET.get("search")
    estado = request.GET.get("estado")
    municipio = request.GET.get("municipio")
    funcao = request.GET.get("funcao")

    educadores_base = Educador.objects.filter(
        Q(cursos_certificados__isnull=False) | Q(funcoes__isnull=False)
    ).distinct()

    qs = filtrar_educadores_relatorio(
        educadores_base,
        search=search,
        curso_id=curso_id,
        curso_nome=curso_nome,
        estado=estado,
        municipio=municipio,
        funcao=funcao,
    ).select_related(
        "usuario", "genero", "cor_raca", "endereco__cidade__estado"
    ).prefetch_related(
        "cursos_certificados",
        "funcoes__educador_escola__cidade__estado",
        "funcoes__educador_escola__escola",
        "funcoes__educador_escola__funcao",
        "funcoes__educador_escola__funcao_caracterizacao_turmas",
    )

    def row_generator():
        yield "\ufeff"  # BOM UTF-8 para Excel abrir acentos corretamente
        buffer = Echo()
        writer = csv.writer(buffer, delimiter=";")

        headers = [
            "Nome Completo", "CPF", "E-mail", "Telefone", "Data de Nascimento",
            "Idade", "Gênero", "Cor / Raça", "Cursos Solicitados", "Município Residência",
            "UF Residência", "CEP", "Bairro", "Logradouro", "Escola",
            "Município Atuação", "UF Atuação", "Função na EJA", "Caracterização / Turmas",
            "Tempo de Atuação"
        ]
        yield writer.writerow(headers)

        for educador in qs.iterator(chunk_size=500):
            cursos = list(educador.cursos_certificados.all())
            vinculos = [
                f.educador_escola for f in educador.funcoes.all() if f.educador_escola
            ]
            regs = []
            if not vinculos:
                regs.append(montar_registro_participante(educador, vinculo=None, cursos=cursos))
            else:
                for v in vinculos:
                    regs.append(montar_registro_participante(educador, vinculo=v, cursos=cursos))

            for p in regs:
                cursos_str = ", ".join(p.get("cursos_certificados", []))
                row = [
                    p.get("nome", ""),
                    p.get("cpf", ""),
                    p.get("email", ""),
                    p.get("telefone", ""),
                    p.get("data_nascimento", ""),
                    p.get("idade", ""),
                    p.get("genero", ""),
                    p.get("cor", ""),
                    cursos_str,
                    p.get("municipio_residencia", ""),
                    p.get("sigla_uf_residencia", ""),
                    p.get("cep", ""),
                    p.get("bairro", ""),
                    f"{p.get('logradouro', '')} {p.get('numero', '')} {p.get('complemento', '')}".strip(),
                    p.get("escola", ""),
                    p.get("municipio_atuacao", ""),
                    p.get("sigla_uf_atuacao", ""),
                    p.get("funcao", ""),
                    p.get("caracterizacao", ""),
                    p.get("tempo", ""),
                ]
                yield writer.writerow(row)

    hoje_str = timezone.now().strftime("%Y-%m-%d")
    response = StreamingHttpResponse(row_generator(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="solicitacoes_certificados_pacto_eja_{hoje_str}.csv"'
    return response


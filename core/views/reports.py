from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.models import Atividade, Educador, EducadorEscola, Inscricao


ROTULOS_TEMPO_ATUACAO = {
    "0_3_anos": "0 a 3 anos",
    "4_6_anos": "4 a 6 anos",
    "mais_6_anos": "Mais de 6 anos",
}


def usuario_e_staff(usuario):
    """Restringe os relatórios a usuários autenticados da equipe."""
    return usuario.is_authenticated and usuario.is_staff


staff_required = user_passes_test(usuario_e_staff)


def normalizar_distribuicao(
    registros,
    campo_rotulo,
    rotulos=None,
    campos_extras=None,
):
    """Converte agregações do ORM no formato uniforme consumido pelos gráficos."""
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


def obter_escolaridade_educador(educador):
    """Retorna o maior nível de escolaridade cadastrado para o educador."""
    formacoes = list(educador.formacoes.all())
    if not formacoes:
        return "Não informado"
    formacoes_ordenadas = sorted(formacoes, key=lambda f: f.nivel_id or 0, reverse=True)
    return formacoes_ordenadas[0].nivel.nome


def dados_basicos_educador(educador):
    """Reúne os dados pessoais repetidos em cada vínculo do relatório detalhado."""
    usuario = educador.usuario
    rep = educador.representante_estado_undime_consed
    if rep is True:
        rep_label = "Sim"
    elif rep is False:
        rep_label = "Não"
    else:
        rep_label = "Não informado"

    return {
        "nome": (
            educador.nome_completo
            or usuario.get_full_name()
            or usuario.username
            or "Educador sem nome"
        ),
        "cpf": educador.cpf or "",
        "email": usuario.email or "",
        "telefone": educador.telefone or "",
        "genero": educador.genero.nome if educador.genero else "Não informado",
        "cor": educador.cor_raca.nome if educador.cor_raca else "Não informado",
        "escolaridade": obter_escolaridade_educador(educador),
        "representante_undime_consed": rep_label,
    }


def obter_cidade_educador(educador, vinculo=None):
    """Retorna a cidade vinculada à escola ou a cidade residencial do educador."""
    if vinculo and getattr(vinculo, "cidade", None):
        return vinculo.cidade
    try:
        endereco = getattr(educador, "endereco", None)
        if endereco and getattr(endereco, "cidade", None):
            return endereco.cidade
    except Exception:
        pass
    return None


def registro_participante(educador, vinculo=None):
    """Monta uma linha do relatório detalhado, com ou sem vínculo escolar."""
    registro = dados_basicos_educador(educador)
    cidade = obter_cidade_educador(educador, vinculo)

    if cidade:
        nome_cidade = cidade.nome_cidade or "Não informado"
        estado_nome = (
            cidade.estado.nome_estado
            if getattr(cidade, "estado", None)
            else "Não informado"
        )
        sigla_uf = (
            cidade.estado.sigla
            if getattr(cidade, "estado", None) and cidade.estado.sigla
            else ""
        )
    else:
        nome_cidade = "Não informado"
        estado_nome = "Não informado"
        sigla_uf = ""

    if not vinculo:
        registro.update(
            municipio=nome_cidade,
            estado=estado_nome,
            sigla_uf=sigla_uf,
            escola="Não informado",
            funcao="Não informado",
            tempo="Não informado",
        )
        return registro

    registro.update(
        municipio=nome_cidade,
        estado=estado_nome,
        sigla_uf=sigla_uf,
        escola=vinculo.escola.nome if getattr(vinculo, "escola", None) else "Não informado",
        funcao=vinculo.funcao.nome if getattr(vinculo, "funcao", None) else "Não informado",
        tempo=ROTULOS_TEMPO_ATUACAO.get(
            vinculo.tempo_atuacao,
            vinculo.tempo_atuacao or "Não informado",
        ),
    )
    return registro


def listar_participantes_detalhados(educadores_qs=None, atividade_selecionada_id=None):
    """Expande cada educador em uma linha por vínculo escolar cadastrado, incluindo inscrições em atividades."""
    if educadores_qs is None:
        educadores_qs = Educador.objects.all()

    educadores = educadores_qs.select_related(
        "usuario", "genero", "cor_raca", "endereco__cidade__estado"
    ).prefetch_related(
        "formacoes__nivel",
        "funcoes__educador_escola__cidade__estado",
        "funcoes__educador_escola__escola",
        "funcoes__educador_escola__funcao",
        "usuario__inscricoes_atividades__atividade",
    )
    participantes = []

    for educador in educadores:
        inscricoes = list(educador.usuario.inscricoes_atividades.all())
        atividades_info = []
        atividades_ids = []
        atividades_tipos = []
        atividades_modalidades = []
        atividades_status = []
        atividades_nomes = []

        modalidade_inscrito_atividade_atual = ""
        data_inscricao_atividade_atual = ""

        for insc in inscricoes:
            atividade = insc.atividade
            status_insc = "abertas" if atividade.inscricoes_abertas else "encerradas"
            status_ativo = "ativa" if atividade.ativo else "inativa"

            atividades_ids.append(atividade.id)
            atividades_tipos.append(atividade.tipo)
            atividades_modalidades.append(insc.modalidade)
            atividades_status.append(status_insc)
            atividades_status.append(status_ativo)
            atividades_nomes.append(atividade.titulo)

            if atividade_selecionada_id and atividade.id == atividade_selecionada_id:
                modalidade_inscrito_atividade_atual = insc.get_modalidade_display()
                data_inscricao_atividade_atual = (
                    insc.inscrito_em.strftime("%d/%m/%Y %H:%M")
                    if insc.inscrito_em
                    else ""
                )

            atividades_info.append({
                "id": atividade.id,
                "titulo": atividade.titulo,
                "tipo": atividade.tipo,
                "tipo_label": atividade.get_tipo_display(),
                "modalidade": insc.modalidade,
                "modalidade_label": insc.get_modalidade_display(),
                "atividade_modalidade": atividade.modalidade,
                "atividade_modalidade_label": atividade.get_modalidade_display(),
                "data_inscricao": (
                    insc.inscrito_em.strftime("%d/%m/%Y %H:%M")
                    if insc.inscrito_em
                    else ""
                ),
                "ativo": atividade.ativo,
                "inscricoes_abertas": atividade.inscricoes_abertas,
            })

        dados_atividades = {
            "atividades": atividades_info,
            "atividades_ids": list(set(atividades_ids)),
            "atividades_tipos": list(set(atividades_tipos)),
            "atividades_modalidades": list(set(atividades_modalidades)),
            "atividades_status": list(set(atividades_status)),
            "atividades_nomes": atividades_nomes,
            "modalidade_inscrito_atual": modalidade_inscrito_atividade_atual,
            "data_inscricao_atual": data_inscricao_atividade_atual,
        }

        vinculos = [
            funcao_educador.educador_escola
            for funcao_educador in educador.funcoes.all()
        ]
        if not vinculos:
            reg = registro_participante(educador)
            reg.update(dados_atividades)
            participantes.append(reg)
            continue

        for vinculo in vinculos:
            reg = registro_participante(educador, vinculo)
            reg.update(dados_atividades)
            participantes.append(reg)

    return participantes


@method_decorator(staff_required, name="dispatch")
class ReportsView(TemplateView):
    """Apresenta indicadores agregados e a relação detalhada de participantes."""

    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        """Executa as agregações e entrega estruturas prontas para tabelas e gráficos."""
        context = super().get_context_data(**kwargs)

        # 1. Catálogo completo de atividades para a central/modal de seleção
        atividades = Atividade.objects.prefetch_related("inscricoes").order_by("titulo")
        atividades_catalogo = []
        for a in atividades:
            insc_count = a.inscricoes.count()
            vagas_totais = a.vagas or 0
            taxa_ocupacao = (
                round((insc_count / vagas_totais * 100), 1)
                if vagas_totais > 0
                else 0
            )
            status_insc = "abertas" if a.inscricoes_abertas else "encerradas"
            status_label = (
                "Inscrições Abertas"
                if a.inscricoes_abertas
                else ("Inscrições Encerradas" if a.ativo else "Inativa")
            )

            atividades_catalogo.append({
                "id": a.id,
                "titulo": a.titulo,
                "descricao": a.descricao,
                "tipo": a.tipo,
                "tipo_label": a.get_tipo_display(),
                "modalidade": a.modalidade,
                "modalidade_label": a.get_modalidade_display(),
                "local": a.local or "",
                "link": a.link or "",
                "local_ou_link": a.local or a.link or "Não informado",
                "data_inicio": (
                    a.data_inicio.strftime("%d/%m/%Y %H:%M")
                    if a.data_inicio
                    else ""
                ),
                "data_fim": (
                    a.data_fim.strftime("%d/%m/%Y %H:%M")
                    if a.data_fim
                    else ""
                ),
                "inscricoes_fim": (
                    a.inscricoes_fim.strftime("%d/%m/%Y %H:%M")
                    if a.inscricoes_fim
                    else ""
                ),
                "vagas": a.vagas,
                "total_inscritos": insc_count,
                "vagas_restantes": a.vagas_restantes,
                "taxa_ocupacao": taxa_ocupacao,
                "ativo": a.ativo,
                "inscricoes_abertas": a.inscricoes_abertas,
                "status_slug": status_insc if a.ativo else "inativa",
                "status_label": status_label,
            })

        # 2. Verificação de filtro por atividade ativa ou visão geral via URL
        atividade_id_param = self.request.GET.get("atividade")
        visao_geral = self.request.GET.get("visao") == "geral"
        atividade_selecionada = None
        atividade_selecionada_dict = None

        if atividade_id_param:
            try:
                atividade_id = int(atividade_id_param)
                atividade_selecionada = Atividade.objects.filter(pk=atividade_id).first()
                if atividade_selecionada:
                    atividade_selecionada_dict = next(
                        (item for item in atividades_catalogo if item["id"] == atividade_id),
                        None,
                    )
            except (ValueError, TypeError):
                atividade_selecionada = None

        exibir_dashboard = bool(atividade_selecionada or visao_geral)

        if atividade_selecionada:
            educadores_base = Educador.objects.filter(
                usuario__inscricoes_atividades__atividade=atividade_selecionada
            ).distinct()
            vinculos = EducadorEscola.objects.filter(
                funcao_educador__educador__in=educadores_base
            ).distinct()

            participantes_por_modalidade = (
                Inscricao.objects.filter(atividade=atividade_selecionada)
                .values(mod_inscricao=F("modalidade"))
                .annotate(qtd=Count("usuario", distinct=True))
                .order_by("-qtd")
            )
            atividade_dados = normalizar_distribuicao(
                participantes_por_modalidade,
                "mod_inscricao",
                rotulos={"online": "On-line", "presencial": "Presencial"},
            )
        else:
            educadores_base = Educador.objects.all()
            vinculos = EducadorEscola.objects.all()
            participantes_por_atividade = (
                Inscricao.objects.values(nome_atividade=F("atividade__titulo"))
                .annotate(qtd=Count("usuario", distinct=True))
                .order_by("-qtd")
            )
            atividade_dados = normalizar_distribuicao(
                participantes_por_atividade,
                "nome_atividade",
            )

        participantes_por_escola = (
            vinculos.values(nome_escola=F("escola__nome"))
            .annotate(qtd=Count("pk"))
            .order_by("-qtd")
        )

        from collections import Counter
        contagem_escolaridade = Counter()
        for educador in educadores_base.prefetch_related("formacoes__nivel"):
            contagem_escolaridade[obter_escolaridade_educador(educador)] += 1

        escolaridade_dados = [
            {"label": nivel_nome, "qtd": qtd}
            for nivel_nome, qtd in contagem_escolaridade.most_common()
        ]

        participantes_detalhados = listar_participantes_detalhados(
            educadores_qs=educadores_base,
            atividade_selecionada_id=atividade_selecionada.id if atividade_selecionada else None,
        )

        contagem_municipios = Counter()
        municipio_estados = {}
        contagem_estados = Counter()
        estado_siglas = {}

        for p in participantes_detalhados:
            m = p.get("municipio") or "Não informado"
            contagem_municipios[m] += 1
            if m != "Não informado" and m not in municipio_estados:
                municipio_estados[m] = p.get("sigla_uf") or ""

            e = p.get("estado") or "Não informado"
            contagem_estados[e] += 1
            if e != "Não informado" and e not in estado_siglas:
                estado_siglas[e] = p.get("sigla_uf") or ""

        municipio_dados = [
            {
                "label": m,
                "qtd": qtd,
                "state": municipio_estados.get(m, ""),
            }
            for m, qtd in contagem_municipios.most_common()
        ]

        estado_dados = [
            {
                "label": e,
                "qtd": qtd,
                "sigla": estado_siglas.get(e, ""),
            }
            for e, qtd in contagem_estados.most_common()
        ]

        total_municipios = len({
            p["municipio"]
            for p in participantes_detalhados
            if p.get("municipio") and p["municipio"] != "Não informado"
        })

        context.update(
            exibir_dashboard=exibir_dashboard,
            visao_geral=visao_geral,
            atividade_selecionada=atividade_selecionada_dict,
            atividades_catalogo=atividades_catalogo,
            total_educadores=educadores_base.count(),
            total_vinculos=vinculos.count(),
            total_escolas=vinculos.values("escola").distinct().count(),
            total_municipios=total_municipios,
            participantes_detalhados=participantes_detalhados,
            atividade_dados=atividade_dados,
            municipio_dados=municipio_dados,
            escola_dados=normalizar_distribuicao(
                participantes_por_escola, "nome_escola"
            ),
            estado_dados=estado_dados,
            genero_dados=normalizar_distribuicao(
                educadores_base.values(nome_genero=F("genero__nome"))
                .annotate(qtd=Count("pk"))
                .order_by("-qtd"),
                "nome_genero",
            ),
            cor_dados=normalizar_distribuicao(
                educadores_base.values(cor=F("cor_raca__nome"))
                .annotate(qtd=Count("pk"))
                .order_by("-qtd"),
                "cor",
            ),
            funcao_dados=normalizar_distribuicao(
                vinculos.values(nome_funcao=F("funcao__nome"))
                .annotate(qtd=Count("pk"))
                .order_by("-qtd"),
                "nome_funcao",
            ),
            tempo_dados=normalizar_distribuicao(
                vinculos.values("tempo_atuacao")
                .annotate(qtd=Count("pk"))
                .order_by("-qtd"),
                "tempo_atuacao",
                ROTULOS_TEMPO_ATUACAO,
            ),
            escolaridade_dados=escolaridade_dados,
        )
        return context


# A URL importa uma função; ``as_view`` adapta a classe para esse contrato.
reports = ReportsView.as_view()


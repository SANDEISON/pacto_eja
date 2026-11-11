from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F, Prefetch
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.menu import can_view_reports
from core.models import (
    Atividade,
    Credenciamento,
    Educador,
    EducadorEscola,
    Frequencia,
    Inscricao,
    ProgramacaoSala,
    Sala,
)


ROTULOS_TEMPO_ATUACAO = {
    "0_3_anos": "0 a 3 anos",
    "4_6_anos": "4 a 6 anos",
    "mais_6_anos": "Mais de 6 anos",
}


def datas_disponiveis_atividade(atividade):
    datas = sorted({p.dia for p in atividade.programacoes.all()})
    if not datas:
        inicio = timezone.localtime(atividade.data_inicio).date()
        fim = timezone.localtime(atividade.data_fim).date()
        datas = [inicio + timezone.timedelta(days=i) for i in range((fim - inicio).days + 1)]
    return [data.isoformat() for data in datas]


reports_required = user_passes_test(can_view_reports)


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


def obter_formacoes_academicas(educador):
    """Retorna todas as formações em rótulos legíveis para a tabela e o CSV."""
    formacoes = []
    for formacao in educador.formacoes.all():
        partes = [formacao.nivel.nome, formacao.nome_curso, formacao.instituicao]
        if formacao.situacao_id:
            partes.append(formacao.situacao.nome)
        formacoes.append(" — ".join(parte for parte in partes if parte))
    return formacoes or ["Não informado"]


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

    registro = {
        "educador_id": educador.pk,
        "undime_confirmada": educador.undime_confirmada,
        "undime_confirmado_por": (
            educador.undime_confirmado_por.get_full_name()
            or educador.undime_confirmado_por.get_username()
        ) if educador.undime_confirmado_por_id else "",
        "undime_confirmado_em": (
            timezone.localtime(educador.undime_confirmado_em).strftime("%d/%m/%Y %H:%M:%S")
            if educador.undime_confirmado_em else ""
        ),
        "nome": (
            educador.nome_completo
            or usuario.get_full_name()
            or usuario.username
            or "Educador sem nome"
        ),
        "cpf": educador.cpf or "",
        "email": usuario.email or "",
        "telefone": educador.telefone or "",
        "data_nascimento": educador.data_nascimento.strftime("%d/%m/%Y") if educador.data_nascimento else "Não informado",
        "genero": educador.genero.nome if educador.genero else "Não informado",
        "cor": educador.cor_raca.nome if educador.cor_raca else "Não informado",
        "escolaridade": obter_escolaridade_educador(educador),
        "formacoes_academicas": obter_formacoes_academicas(educador),
        "representante_undime_consed": rep_label,
    }

    endereco = getattr(educador, "endereco", None)
    cidade_residencia = endereco.cidade if endereco else None
    estado_residencia = cidade_residencia.estado if cidade_residencia else None
    registro.update(
        estado_civil=educador.estado_civil.nome if educador.estado_civil else "Não informado",
        cep=endereco.cep if endereco else "",
        logradouro=endereco.logradouro if endereco else "",
        numero=endereco.numero if endereco else "",
        bairro=endereco.bairro if endereco else "",
        complemento=endereco.complemento if endereco else "",
        municipio_residencia=cidade_residencia.nome_cidade if cidade_residencia else "Não informado",
        uf_residencia=estado_residencia.sigla if estado_residencia else "Não informado",
    )
    return registro


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
    """Monta uma linha única do relatório detalhado, agregando os vínculos escolares do educador."""
    registro = dados_basicos_educador(educador)

    if vinculo is None:
        lista_vinculos = []
    elif isinstance(vinculo, (list, tuple)):
        lista_vinculos = list(vinculo)
    else:
        lista_vinculos = [vinculo]

    cidade = None
    for v in lista_vinculos:
        cid = obter_cidade_educador(educador, v)
        if cid:
            cidade = cid
            break
    if not cidade:
        cidade = obter_cidade_educador(educador)

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

    escolas_nomes = []
    funcoes_nomes = []
    tempos_nomes = []

    for v in lista_vinculos:
        if getattr(v, "escola", None) and getattr(v.escola, "nome", None):
            nome_esc = v.escola.nome.strip()
            if nome_esc and nome_esc not in escolas_nomes:
                escolas_nomes.append(nome_esc)
        if getattr(v, "funcao", None) and getattr(v.funcao, "nome", None):
            nome_func = v.funcao.nome.strip()
            if nome_func and nome_func not in funcoes_nomes:
                funcoes_nomes.append(nome_func)
        if getattr(v, "tempo_atuacao", None):
            rotulo_tempo = ROTULOS_TEMPO_ATUACAO.get(v.tempo_atuacao, v.tempo_atuacao)
            if rotulo_tempo and rotulo_tempo not in tempos_nomes:
                tempos_nomes.append(rotulo_tempo)

    registro.update(
        municipio=nome_cidade,
        estado=estado_nome,
        sigla_uf=sigla_uf,
        escola=", ".join(escolas_nomes) if escolas_nomes else "Não informado",
        funcao=", ".join(funcoes_nomes) if funcoes_nomes else "Não informado",
        tempo=", ".join(tempos_nomes) if tempos_nomes else "Não informado",
    )
    return registro


def listar_participantes_detalhados(educadores_qs=None, atividade_selecionada_id=None):
    """Retorna uma linha única por educador, agregando vínculos escolares e incluindo inscrições em atividades."""
    if educadores_qs is None:
        educadores_qs = Educador.objects.all()

    educadores = educadores_qs.select_related(
        "usuario", "undime_confirmado_por", "genero", "cor_raca", "estado_civil", "endereco__cidade__estado"
    ).prefetch_related(
        "formacoes__nivel",
        "formacoes__situacao",
        "funcoes__educador_escola__cidade__estado",
        "funcoes__educador_escola__escola",
        "funcoes__educador_escola__funcao",
        "usuario__inscricoes_atividades__atividade",
        "usuario__inscricoes_atividades__atividade__inscricoes",
        Prefetch(
            "usuario__inscricoes_atividades__atividade__programacoes",
            queryset=ProgramacaoSala.objects.annotate(_total_inscritos=Count("inscricoes")),
        ),
        "usuario__inscricoes_atividades__programacoes__sala",
        "usuario__inscricoes_atividades__programacoes__tematica",
        "usuario__inscricoes_atividades__refeicoes",
        Prefetch(
            "usuario__inscricoes_atividades__frequencias",
            queryset=Frequencia.objects.select_related("programacao__sala"),
        ),
        "usuario__inscricoes_atividades__credenciamento",
    )
    participantes = []
    status_por_atividade = {}

    for educador in educadores:
        inscricoes = list(educador.usuario.inscricoes_atividades.all())
        atividades_info = []
        atividades_ids = []
        atividades_tipos = []
        atividades_modalidades = []
        atividades_status = []
        atividades_nomes = []
        programacoes_ids = []
        programacoes_labels = []
        programacoes_detalhadas = []
        refeicoes_labels = []
        modalidades_labels = []

        modalidade_inscrito_atividade_atual = ""
        data_inscricao_atividade_atual = ""
        data_alteracao_atividade_atual = ""
        refeicoes_inscrito_atividade_atual = []
        frequencias_atividade_atual = []
        todas_frequencias = []

        for insc in inscricoes:
            atividade = insc.atividade
            if atividade.pk not in status_por_atividade:
                status_por_atividade[atividade.pk] = atividade.inscricoes_abertas
            inscricoes_abertas = status_por_atividade[atividade.pk]
            status_insc = "abertas" if inscricoes_abertas else "encerradas"
            status_ativo = "ativa" if atividade.ativo else "inativa"

            atividades_ids.append(atividade.id)
            atividades_tipos.append(atividade.tipo)
            atividades_modalidades.append(insc.modalidade)
            modalidades_labels.append(insc.get_modalidade_display())
            atividades_status.append(status_insc)
            atividades_status.append(status_ativo)
            atividades_nomes.append(atividade.titulo)

            insc_progs = []
            for p_sala in insc.programacoes.all():
                prog_label = f"{p_sala.sala.nome} — {p_sala.get_turno_display()} ({p_sala.dia.strftime('%d/%m/%Y')})"
                if p_sala.tematica:
                    prog_label += f" ({p_sala.tematica.nome})"

                if not atividade_selecionada_id or atividade.id == atividade_selecionada_id:
                    programacoes_ids.append(p_sala.id)
                    programacoes_labels.append(prog_label)
                    programacoes_detalhadas.append({
                        "id": p_sala.id,
                        "label": prog_label,
                        "sala": p_sala.sala.nome,
                        "turno": p_sala.get_turno_display(),
                        "data": p_sala.dia.strftime("%d/%m/%Y"),
                        "modalidade": p_sala.get_modalidade_display(),
                        "tematica": p_sala.tematica.nome if p_sala.tematica else "",
                        "atividade_id": atividade.id,
                    })
                insc_progs.append(prog_label)

            insc_refeicoes = [str(refeicao) for refeicao in insc.refeicoes.all()]
            refeicoes_labels.extend(f"{atividade.titulo}: {refeicao}" for refeicao in insc_refeicoes)

            insc_freqs = list(insc.frequencias.all())
            todas_frequencias.extend(insc_freqs)

            if atividade_selecionada_id and atividade.id == atividade_selecionada_id:
                modalidade_inscrito_atividade_atual = insc.get_modalidade_display()
                refeicoes_inscrito_atividade_atual = insc_refeicoes
                frequencias_atividade_atual.extend(insc_freqs)
                data_inscricao_atividade_atual = (
                    timezone.localtime(insc.inscrito_em).strftime("%d/%m/%Y %H:%M")
                    if insc.inscrito_em
                    else ""
                )
                data_alteracao_atividade_atual = (
                    timezone.localtime(insc.alterado_em).strftime("%d/%m/%Y %H:%M")
                    if insc.alterado_em else ""
                )

            atividades_info.append({
                "id": atividade.id,
                "vai_apresentar_trabalho": insc.vai_apresentar_trabalho,
                "titulo": atividade.titulo,
                "tipo": atividade.tipo,
                "tipo_label": atividade.get_tipo_display(),
                "modalidade": insc.modalidade,
                "modalidade_label": insc.get_modalidade_display(),
                "atividade_modalidade": atividade.modalidade,
                "atividade_modalidade_label": atividade.get_modalidade_display(),
                "programacoes": insc_progs,
                "refeicoes": insc_refeicoes,
                "refeicoes_ids": [r.id for r in insc.refeicoes.all()],
                "datas": (
                    sorted({p.dia.isoformat() for p in insc.programacoes.all()})
                    if atividade.programacoes.all()
                    else datas_disponiveis_atividade(atividade)
                ),
                "data_inscricao": (
                    insc.inscrito_em.strftime("%d/%m/%Y %H:%M")
                    if insc.inscrito_em
                    else ""
                ),
                "ativo": atividade.ativo,
                "inscricoes_abertas": inscricoes_abertas,
            })

        dados_atividades = {
            "atividades": atividades_info,
            "atividades_ids": list(set(atividades_ids)),
            "atividades_tipos": list(set(atividades_tipos)),
            "atividades_modalidades": list(set(atividades_modalidades)),
            "atividades_status": list(set(atividades_status)),
            "atividades_nomes": atividades_nomes,
            "programacoes_ids": list(set(programacoes_ids)),
            "programacoes_labels": list(set(programacoes_labels)),
            "programacoes": programacoes_detalhadas,
            "modalidade_inscrito_atual": modalidade_inscrito_atividade_atual,
            "data_inscricao_atual": data_inscricao_atividade_atual,
            "data_alteracao_atual": data_alteracao_atividade_atual,
            "refeicoes_inscrito_atual": refeicoes_inscrito_atividade_atual,
            "refeicoes": refeicoes_labels,
            "modalidades_inscricao": list(dict.fromkeys(modalidades_labels)),
        }

        vinculos = [
            funcao_educador.educador_escola
            for funcao_educador in educador.funcoes.all()
            if getattr(funcao_educador, "educador_escola", None)
        ]

        freqs_relevantes = frequencias_atividade_atual if atividade_selecionada_id else todas_frequencias
        freq_presenciais = [f for f in freqs_relevantes if f.programacao.modalidade == "presencial"]
        freq_online = [f for f in freqs_relevantes if f.programacao.modalidade == "online"]
        salas_presencial = sorted(list({f.programacao.sala.nome for f in freq_presenciais}))
        salas_online = sorted(list({f.programacao.sala.nome for f in freq_online}))
        presente = len(freqs_relevantes) > 0

        # Credenciamento e entrega de material
        credenciado = False
        credenciado_em = ""
        credenciado_metodo = ""
        for insc in inscricoes:
            if not atividade_selecionada_id or insc.atividade_id == atividade_selecionada_id:
                if hasattr(insc, "credenciamento") and insc.credenciamento is not None:
                    credenciado = True
                    credenciado_em = (
                        timezone.localtime(insc.credenciamento.registrado_em).strftime("%d/%m/%Y %H:%M")
                        if insc.credenciamento.registrado_em
                        else ""
                    )
                    credenciado_metodo = insc.credenciamento.get_metodo_display()
                    break

        is_presencial = (
            modalidade_inscrito_atividade_atual.lower() == "presencial"
            or any(m == "presencial" for m in atividades_modalidades)
        )
        if credenciado:
            recebeu_material = "Sim"
        elif is_presencial:
            recebeu_material = "Não (Pendente)"
        else:
            recebeu_material = "Não se aplica (On-line)"

        dados_frequencia = {
            "presente": presente,
            "presente_presencial": len(freq_presenciais) > 0,
            "presente_online": len(freq_online) > 0,
            "total_frequencias": len(freqs_relevantes),
            "total_frequencias_presencial": len(freq_presenciais),
            "total_frequencias_online": len(freq_online),
            "salas_presente_presencial": ", ".join(salas_presencial) if salas_presencial else "",
            "salas_presente_online": ", ".join(salas_online) if salas_online else "",
            "status_presenca": "Presente" if presente else "Ausente",
            "credenciado": credenciado,
            "credenciado_em": credenciado_em,
            "credenciado_metodo": credenciado_metodo,
            "recebeu_material": recebeu_material,
        }

        reg = registro_participante(educador, vinculos)
        reg.update(dados_atividades)
        reg.update(dados_frequencia)
        participantes.append(reg)

    return participantes


@method_decorator(reports_required, name="dispatch")
class ReportsView(TemplateView):
    """Apresenta indicadores agregados e a relação detalhada de participantes."""

    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        """Executa as agregações e entrega estruturas prontas para tabelas e gráficos."""
        context = super().get_context_data(**kwargs)

        # 1. Catálogo completo de atividades para a central/modal de seleção
        atividades = Atividade.objects.prefetch_related(
            "inscricoes",
            "refeicoes",
            "programacoes__sala",
            "programacoes__tematica",
            "programacoes__inscricoes",
        ).order_by("titulo")
        atividades_catalogo = []
        for a in atividades:
            insc_count = a.inscricoes.count()
            vagas_totais = a.vagas + a.vagas_online
            vagas_ocupadas = vagas_totais - a.vagas_restantes - a.vagas_online_restantes
            taxa_ocupacao = (
                round((vagas_ocupadas / vagas_totais * 100), 1)
                if vagas_totais > 0
                else 0
            )
            status_insc = "abertas" if a.inscricoes_abertas else "encerradas"
            status_label = (
                "Inscrições Abertas"
                if a.inscricoes_abertas
                else ("Inscrições Encerradas" if a.ativo else "Inativa")
            )

            progs_disponiveis = []
            progs_ids = []
            for p in a.programacoes.all():
                p_label = f"{p.sala.nome} — {p.get_turno_display()} ({p.dia.strftime('%d/%m/%Y')})"
                if p.tematica:
                    p_label += f" ({p.tematica.nome})"
                progs_disponiveis.append({
                    "id": p.id,
                    "label": p_label,
                    "sala": p.sala.nome,
                    "turno": p.get_turno_display(),
                    "data": p.dia.strftime("%d/%m/%Y"),
                    "modalidade": p.get_modalidade_display(),
                    "tematica": p.tematica.nome if p.tematica else "",
                })
                progs_ids.append(p.id)

            atividades_catalogo.append({
                "id": a.id,
                "titulo": a.titulo,
                "descricao": a.descricao,
                "tipo": a.tipo,
                "tipo_label": a.get_tipo_display(),
                "modalidade": a.modalidade,
                "modalidade_label": a.get_modalidade_display(),
                "local": a.local or "",
                "local_url": a.local_url if a.local else "",
                "link": a.link or "",
                "local_ou_link": a.local or a.link or "Não informado",
                "data_inicio": (
                    timezone.localtime(a.data_inicio).strftime("%d/%m/%Y %H:%M")
                    if a.data_inicio
                    else ""
                ),
                "data_fim": (
                    timezone.localtime(a.data_fim).strftime("%d/%m/%Y %H:%M")
                    if a.data_fim
                    else ""
                ),
                "inscricoes_fim": (
                    timezone.localtime(a.inscricoes_fim).strftime("%d/%m/%Y %H:%M")
                    if a.inscricoes_fim
                    else ""
                ),
                "vagas": a.vagas,
                "vagas_online": a.vagas_online,
                "total_inscritos": insc_count,
                "vagas_restantes": a.vagas_restantes,
                "vagas_online_restantes": a.vagas_online_restantes,
                "vagas_totais": vagas_totais,
                "vagas_disponiveis": a.vagas_restantes + a.vagas_online_restantes,
                "vagas_preenchidas": vagas_ocupadas,
                "vagas_presenciais_preenchidas": a.vagas - a.vagas_restantes,
                "vagas_online_preenchidas": a.vagas_online - a.vagas_online_restantes,
                "taxa_ocupacao": taxa_ocupacao,
                "ativo": a.ativo,
                "inscricoes_abertas": a.inscricoes_abertas,
                "status_slug": status_insc if a.ativo else "inativa",
                "status_label": status_label,
                "programacoes": progs_disponiveis,
                "datas": datas_disponiveis_atividade(a),
                "refeicoes": [{"id": r.id, "label": str(r), "data": r.data.isoformat()} for r in a.refeicoes.all()],
                "programacoes_ids": progs_ids,
                "total_programacoes": len(progs_disponiveis),
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

        # Programações disponíveis
        programacoes_catalogo = []
        if atividade_selecionada:
            progs_qs = (
                atividade_selecionada.programacoes.select_related("sala", "tematica")
                .order_by("data", "turno", "sala__nome")
            )
        else:
            progs_qs = (
                ProgramacaoSala.objects.filter(atividades__isnull=False)
                .distinct()
                .select_related("sala", "tematica")
                .order_by("data", "turno", "sala__nome")
            )

        for prog in progs_qs:
            prog_label = f"{prog.sala.nome} — {prog.get_turno_display()} ({prog.dia.strftime('%d/%m/%Y')})"
            if prog.tematica:
                prog_label += f" ({prog.tematica.nome})"
            programacoes_catalogo.append({
                "id": prog.id,
                "label": prog_label,
                "sala": prog.sala.nome,
                "turno": prog.get_turno_display(),
                "data": prog.dia.strftime("%d/%m/%Y"),
                "modalidade": prog.get_modalidade_display(),
                "tematica": prog.tematica.nome if prog.tematica else "",
            })

        # =========================================================================
        # Indicadores e Relatórios de Frequência & Presença / Ausência
        # =========================================================================
        total_inscritos = len(participantes_detalhados)
        total_presentes = sum(1 for p in participantes_detalhados if p.get("presente"))
        total_presentes_presencial = sum(1 for p in participantes_detalhados if p.get("presente_presencial"))
        total_presentes_online = sum(1 for p in participantes_detalhados if p.get("presente_online"))
        total_ausentes = total_inscritos - total_presentes

        total_ausentes_presencial = sum(
            1 for p in participantes_detalhados
            if (p.get("modalidade_inscrito_atual", "").lower() == "presencial" or
                "presencial" in [m.lower() for m in p.get("atividades_modalidades", [])])
            and not p.get("presente_presencial")
        )
        total_ausentes_online = sum(
            1 for p in participantes_detalhados
            if ("online" in p.get("modalidade_inscrito_atual", "").lower() or
                "remoto" in p.get("modalidade_inscrito_atual", "").lower() or
                any("online" in m.lower() for m in p.get("atividades_modalidades", [])))
            and not p.get("presente_online")
        )
        taxa_presenca = round((total_presentes / total_inscritos * 100), 1) if total_inscritos else 0.0
        taxa_ausencia = round((total_ausentes / total_inscritos * 100), 1) if total_inscritos else 0.0

        # Credenciamento e entrega de material no evento
        total_credenciados = sum(1 for p in participantes_detalhados if p.get("credenciado"))
        total_inscritos_presenciais = sum(
            1 for p in participantes_detalhados
            if (p.get("modalidade_inscrito_atual", "").lower() == "presencial" or
                "presencial" in [m.lower() for m in p.get("atividades_modalidades", [])])
        )
        taxa_credenciamento = (
            round((total_credenciados / total_inscritos_presenciais * 100), 1)
            if total_inscritos_presenciais
            else 0.0
        )
        total_credenciamento_pendente = max(0, total_inscritos_presenciais - total_credenciados)

        frequencia_kpis = {
            "total_inscritos": total_inscritos,
            "total_presentes": total_presentes,
            "total_presentes_presencial": total_presentes_presencial,
            "total_presentes_online": total_presentes_online,
            "total_ausentes": total_ausentes,
            "total_ausentes_presencial": total_ausentes_presencial,
            "total_ausentes_online": total_ausentes_online,
            "taxa_presenca": taxa_presenca,
            "taxa_ausencia": taxa_ausencia,
            "total_credenciados": total_credenciados,
            "total_inscritos_presenciais": total_inscritos_presenciais,
            "total_credenciamento_pendente": total_credenciamento_pendente,
            "taxa_credenciamento": taxa_credenciamento,
        }

        # 1. Presença e Ausência por Estado (online e presencial)
        estados_map = {}
        for p in participantes_detalhados:
            est = p.get("estado") or "Não informado"
            sigla = p.get("sigla_uf") or ""
            uid = p.get("educador_id")
            is_p = (
                p.get("modalidade_inscrito_atual", "").lower() == "presencial" or
                "presencial" in [m.lower() for m in p.get("atividades_modalidades", [])]
            )
            is_o = (
                "online" in p.get("modalidade_inscrito_atual", "").lower() or
                "remoto" in p.get("modalidade_inscrito_atual", "").lower() or
                any("online" in m.lower() for m in p.get("atividades_modalidades", []))
            )
            pres_p = p.get("presente_presencial", False)
            pres_o = p.get("presente_online", False)
            pres_any = p.get("presente", False)

            if est not in estados_map:
                estados_map[est] = {
                    "label": est,
                    "sigla": sigla,
                    "_users_all": set(),
                    "_users_p_insc": set(),
                    "_users_o_insc": set(),
                    "_users_p_pres": set(),
                    "_users_o_pres": set(),
                    "_users_all_pres": set(),
                }
            estados_map[est]["_users_all"].add(uid)
            if is_p:
                estados_map[est]["_users_p_insc"].add(uid)
            if is_o:
                estados_map[est]["_users_o_insc"].add(uid)
            if pres_p:
                estados_map[est]["_users_p_pres"].add(uid)
            if pres_o:
                estados_map[est]["_users_o_pres"].add(uid)
            if pres_any:
                estados_map[est]["_users_all_pres"].add(uid)

        frequencia_estado_dados = []
        for d in estados_map.values():
            tot_insc = len(d["_users_all"])
            pres_p = len(d["_users_p_pres"])
            pres_o = len(d["_users_o_pres"])
            pres_tot = len(d["_users_all_pres"])
            aus_p = len(d["_users_p_insc"] - d["_users_p_pres"])
            aus_o = len(d["_users_o_insc"] - d["_users_o_pres"])
            aus_tot = len(d["_users_all"] - d["_users_all_pres"])
            tx_p = round(pres_tot / tot_insc * 100, 1) if tot_insc else 0.0
            tx_a = round(aus_tot / tot_insc * 100, 1) if tot_insc else 0.0
            frequencia_estado_dados.append({
                "label": d["label"],
                "sigla": d["sigla"],
                "total_inscritos": tot_insc,
                "presencial": pres_p,
                "online": pres_o,
                "qtd": pres_tot,
                "presencial_ausentes": aus_p,
                "online_ausentes": aus_o,
                "total_ausentes": aus_tot,
                "taxa_presenca": tx_p,
                "taxa_ausencia": tx_a,
            })
        frequencia_estado_dados.sort(key=lambda x: x["qtd"], reverse=True)

        # 2. Presença e Ausência por Cidade (online e presencial)
        cidades_map = {}
        for p in participantes_detalhados:
            cid = p.get("municipio") or "Não informado"
            sigla = p.get("sigla_uf") or ""
            uid = p.get("educador_id")
            chave = (cid, sigla)
            is_p = (
                p.get("modalidade_inscrito_atual", "").lower() == "presencial" or
                "presencial" in [m.lower() for m in p.get("atividades_modalidades", [])]
            )
            is_o = (
                "online" in p.get("modalidade_inscrito_atual", "").lower() or
                "remoto" in p.get("modalidade_inscrito_atual", "").lower() or
                any("online" in m.lower() for m in p.get("atividades_modalidades", []))
            )
            pres_p = p.get("presente_presencial", False)
            pres_o = p.get("presente_online", False)
            pres_any = p.get("presente", False)

            if chave not in cidades_map:
                cidades_map[chave] = {
                    "label": cid,
                    "sigla": sigla,
                    "_users_all": set(),
                    "_users_p_insc": set(),
                    "_users_o_insc": set(),
                    "_users_p_pres": set(),
                    "_users_o_pres": set(),
                    "_users_all_pres": set(),
                }
            cidades_map[chave]["_users_all"].add(uid)
            if is_p:
                cidades_map[chave]["_users_p_insc"].add(uid)
            if is_o:
                cidades_map[chave]["_users_o_insc"].add(uid)
            if pres_p:
                cidades_map[chave]["_users_p_pres"].add(uid)
            if pres_o:
                cidades_map[chave]["_users_o_pres"].add(uid)
            if pres_any:
                cidades_map[chave]["_users_all_pres"].add(uid)

        frequencia_cidade_dados = []
        for d in cidades_map.values():
            tot_insc = len(d["_users_all"])
            pres_p = len(d["_users_p_pres"])
            pres_o = len(d["_users_o_pres"])
            pres_tot = len(d["_users_all_pres"])
            aus_p = len(d["_users_p_insc"] - d["_users_p_pres"])
            aus_o = len(d["_users_o_insc"] - d["_users_o_pres"])
            aus_tot = len(d["_users_all"] - d["_users_all_pres"])
            tx_p = round(pres_tot / tot_insc * 100, 1) if tot_insc else 0.0
            tx_a = round(aus_tot / tot_insc * 100, 1) if tot_insc else 0.0
            frequencia_cidade_dados.append({
                "label": d["label"],
                "sigla": d["sigla"],
                "total_inscritos": tot_insc,
                "presencial": pres_p,
                "online": pres_o,
                "qtd": pres_tot,
                "presencial_ausentes": aus_p,
                "online_ausentes": aus_o,
                "total_ausentes": aus_tot,
                "taxa_presenca": tx_p,
                "taxa_ausencia": tx_a,
            })
        frequencia_cidade_dados.sort(key=lambda x: x["qtd"], reverse=True)

        # 3. Presença e Ausência por Sala (Presencial)
        salas_presenciais_qs = ProgramacaoSala.objects.filter(modalidade="presencial")
        if atividade_selecionada:
            salas_presenciais_qs = salas_presenciais_qs.filter(atividades=atividade_selecionada)
        else:
            salas_presenciais_qs = salas_presenciais_qs.filter(atividades__isnull=False).distinct()
        salas_presenciais_qs = salas_presenciais_qs.select_related("sala")

        salas_p_map = {}
        for prog in salas_presenciais_qs:
            s_nome = prog.sala.nome
            if s_nome not in salas_p_map:
                salas_p_map[s_nome] = {
                    "label": s_nome,
                    "vagas": 0,
                    "_users_inscritos": set(),
                    "_users_presentes": set(),
                }
            salas_p_map[s_nome]["vagas"] += prog.quantidade_max_participantes
            salas_p_map[s_nome]["_users_inscritos"].update(
                prog.inscricoes.values_list("usuario_id", flat=True)
            )

        freq_presencial_qs = Frequencia.objects.filter(programacao__in=salas_presenciais_qs).select_related(
            "programacao__sala", "inscricao"
        )
        if atividade_selecionada:
            freq_presencial_qs = freq_presencial_qs.filter(inscricao__atividade=atividade_selecionada)

        for f in freq_presencial_qs:
            s_nome = f.programacao.sala.nome
            if s_nome in salas_p_map:
                salas_p_map[s_nome]["_users_presentes"].add(f.inscricao.usuario_id)

        frequencia_sala_presencial_dados = []
        for s_nome, d in salas_p_map.items():
            insc = len(d["_users_inscritos"])
            pres = len(d["_users_presentes"])
            aus = max(0, insc - pres)
            tx_p = round(pres / insc * 100, 1) if insc else 0.0
            tx_a = round(aus / insc * 100, 1) if insc else 0.0
            frequencia_sala_presencial_dados.append({
                "label": s_nome,
                "vagas": d["vagas"],
                "inscritos": insc,
                "qtd": pres,
                "presentes": pres,
                "ausentes": aus,
                "taxa_presenca": tx_p,
                "taxa_ausencia": tx_a,
            })
        frequencia_sala_presencial_dados.sort(key=lambda x: x["qtd"], reverse=True)

        # 4. Presença e Ausência por Sala (On-line)
        salas_online_qs = ProgramacaoSala.objects.filter(modalidade="online")
        if atividade_selecionada:
            salas_online_qs = salas_online_qs.filter(atividades=atividade_selecionada)
        else:
            salas_online_qs = salas_online_qs.filter(atividades__isnull=False).distinct()
        salas_online_qs = salas_online_qs.select_related("sala")

        salas_o_map = {}
        for prog in salas_online_qs:
            s_nome = prog.sala.nome
            if s_nome not in salas_o_map:
                salas_o_map[s_nome] = {
                    "label": s_nome,
                    "vagas": 0,
                    "_users_inscritos": set(),
                    "_users_presentes": set(),
                }
            salas_o_map[s_nome]["vagas"] += prog.quantidade_max_participantes
            salas_o_map[s_nome]["_users_inscritos"].update(
                prog.inscricoes.values_list("usuario_id", flat=True)
            )

        freq_online_qs = Frequencia.objects.filter(programacao__in=salas_online_qs).select_related(
            "programacao__sala", "inscricao"
        )
        if atividade_selecionada:
            freq_online_qs = freq_online_qs.filter(inscricao__atividade=atividade_selecionada)

        for f in freq_online_qs:
            s_nome = f.programacao.sala.nome
            if s_nome in salas_o_map:
                salas_o_map[s_nome]["_users_presentes"].add(f.inscricao.usuario_id)

        frequencia_sala_online_dados = []
        for s_nome, d in salas_o_map.items():
            insc = len(d["_users_inscritos"])
            pres = len(d["_users_presentes"])
            aus = max(0, insc - pres)
            tx_p = round(pres / insc * 100, 1) if insc else 0.0
            tx_a = round(aus / insc * 100, 1) if insc else 0.0
            frequencia_sala_online_dados.append({
                "label": s_nome,
                "vagas": d["vagas"],
                "inscritos": insc,
                "qtd": pres,
                "presentes": pres,
                "ausentes": aus,
                "taxa_presenca": tx_p,
                "taxa_ausencia": tx_a,
            })
        frequencia_sala_online_dados.sort(key=lambda x: x["qtd"], reverse=True)

        context.update(
            exibir_dashboard=exibir_dashboard,
            visao_geral=visao_geral,
            atividade_selecionada=atividade_selecionada_dict,
            atividades_catalogo=atividades_catalogo,
            programacoes_catalogo=programacoes_catalogo,
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
            frequencia_kpis=frequencia_kpis,
            frequencia_estado_dados=frequencia_estado_dados,
            frequencia_cidade_dados=frequencia_cidade_dados,
            frequencia_sala_presencial_dados=frequencia_sala_presencial_dados,
            frequencia_sala_online_dados=frequencia_sala_online_dados,
        )
        return context


# A URL importa uma função; ``as_view`` adapta a classe para esse contrato.
reports = ReportsView.as_view()


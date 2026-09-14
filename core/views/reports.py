from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.models import Educador, EducadorEscola


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


def dados_basicos_educador(educador):
    """Reúne os dados pessoais repetidos em cada vínculo do relatório detalhado."""
    usuario = educador.usuario
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
    }


def registro_participante(educador, vinculo=None):
    """Monta uma linha do relatório detalhado, com ou sem vínculo escolar."""
    registro = dados_basicos_educador(educador)
    if not vinculo:
        registro.update(
            municipio="Não informado",
            estado="Não informado",
            sigla_uf="",
            escola="Não informado",
            funcao="Não informado",
            tempo="Não informado",
        )
        return registro

    registro.update(
        municipio=vinculo.cidade.nome_cidade or "Não informado",
        estado=vinculo.cidade.estado.nome_estado or "Não informado",
        sigla_uf=vinculo.cidade.estado.sigla or "",
        escola=vinculo.escola.nome or "Não informado",
        funcao=vinculo.funcao.nome if vinculo.funcao else "Não informado",
        tempo=ROTULOS_TEMPO_ATUACAO.get(
            vinculo.tempo_atuacao,
            vinculo.tempo_atuacao or "Não informado",
        ),
    )
    return registro


def listar_participantes_detalhados():
    """Expande cada educador em uma linha por vínculo escolar cadastrado."""
    educadores = Educador.objects.select_related(
        "usuario", "genero", "cor_raca"
    ).prefetch_related(
        "funcoes__educador_escola__cidade__estado",
        "funcoes__educador_escola__escola",
        "funcoes__educador_escola__funcao",
    )
    participantes = []

    for educador in educadores:
        vinculos = [
            funcao_educador.educador_escola
            for funcao_educador in educador.funcoes.all()
        ]
        if not vinculos:
            participantes.append(registro_participante(educador))
            continue
        participantes.extend(
            registro_participante(educador, vinculo) for vinculo in vinculos
        )

    return participantes


@method_decorator(staff_required, name="dispatch")
class ReportsView(TemplateView):
    """Apresenta indicadores agregados e a relação detalhada de participantes."""

    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        """Executa as agregações e entrega estruturas prontas para tabelas e gráficos."""
        context = super().get_context_data(**kwargs)
        vinculos = EducadorEscola.objects.all()

        participantes_por_municipio = (
            vinculos.values(
                municipio=F("cidade__nome_cidade"),
                estado_sigla=F("cidade__estado__sigla"),
            )
            .annotate(qtd=Count("pk"))
            .order_by("-qtd")
        )
        participantes_por_escola = (
            vinculos.values(nome_escola=F("escola__nome"))
            .annotate(qtd=Count("pk"))
            .order_by("-qtd")
        )
        participantes_por_estado = (
            vinculos.values(
                estado=F("cidade__estado__nome_estado"),
                sigla=F("cidade__estado__sigla"),
            )
            .annotate(qtd=Count("pk"))
            .order_by("-qtd")
        )

        context.update(
            total_educadores=Educador.objects.count(),
            total_vinculos=vinculos.count(),
            total_escolas=vinculos.values("escola").distinct().count(),
            total_municipios=vinculos.values("cidade").distinct().count(),
            participantes_detalhados=listar_participantes_detalhados(),
            municipio_dados=normalizar_distribuicao(
                participantes_por_municipio,
                "municipio",
                campos_extras={"estado_sigla": "state"},
            ),
            escola_dados=normalizar_distribuicao(
                participantes_por_escola, "nome_escola"
            ),
            estado_dados=normalizar_distribuicao(
                participantes_por_estado,
                "estado",
                campos_extras={"sigla": "sigla"},
            ),
            genero_dados=normalizar_distribuicao(
                Educador.objects.values(nome_genero=F("genero__nome"))
                .annotate(qtd=Count("pk"))
                .order_by("-qtd"),
                "nome_genero",
            ),
            cor_dados=normalizar_distribuicao(
                Educador.objects.values(cor=F("cor_raca__nome"))
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
        )
        return context


# A URL importa uma função; ``as_view`` adapta a classe para esse contrato.
reports = ReportsView.as_view()

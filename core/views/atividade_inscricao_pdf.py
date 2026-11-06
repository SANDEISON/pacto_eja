from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import get_script_prefix, reverse
from django.utils.text import slugify

from ..models import Atividade
from ..services.atividade_inscricao_pdf import gerar_atividade_inscricao_pdf


def _atividade_para_divulgacao(request, pk):
    if not (request.user.has_perm("core.view_atividade") or request.user.has_perm("core.change_atividade")):
        raise PermissionDenied
    return get_object_or_404(Atividade, pk=pk)


def _url_divulgacao(rota, identificador):
    # The public base already includes the proxy prefix. Remove the script
    # prefix from reverse() so it cannot be duplicated in the shared URL.
    caminho = reverse(rota, args=[identificador])
    caminho = caminho.removeprefix(get_script_prefix())
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/{caminho}"


@login_required
def atividade_inscricao_pdf(request, pk):
    """Disponibiliza o material de inscrição a quem pode gerenciar atividades."""
    atividade = _atividade_para_divulgacao(request, pk)
    url = _url_divulgacao("atividade_inscricao", atividade.pk)
    return FileResponse(
        gerar_atividade_inscricao_pdf(atividade, url),
        as_attachment=True, filename=f"inscricao-{slugify(atividade.titulo) or f'atividade-{atividade.pk}'}.pdf",
        content_type="application/pdf",
    )


@login_required
def atividade_programacao_pdf(request, pk):
    """Disponibiliza o QR code para o download do anexo da programação."""
    atividade = _atividade_para_divulgacao(request, pk)
    if not atividade.arquivo_programacao:
        raise Http404
    url = _url_divulgacao("atividade_programacao_publica", atividade.token_programacao_publica)
    nome = slugify(atividade.titulo) or f"atividade-{atividade.pk}"
    return FileResponse(
        gerar_atividade_inscricao_pdf(atividade, url, programacao=True),
        as_attachment=True,
        filename=f"programacao-{nome}.pdf",
        content_type="application/pdf",
    )

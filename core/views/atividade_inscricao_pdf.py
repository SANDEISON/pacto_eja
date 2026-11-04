from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import get_script_prefix, reverse
from django.utils.text import slugify

from ..models import Atividade
from ..services.atividade_inscricao_pdf import gerar_atividade_inscricao_pdf


@login_required
def atividade_inscricao_pdf(request, pk):
    """Disponibiliza o material de inscrição a quem pode gerenciar atividades."""
    if not (request.user.has_perm("core.view_atividade") or request.user.has_perm("core.change_atividade")):
        raise PermissionDenied
    atividade = get_object_or_404(Atividade, pk=pk)
    # The public base already includes the proxy prefix. Remove the script
    # prefix from reverse() so it cannot be duplicated in the shared URL.
    caminho = reverse("atividade_inscricao", args=[atividade.pk])
    caminho = caminho.removeprefix(get_script_prefix())
    url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/{caminho}"
    return FileResponse(
        gerar_atividade_inscricao_pdf(atividade, url),
        as_attachment=True, filename=f"inscricao-{slugify(atividade.titulo) or f'atividade-{atividade.pk}'}.pdf",
        content_type="application/pdf",
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from accounts.constants import SENHA_INICIAL

from ..models import Educador


@login_required
@permission_required("core.change_educador", raise_exception=True)
@require_POST
def educator_password_reset(request, pk):
    """Redefine a senha da conta vinculada ao educador selecionado."""
    educador = get_object_or_404(Educador.objects.select_related("usuario"), pk=pk)
    usuario = educador.usuario
    if (usuario.is_staff or usuario.is_superuser) and not request.user.is_superuser:
        raise PermissionDenied

    usuario.set_password(SENHA_INICIAL)
    usuario.save(update_fields=("password",))
    messages.success(
        request,
        f"Senha de {educador} redefinida para {SENHA_INICIAL}. "
        "O educador deverá criar uma nova senha ao entrar.",
    )
    return redirect("educator_model_list")

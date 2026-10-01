from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin


class RequiredPasswordChangeMiddleware(MiddlewareMixin):
    """Mantém a sessão na troca de senha até que uma nova senha seja salva."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if (
            request.user.is_authenticated
            and request.session.get("alteracao_senha_obrigatoria")
            and request.resolver_match.view_name not in {
                "accounts:change_initial_password", "accounts:logout",
            }
        ):
            return redirect("accounts:change_initial_password")

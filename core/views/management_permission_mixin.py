from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class ManagementPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Exige login e devolve HTTP 403 quando falta a permissão administrativa."""
    raise_exception = True

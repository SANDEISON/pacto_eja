from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class ManagementPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True

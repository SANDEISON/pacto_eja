from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from .management_permission_mixin import ManagementPermissionMixin


class UserDeleteView(ManagementPermissionMixin, DeleteView):
    """Exclui contas sem permitir ações administrativas inseguras."""
    model = get_user_model()
    permission_required = "auth.delete_user"
    template_name = "management/confirm_delete.html"
    success_url = reverse_lazy("user_list")
    extra_context = {"object_label": "usuário", "cancel_url_name": "user_list"}

    def get_object(self, queryset=None):
        """Impede autoexclusão e protege superusuários de operadores comuns."""
        usuario = super().get_object(queryset)
        if usuario == self.request.user or (
            usuario.is_superuser and not self.request.user.is_superuser
        ):
            raise PermissionDenied
        return usuario

    def form_valid(self, form):
        """Confirma a exclusão da conta."""
        messages.success(self.request, "Usuário excluído com sucesso.")
        return super().form_valid(form)

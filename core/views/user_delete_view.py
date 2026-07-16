from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from .management_permission_mixin import ManagementPermissionMixin


class UserDeleteView(ManagementPermissionMixin, DeleteView):
    model = get_user_model()
    permission_required = "auth.delete_user"
    template_name = "management/confirm_delete.html"
    success_url = reverse_lazy("user_list")
    extra_context = {"object_label": "usuário", "cancel_url_name": "user_list"}

    def get_object(self, queryset=None):
        user = super().get_object(queryset)
        if user == self.request.user or (user.is_superuser and not self.request.user.is_superuser):
            raise PermissionDenied
        return user

    def form_valid(self, form):
        messages.success(self.request, "Usuário excluído com sucesso.")
        return super().form_valid(form)

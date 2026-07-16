from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from ..forms import ManagedUserForm
from .management_permission_mixin import ManagementPermissionMixin


class UserUpdateView(ManagementPermissionMixin, UpdateView):
    model = get_user_model()
    permission_required = "auth.change_user"
    form_class = ManagedUserForm
    template_name = "management/user_form.html"
    success_url = reverse_lazy("user_list")

    def get_object(self, queryset=None):
        user = super().get_object(queryset)
        if user.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied
        return user

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado com sucesso.")
        return super().form_valid(form)

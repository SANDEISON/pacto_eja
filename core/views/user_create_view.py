from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic import CreateView

from ..forms import ManagedUserForm
from .management_permission_mixin import ManagementPermissionMixin


class UserCreateView(ManagementPermissionMixin, CreateView):
    model = get_user_model()
    permission_required = "auth.add_user"
    form_class = ManagedUserForm
    template_name = "management/user_form.html"
    success_url = reverse_lazy("user_list")

    def form_valid(self, form):
        messages.success(self.request, "Usuário cadastrado com sucesso.")
        return super().form_valid(form)

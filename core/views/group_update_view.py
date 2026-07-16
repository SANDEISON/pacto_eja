from django.contrib import messages
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from ..forms import ManagedGroupForm
from .management_permission_mixin import ManagementPermissionMixin


class GroupUpdateView(ManagementPermissionMixin, UpdateView):
    model = Group
    permission_required = "auth.change_group"
    form_class = ManagedGroupForm
    template_name = "management/group_form.html"
    success_url = reverse_lazy("group_list")

    def form_valid(self, form):
        messages.success(self.request, "Grupo atualizado com sucesso.")
        return super().form_valid(form)

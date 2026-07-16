from django.contrib import messages
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.views.generic import CreateView

from ..forms import ManagedGroupForm
from .management_permission_mixin import ManagementPermissionMixin


class GroupCreateView(ManagementPermissionMixin, CreateView):
    model = Group
    permission_required = "auth.add_group"
    form_class = ManagedGroupForm
    template_name = "management/group_form.html"
    success_url = reverse_lazy("group_list")

    def form_valid(self, form):
        messages.success(self.request, "Grupo cadastrado com sucesso.")
        return super().form_valid(form)

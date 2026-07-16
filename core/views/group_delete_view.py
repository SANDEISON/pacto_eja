from django.contrib import messages
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from .management_permission_mixin import ManagementPermissionMixin


class GroupDeleteView(ManagementPermissionMixin, DeleteView):
    model = Group
    permission_required = "auth.delete_group"
    template_name = "management/confirm_delete.html"
    success_url = reverse_lazy("group_list")
    extra_context = {"object_label": "grupo", "cancel_url_name": "group_list"}

    def form_valid(self, form):
        messages.success(self.request, "Grupo excluído com sucesso.")
        return super().form_valid(form)

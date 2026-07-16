from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from ..models import CadastroEducador
from .management_permission_mixin import ManagementPermissionMixin


class EducatorDeleteView(ManagementPermissionMixin, DeleteView):
    model = CadastroEducador
    permission_required = "core.delete_cadastroeducador"
    template_name = "management/confirm_delete.html"
    success_url = reverse_lazy("educator_list")
    extra_context = {"object_label": "cadastro de educador", "cancel_url_name": "educator_list"}

    def form_valid(self, form):
        messages.success(self.request, "Cadastro do educador excluído com sucesso.")
        return super().form_valid(form)

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from ..forms import ManagedCadastroEducadorForm
from ..models import CadastroEducador
from .management_permission_mixin import ManagementPermissionMixin


class EducatorUpdateView(ManagementPermissionMixin, UpdateView):
    model = CadastroEducador
    permission_required = "core.change_cadastroeducador"
    form_class = ManagedCadastroEducadorForm
    template_name = "management/educator_form.html"
    success_url = reverse_lazy("educator_list")

    def form_valid(self, form):
        messages.success(self.request, "Cadastro do educador atualizado com sucesso.")
        return super().form_valid(form)

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView

from ..forms import ManagedCadastroEducadorForm
from ..models import CadastroEducador
from .management_permission_mixin import ManagementPermissionMixin


class EducatorCreateView(ManagementPermissionMixin, CreateView):
    model = CadastroEducador
    permission_required = "core.add_cadastroeducador"
    form_class = ManagedCadastroEducadorForm
    template_name = "management/educator_form.html"
    success_url = reverse_lazy("educator_list")

    def form_valid(self, form):
        messages.success(self.request, "Educador cadastrado com sucesso.")
        return super().form_valid(form)

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from ..forms import EducadorEscolaForm
from ..models import EducadorEscola
from .management_permission_mixin import ManagementPermissionMixin


class EducatorUpdateView(ManagementPermissionMixin, UpdateView):
    model = EducadorEscola
    permission_required = "core.change_educadorescola"
    form_class = EducadorEscolaForm
    template_name = "management/educator_form.html"
    success_url = reverse_lazy("educator_list")

    def form_valid(self, form):
        messages.success(self.request, "Cadastro do educador atualizado com sucesso.")
        return super().form_valid(form)

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView

from ..forms import EducadorEscolaForm
from ..models import EducadorEscola
from .management_permission_mixin import ManagementPermissionMixin


class EducatorCreateView(ManagementPermissionMixin, CreateView):
    """Cadastra um novo vínculo entre educador, escola e função."""
    model = EducadorEscola
    permission_required = "core.add_educadorescola"
    form_class = EducadorEscolaForm
    template_name = "management/educator_form.html"
    success_url = reverse_lazy("educator_list")

    def form_valid(self, form):
        """Confirma a criação depois que o formulário foi validado."""
        messages.success(self.request, "Educador cadastrado com sucesso.")
        return super().form_valid(form)

from django.views.generic import ListView

from ..models import EducadorEscola
from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


class EducatorListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = EducadorEscola
    permission_required = "core.view_educadorescola"
    template_name = "management/educator_list.html"
    context_object_name = "educators"
    search_fields = (
        "funcao_educador__educador__cpf",
        "funcao_educador__educador__nome_completo",
        "funcao_educador__educador__usuario__first_name",
        "funcao_educador__educador__usuario__last_name",
        "funcao_educador__educador__usuario__email",
        "cidade__nome_cidade",
        "escola__nome",
    )

    def get_queryset(self):
        return super().get_queryset().select_related(
            "funcao_educador__educador__usuario",
            "cidade__estado",
            "escola",
        )

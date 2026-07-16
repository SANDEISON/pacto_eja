from django.views.generic import ListView

from ..models import CadastroEducador
from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


class EducatorListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = CadastroEducador
    permission_required = "core.view_cadastroeducador"
    template_name = "management/educator_list.html"
    context_object_name = "educators"
    search_fields = (
        "id_pessoa__cpf",
        "id_pessoa__usuario__first_name",
        "id_pessoa__usuario__last_name",
        "id_pessoa__usuario__email",
        "cidade__nome_cidade",
        "escola__nome",
    )

    def get_queryset(self):
        return super().get_queryset().select_related(
            "id_pessoa__usuario",
            "estado",
            "cidade",
            "escola",
        )

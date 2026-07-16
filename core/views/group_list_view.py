from django.contrib.auth.models import Group
from django.views.generic import ListView

from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


class GroupListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = Group
    permission_required = "auth.view_group"
    template_name = "management/group_list.html"
    context_object_name = "groups"
    search_fields = ("name",)

    def get_queryset(self):
        return super().get_queryset().prefetch_related("permissions").order_by("name")

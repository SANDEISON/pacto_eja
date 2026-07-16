from django.contrib.auth import get_user_model
from django.views.generic import ListView

from .management_permission_mixin import ManagementPermissionMixin
from .searchable_list_mixin import SearchableListMixin


class UserListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = get_user_model()
    permission_required = "auth.view_user"
    template_name = "management/user_list.html"
    context_object_name = "users"
    search_fields = ("username", "first_name", "last_name", "email")

    def get_queryset(self):
        return super().get_queryset().prefetch_related("groups").order_by("username")

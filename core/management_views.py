from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ManagedGroupForm, ManagedUserForm


class ManagementPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True


class SearchableListMixin:
    paginate_by = 20
    search_fields = ()

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query:
            filters = Q()
            for field in self.search_fields:
                filters |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        return context


class UserListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = get_user_model()
    permission_required = "auth.view_user"
    template_name = "management/user_list.html"
    context_object_name = "users"
    search_fields = ("username", "first_name", "last_name", "email")

    def get_queryset(self):
        return super().get_queryset().prefetch_related("groups").order_by("username")


class UserCreateView(ManagementPermissionMixin, CreateView):
    model = get_user_model()
    permission_required = "auth.add_user"
    form_class = ManagedUserForm
    template_name = "management/user_form.html"
    success_url = reverse_lazy("user_list")

    def form_valid(self, form):
        messages.success(self.request, "Usuário cadastrado com sucesso.")
        return super().form_valid(form)


class UserUpdateView(ManagementPermissionMixin, UpdateView):
    model = get_user_model()
    permission_required = "auth.change_user"
    form_class = ManagedUserForm
    template_name = "management/user_form.html"
    success_url = reverse_lazy("user_list")

    def get_object(self, queryset=None):
        user = super().get_object(queryset)
        if user.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied
        return user

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado com sucesso.")
        return super().form_valid(form)


class UserDeleteView(ManagementPermissionMixin, DeleteView):
    model = get_user_model()
    permission_required = "auth.delete_user"
    template_name = "management/confirm_delete.html"
    success_url = reverse_lazy("user_list")
    extra_context = {"object_label": "usuário", "cancel_url_name": "user_list"}

    def get_object(self, queryset=None):
        user = super().get_object(queryset)
        if user == self.request.user or (user.is_superuser and not self.request.user.is_superuser):
            raise PermissionDenied
        return user

    def form_valid(self, form):
        messages.success(self.request, "Usuário excluído com sucesso.")
        return super().form_valid(form)


class GroupListView(ManagementPermissionMixin, SearchableListMixin, ListView):
    model = Group
    permission_required = "auth.view_group"
    template_name = "management/group_list.html"
    context_object_name = "groups"
    search_fields = ("name",)

    def get_queryset(self):
        return super().get_queryset().prefetch_related("permissions").order_by("name")


class GroupCreateView(ManagementPermissionMixin, CreateView):
    model = Group
    permission_required = "auth.add_group"
    form_class = ManagedGroupForm
    template_name = "management/group_form.html"
    success_url = reverse_lazy("group_list")

    def form_valid(self, form):
        messages.success(self.request, "Grupo cadastrado com sucesso.")
        return super().form_valid(form)


class GroupUpdateView(ManagementPermissionMixin, UpdateView):
    model = Group
    permission_required = "auth.change_group"
    form_class = ManagedGroupForm
    template_name = "management/group_form.html"
    success_url = reverse_lazy("group_list")

    def form_valid(self, form):
        messages.success(self.request, "Grupo atualizado com sucesso.")
        return super().form_valid(form)


class GroupDeleteView(ManagementPermissionMixin, DeleteView):
    model = Group
    permission_required = "auth.delete_group"
    template_name = "management/confirm_delete.html"
    success_url = reverse_lazy("group_list")
    extra_context = {"object_label": "grupo", "cancel_url_name": "group_list"}

    def form_valid(self, form):
        messages.success(self.request, "Grupo excluído com sucesso.")
        return super().form_valid(form)

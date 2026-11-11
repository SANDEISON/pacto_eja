from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User


class SuperuserAuthWritesMixin:
    """Mantém as alterações do Django Admin reservadas a superusuários."""

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


class ProtectedUserAdmin(SuperuserAuthWritesMixin, UserAdmin):
    pass


class ProtectedGroupAdmin(SuperuserAuthWritesMixin, GroupAdmin):
    pass


admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, ProtectedUserAdmin)
admin.site.register(Group, ProtectedGroupAdmin)

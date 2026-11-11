from django.contrib.auth.models import Group


def can_change_educator_groups(actor, target):
    return actor.has_perms(("core.change_educador", "auth.change_user")) and (
        actor.is_superuser or not (target.is_staff or target.is_superuser)
    )


def can_reset_educator_password(actor, target):
    return actor.is_superuser or not (
        target.is_staff
        or target.is_superuser
        or target.has_perm("auth.change_user")
        or target.has_perm("core.view_relatorios")
    )


def default_educator_group():
    """Só atribui automaticamente o perfil se ele continuar sem permissões administrativas."""
    return Group.objects.filter(name="Educador", permissions__isnull=True)

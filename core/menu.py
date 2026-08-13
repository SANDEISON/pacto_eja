def staff_only(request):
    """Exibe o item de menu apenas para usuários da equipe administrativa."""
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


def educator_management_access(request):
    """Exibe Educadores somente para a equipe com acesso aos cadastros."""
    user = getattr(request, "user", None)
    return bool(
        user
        and user.is_authenticated
        and user.is_staff
        and user.has_perm("core.view_educadorescola")
    )


def management_access(request):
    """Exibe a seção quando o usuário pode consultar usuários ou grupos."""
    user = getattr(request, "user", None)
    return bool(
        user
        and user.is_authenticated
        and user.is_staff
        and (user.has_perm("auth.view_user") or user.has_perm("auth.view_group"))
    )

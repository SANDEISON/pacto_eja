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
    """Exibe a seção quando o usuário pode consultar algum cadastro administrativo."""
    user = getattr(request, "user", None)
    return bool(
        user
        and user.is_authenticated
        and user.is_staff
        and any(
            user.has_perm(permission)
            for permission in (
                "core.view_cidade",
                "core.view_corraca",
                "core.view_educador",
                "core.view_educadorgenero",
                "core.change_educadorgenero",
                "core.view_escola",
                "core.view_estado",
                "core.view_nivel",
                "core.view_modalidade",
                "core.view_situacao",
            )
        )
    )

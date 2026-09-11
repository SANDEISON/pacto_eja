from django.db import models


def staff_only(request):
    """Exibe o item de menu apenas para usuários da equipe administrativa."""
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


def activity_management_access(request):
    """Exibe atividades para a equipe que pode consultá-las ou alterá-las."""
    user = getattr(request, "user", None)
    return bool(
        user
        and user.is_authenticated
        and user.is_staff
        and (user.has_perm("core.view_atividade") or user.has_perm("core.change_atividade"))
    )


def educator_management_access(request):
    """Exibe Educadores somente para a equipe com acesso aos cadastros."""
    user = getattr(request, "user", None)
    return bool(
        user
        and user.is_authenticated
        and user.is_staff
        and user.has_perm("core.view_educadorescola")
    )


def evaluator_portal_access(request):
    """Exibe o espaço de avaliação quando o usuário recebeu ao menos um trabalho."""
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.designacoes_avaliacao.exists())


def evaluator_opportunities_access(request):
    """Exibe chamadas quando existe uma oportunidade publicada ou candidatura própria."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    from django.utils import timezone

    from .models import ChamadaAvaliadores

    return ChamadaAvaliadores.objects.filter(ativa=True).filter(
        models.Q(inscricoes_fim__gte=timezone.now()) | models.Q(candidaturas__usuario=user)
    ).exists()


def evaluator_section_access(request):
    """Mantém a seção oculta quando não há nenhuma ação de avaliação disponível."""
    return evaluator_opportunities_access(request) or evaluator_portal_access(request)


def review_management_access(request):
    """Exibe a gestão das chamadas conforme as permissões atribuídas ao grupo."""
    user = getattr(request, "user", None)
    return bool(
        user
        and user.is_authenticated
        and user.is_staff
        and any(
            user.has_perm(permission)
            for permission in (
                "core.view_chamadaavaliadores",
                "core.change_chamadaavaliadores",
                "core.view_candidaturaavaliador",
                "core.view_designacaoavaliacao",
            )
        )
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

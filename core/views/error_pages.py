from django.shortcuts import render


ERROR_MESSAGES = {
    400: ("Solicitação inválida", "Não foi possível entender a solicitação enviada."),
    401: ("Autenticação necessária", "Entre com sua conta para acessar este conteúdo."),
    403: ("Acesso negado", "Você não tem permissão para acessar esta página."),
    404: ("Página não encontrada", "A página que você procura não existe ou foi movida."),
    500: ("Erro interno", "Ocorreu um problema inesperado. Nossa equipe pode tentar novamente em instantes."),
    503: ("Serviço indisponível", "O serviço está temporariamente indisponível. Tente novamente em alguns minutos."),
}


def error_page(request, status_code, exception=None):
    """Renderiza uma página de erro uniforme para o código HTTP informado."""
    titulo, mensagem = ERROR_MESSAGES.get(
        status_code,
        ("Algo não saiu como esperado", "Tente novamente em instantes."),
    )
    return render(
        request,
        "errors/error.html",
        {
            "status_code": status_code,
            "error_title": titulo,
            "error_message": mensagem,
        },
        status=status_code,
    )


def error_400(request, exception):
    """Trata solicitações inválidas."""
    return error_page(request, 400, exception)


def error_403(request, exception):
    """Trata tentativas de acesso sem permissão."""
    return error_page(request, 403, exception)


def error_404(request, exception):
    """Trata endereços que não correspondem a uma página."""
    return error_page(request, 404, exception)


def error_500(request):
    """Trata falhas internas não capturadas pela aplicação."""
    return error_page(request, 500)


def error_preview(request, status_code):
    """Permite à equipe visualizar o layout de cada erro conhecido."""
    if status_code not in ERROR_MESSAGES:
        status_code = 404
    return error_page(request, status_code)

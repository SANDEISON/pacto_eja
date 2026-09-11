from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def cadastro_educador_success(request):
    """Confirma a conclusão do cadastro público do educador."""
    return render(request, "cadastro_educadores/success.html")

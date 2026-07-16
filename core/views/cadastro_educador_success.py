from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def cadastro_educador_success(request):
    return render(request, "cadastro_educadores/success.html")

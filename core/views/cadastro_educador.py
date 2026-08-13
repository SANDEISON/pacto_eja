from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..forms import EducadorEscolaCadastroForm


@require_http_methods(["GET", "POST"])
def cadastro_educador(request):
    form = EducadorEscolaCadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save_cadastro()
        except IntegrityError:
            form.add_error(None, "Não foi possível concluir o cadastro. Verifique se os dados já estão em uso.")
        else:
            return redirect("cadastro_educador_success")
    return render(request, "cadastro_educadores/form.html", {"form": form})

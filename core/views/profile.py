from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from ..forms import EducadorForm, EnderecoForm, ProfileUserForm
from ..models import Educador, Endereco


@login_required
@transaction.atomic
def profile(request):
    educador, _ = Educador.objects.get_or_create(usuario=request.user)
    endereco = Endereco.objects.filter(educador=educador).first() or Endereco(educador=educador)
    user_form = ProfileUserForm(request.POST or None, instance=request.user, prefix="user")
    educador_form = EducadorForm(request.POST or None, instance=educador, prefix="educador")
    endereco_data = request.POST if request.method == "POST" and any(
        key.startswith("endereco-") for key in request.POST
    ) else None
    endereco_form = EnderecoForm(endereco_data, instance=endereco, prefix="endereco")
    endereco_valido = not endereco_form.is_bound or endereco_form.is_valid()
    if request.method == "POST" and user_form.is_valid() and educador_form.is_valid() and endereco_valido:
        usuario = user_form.save()
        educador = educador_form.save(commit=False)
        educador.nome_completo = usuario.get_full_name()
        educador.save()
        if endereco_form.is_bound and endereco_form.has_changed():
            endereco = endereco_form.save(commit=False)
            endereco.educador = educador
            endereco.save()
        messages.success(request, "Seu perfil foi atualizado com sucesso.")
        return redirect("profile")
    return render(
        request,
        "profile/profile.html",
        {
            "user_form": user_form,
            "educador_form": educador_form,
            "endereco_form": endereco_form,
        },
    )

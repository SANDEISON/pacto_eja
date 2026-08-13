from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from ..forms import EducadorForm, ProfileUserForm
from ..models import Educador


@login_required
@transaction.atomic
def profile(request):
    educador, _ = Educador.objects.get_or_create(usuario=request.user)
    user_form = ProfileUserForm(request.POST or None, instance=request.user, prefix="user")
    educador_form = EducadorForm(request.POST or None, instance=educador, prefix="educador")
    if request.method == "POST" and user_form.is_valid() and educador_form.is_valid():
        usuario = user_form.save()
        educador = educador_form.save(commit=False)
        educador.nome_completo = usuario.get_full_name()
        educador.save()
        messages.success(request, "Seu perfil foi atualizado com sucesso.")
        return redirect("profile")
    return render(request, "profile/profile.html", {"user_form": user_form, "educador_form": educador_form})

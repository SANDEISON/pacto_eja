from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from ..forms import PessoaForm, ProfileUserForm
from ..models import Pessoa


@login_required
@transaction.atomic
def profile(request):
    pessoa, _ = Pessoa.objects.get_or_create(usuario=request.user)
    user_form = ProfileUserForm(request.POST or None, instance=request.user, prefix="user")
    pessoa_form = PessoaForm(request.POST or None, instance=pessoa, prefix="pessoa")
    if request.method == "POST" and user_form.is_valid() and pessoa_form.is_valid():
        user_form.save()
        pessoa_form.save()
        messages.success(request, "Seu perfil foi atualizado com sucesso.")
        return redirect("profile")
    return render(request, "profile/profile.html", {"user_form": user_form, "pessoa_form": pessoa_form})

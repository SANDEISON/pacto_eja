from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from ..forms import (
    EducadorForm,
    EnderecoForm,
    FormacaoFormSet,
    FormacaoFormSetWithExtra,
    ProfileUserForm,
)
from ..models import Educador, Endereco


@login_required
@transaction.atomic
def profile(request):
    educador, _ = Educador.objects.get_or_create(usuario=request.user)
    adicionando_formacao = request.GET.get("adicionar_formacao") == "1" or (
        request.method == "POST" and request.POST.get("adicionar_formacao") == "1"
    )
    endereco = Endereco.objects.filter(educador=educador).first() or Endereco(educador=educador)
    user_form = ProfileUserForm(request.POST or None, instance=request.user, prefix="user")
    educador_form = EducadorForm(request.POST or None, instance=educador, prefix="educador")
    endereco_data = request.POST if request.method == "POST" and any(
        key.startswith("endereco-") for key in request.POST
    ) else None
    endereco_form = EnderecoForm(endereco_data, instance=endereco, prefix="endereco")
    formacao_data = None
    if request.method == "POST" and "formacao-TOTAL_FORMS" in request.POST:
        formacao_data = request.POST.copy()
        if adicionando_formacao:
            try:
                total_formacoes = int(formacao_data["formacao-TOTAL_FORMS"])
            except (KeyError, TypeError, ValueError):
                total_formacoes = 0
            formacao_data["formacao-TOTAL_FORMS"] = str(total_formacoes + 1)
    formset_class = (
        FormacaoFormSetWithExtra
        if adicionando_formacao and request.method == "GET"
        else FormacaoFormSet
    )
    formacao_formset = formset_class(formacao_data, instance=educador, prefix="formacao")
    endereco_valido = not endereco_form.is_bound or endereco_form.is_valid()
    formacoes_validas = not formacao_formset.is_bound or formacao_formset.is_valid()
    if (
        request.method == "POST"
        and not adicionando_formacao
        and user_form.is_valid()
        and educador_form.is_valid()
        and endereco_valido
        and formacoes_validas
    ):
        usuario = user_form.save()
        educador = educador_form.save(commit=False)
        educador.nome_completo = usuario.get_full_name()
        educador.save()
        if endereco_form.is_bound and endereco_form.has_changed():
            endereco = endereco_form.save(commit=False)
            endereco.educador = educador
            endereco.save()
        if formacao_formset.is_bound:
            formacao_formset.save()
        messages.success(request, "Seu perfil foi atualizado com sucesso.")
        return redirect("profile")
    active_profile_tab = "education" if adicionando_formacao or (
        formacao_formset.is_bound and not formacoes_validas
    ) else "personal"
    return render(
        request,
        "profile/profile.html",
        {
            "active_profile_tab": active_profile_tab,
            "user_form": user_form,
            "educador_form": educador_form,
            "endereco_form": endereco_form,
            "formacao_formset": formacao_formset,
        },
    )

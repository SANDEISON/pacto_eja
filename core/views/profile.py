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
    """Exibe e atualiza dados pessoais, endereço e formações do usuário atual."""
    educador, _ = Educador.objects.get_or_create(usuario=request.user)
    adicionando_formacao = request.GET.get("adicionar_formacao") == "1" or (
        request.method == "POST" and request.POST.get("adicionar_formacao") == "1"
    )
    endereco = Endereco.objects.filter(educador=educador).first() or Endereco(educador=educador)
    formulario_usuario = ProfileUserForm(request.POST or None, instance=request.user, prefix="user")
    formulario_educador = EducadorForm(request.POST or None, instance=educador, prefix="educador")
    endereco_data = request.POST if request.method == "POST" and any(
        key.startswith("endereco-") for key in request.POST
    ) else None
    formulario_endereco = EnderecoForm(endereco_data, instance=endereco, prefix="endereco")
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
    formulario_formacoes = formset_class(formacao_data, instance=educador, prefix="formacao")
    endereco_valido = not formulario_endereco.is_bound or formulario_endereco.is_valid()
    formacoes_validas = not formulario_formacoes.is_bound or formulario_formacoes.is_valid()
    if (
        request.method == "POST"
        and not adicionando_formacao
        and formulario_usuario.is_valid()
        and formulario_educador.is_valid()
        and endereco_valido
        and formacoes_validas
    ):
        usuario = formulario_usuario.save()
        educador = formulario_educador.save(commit=False)
        educador.nome_completo = usuario.get_full_name()
        educador.save()
        if formulario_endereco.is_bound and formulario_endereco.has_changed():
            endereco = formulario_endereco.save(commit=False)
            endereco.educador = educador
            endereco.save()
        if formulario_formacoes.is_bound:
            formulario_formacoes.save()
        messages.success(request, "Seu perfil foi atualizado com sucesso.")
        return redirect("profile")
    active_profile_tab = "education" if adicionando_formacao or (
        formulario_formacoes.is_bound and not formacoes_validas
    ) else "personal"
    return render(
        request,
        "profile/profile.html",
        {
            "active_profile_tab": active_profile_tab,
            # Estes nomes são o contrato existente com o template.
            "user_form": formulario_usuario,
            "educador_form": formulario_educador,
            "endereco_form": formulario_endereco,
            "formacao_formset": formulario_formacoes,
        },
    )

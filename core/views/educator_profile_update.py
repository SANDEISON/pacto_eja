from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import EducadorForm, EnderecoForm, FormacaoFormSetWithExtra, ProfileUserForm
from ..models import Educador, Endereco


@login_required
@permission_required("core.change_educador", raise_exception=True)
@transaction.atomic
def educator_profile_update(request, pk):
    educador = get_object_or_404(Educador.objects.select_related("usuario"), pk=pk)
    endereco = Endereco.objects.filter(educador=educador).first() or Endereco(educador=educador)

    user_form = ProfileUserForm(request.POST or None, instance=educador.usuario, prefix="user")
    educador_form = EducadorForm(request.POST or None, instance=educador, prefix="educador")
    endereco_form = EnderecoForm(request.POST or None, instance=endereco, prefix="endereco")
    formacao_formset = FormacaoFormSetWithExtra(
        request.POST or None,
        instance=educador,
        prefix="formacao",
    )

    if request.method == "POST" and all(
        (user_form.is_valid(), educador_form.is_valid(), endereco_form.is_valid(), formacao_formset.is_valid())
    ):
        usuario = user_form.save()
        educador = educador_form.save(commit=False)
        educador.nome_completo = usuario.get_full_name()
        educador.save()

        if endereco_form.has_changed():
            endereco = endereco_form.save(commit=False)
            endereco.educador = educador
            endereco.save()
        formacao_formset.save()

        messages.success(request, "Perfil do educador atualizado com sucesso.")
        return redirect("educator_model_list")

    return render(
        request,
        "management/educator_profile_form.html",
        {
            "educador": educador,
            "user_form": user_form,
            "educador_form": educador_form,
            "endereco_form": endereco_form,
            "formacao_formset": formacao_formset,
        },
    )

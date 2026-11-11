from django.contrib import messages
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import EducadorForm, EnderecoForm, FormacaoFormSetWithExtra, ProfileUserForm
from ..models import Educador, Endereco
from ..access_profiles import can_change_educator_groups, can_reset_educator_password, default_educator_group


class EducatorAccountForm(ProfileUserForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.order_by("name"),
        label="Perfis de acesso",
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )

    class Meta(ProfileUserForm.Meta):
        fields = (*ProfileUserForm.Meta.fields, "groups")

    def clean_groups(self):
        groups = self.cleaned_data["groups"]
        if not groups and not (self.instance.is_staff or self.instance.is_superuser):
            return default_educator_group()
        return groups


@login_required
@permission_required("core.change_educador", raise_exception=True)
@transaction.atomic
def educator_profile_update(request, pk):
    """Permite à equipe editar o perfil completo de outro educador."""
    educador = get_object_or_404(Educador.objects.select_related("usuario"), pk=pk)
    endereco = Endereco.objects.filter(educador=educador).first() or Endereco(educador=educador)

    usuario = educador.usuario
    if not request.user.has_perm("auth.change_user") and not can_reset_educator_password(request.user, usuario):
        raise PermissionDenied
    can_change_groups = can_change_educator_groups(request.user, usuario)
    user_form_class = EducatorAccountForm if can_change_groups else ProfileUserForm
    user_form = user_form_class(request.POST or None, instance=usuario, prefix="user")
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
        if can_change_groups and "groups" in user_form.changed_data:
            user_form.save_m2m()
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

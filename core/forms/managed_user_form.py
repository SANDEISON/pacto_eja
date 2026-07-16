from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .bootstrap_form_mixin import BootstrapFormMixin


class ManagedUserForm(BootstrapFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Na edição, deixe em branco para manter a senha atual.",
    )
    password2 = forms.CharField(
        label="Confirmação da senha",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "is_active", "is_staff", "groups")
        labels = {
            "username": "Usuário",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
            "is_active": "Ativo",
            "is_staff": "Acesso à administração",
            "groups": "Grupos",
        }
        widgets = {"groups": forms.SelectMultiple(attrs={"size": 8})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.order_by("name")
        if not self.instance.pk:
            self.fields["password1"].required = True
            self.fields["password2"].required = True
        self._apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "As senhas não coincidem.")
            elif password1:
                try:
                    validate_password(password1, self.instance)
                except ValidationError as error:
                    self.add_error("password1", error)
                else:
                    self.instance.set_password(password1)
        return cleaned_data

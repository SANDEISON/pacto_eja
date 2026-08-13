from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from core.validators import validate_cpf


User = get_user_model()


class CPFAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": True,
                "inputmode": "numeric",
                "placeholder": "000.000.000-00",
            }
        ),
    )

    def clean_username(self):
        cpf = "".join(character for character in self.cleaned_data["username"] if character.isdigit())
        validate_cpf(cpf)
        return cpf


class SignUpForm(UserCreationForm):
    full_name = forms.CharField(label="Nome completo", max_length=150)
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "000.000.000-00"}),
    )
    email = forms.EmailField(label="E-mail")

    class Meta:
        model = User
        fields = ("full_name", "cpf", "email", "password1", "password2")

    def clean_cpf(self):
        cpf = "".join(character for character in self.cleaned_data["cpf"] if character.isdigit())
        validate_cpf(cpf)
        if User.objects.filter(username=cpf).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este CPF.")
        return cpf

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["full_name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        user.username = self.cleaned_data["cpf"]
        user.email = self.cleaned_data["email"]
        user.first_name = first_name
        user.last_name = last_name
        if commit:
            user.save()
            educador = user.educador
            educador.cpf = self.cleaned_data["cpf"]
            educador.nome_completo = full_name
            educador.save(update_fields=("cpf", "nome_completo"))
        return user

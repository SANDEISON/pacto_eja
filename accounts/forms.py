from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from core.validators import somente_digitos, validate_cpf


User = get_user_model()


class CPFAuthenticationForm(AuthenticationForm):
    """Autentica usando o CPF normalizado como nome de usuário do Django."""
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
        """Retira a máscara antes de consultar o usuário no banco."""
        cpf = somente_digitos(self.cleaned_data["username"])
        validate_cpf(cpf)
        return cpf


class PasswordRecoveryForm(forms.Form):
    """Solicita somente o CPF, sem revelar se ele pertence a uma conta."""

    cpf = forms.CharField(
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

    def clean_cpf(self):
        """Retira a máscara e rejeita números de CPF estruturalmente inválidos."""
        cpf = somente_digitos(self.cleaned_data["cpf"])
        validate_cpf(cpf)
        return cpf


class SignUpForm(UserCreationForm):
    """Cria, em uma única operação, a conta e o perfil de educador associado."""
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
        """Normaliza o CPF e garante que ele ainda não identifica outra conta."""
        cpf = somente_digitos(self.cleaned_data["cpf"])
        validate_cpf(cpf)
        if User.objects.filter(username=cpf).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este CPF.")
        return cpf

    def clean_email(self):
        """Padroniza o e-mail e impede duplicidade sem diferenciar maiúsculas."""
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    def save(self, commit=True):
        """Persiste a conta e sincroniza os dados básicos do perfil criado pelo signal."""
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

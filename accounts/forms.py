from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.db import transaction

from core.validators import somente_digitos, validate_cpf

from .constants import SENHA_INICIAL


User = get_user_model()


class FirstAccessPasswordForm(SetPasswordForm):
    """Valida a nova senha e impede a reutilização da senha inicial."""

    def clean_new_password1(self):
        password = self.cleaned_data["new_password1"]
        if password == SENHA_INICIAL:
            raise forms.ValidationError("Escolha uma senha diferente da senha inicial.")
        return password


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
    """Cria uma conta ou define a senha de uma conta que nunca fez login."""
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_encontrado = None

    def clean_cpf(self):
        """Reaproveita a conta do CPF somente antes do primeiro login."""
        cpf = somente_digitos(self.cleaned_data["cpf"])
        validate_cpf(cpf)
        usuario = User.objects.filter(username=cpf).first()
        if usuario is None:
            usuario = User.objects.filter(educador__cpf=cpf).first()
        if usuario:
            if usuario.last_login is not None or not usuario.is_active:
                raise forms.ValidationError(
                    "Já existe uma conta cadastrada com este CPF. Use a recuperação de senha para acessar."
                )
            self.usuario_encontrado = usuario
            self.instance = usuario
        return cpf

    def clean_email(self):
        """Padroniza o e-mail e impede duplicidade sem diferenciar maiúsculas."""
        email = self.cleaned_data["email"].strip().lower()
        usuarios = User.objects.filter(email__iexact=email)
        if self.usuario_encontrado:
            usuarios = usuarios.exclude(pk=self.usuario_encontrado.pk)
        if usuarios.exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        """Persiste a conta e sincroniza os dados básicos do perfil criado pelo signal."""
        if self.usuario_encontrado:
            usuario = User.objects.select_for_update().get(pk=self.usuario_encontrado.pk)
            if usuario.last_login is not None or not usuario.is_active:
                raise forms.ValidationError(
                    "Esta conta não pode mais ser concluída pelo cadastro. Use a recuperação de senha para acessar."
                )
            # A validação do ModelForm pode alterar a instância em memória;
            # recarregá-la preserva os dados da conta já existente.
            self.instance = usuario
            user = super().save(commit=False)
            user.username = self.cleaned_data["cpf"]
            if commit:
                User.objects.filter(pk=user.pk).update(password=user.password, username=user.username)
            return user
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

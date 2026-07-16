from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import CadastroEducador, Cidade, Escola, Estado, Pessoa
from ..validators import validate_cpf
from .bootstrap_form_mixin import BootstrapFormMixin


User = get_user_model()


class CadastroEducadorForm(BootstrapFormMixin, forms.ModelForm):
    nome_completo = forms.CharField(label="Nome completo", max_length=150, required=False)
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "000.000.000-00",
            }
        ),
    )
    email = forms.EmailField(label="E-mail", required=False, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    estado = forms.ModelChoiceField(
        label="Estado",
        queryset=Estado.objects.all(),
        empty_label="Selecione o estado",
    )
    cidade = forms.ModelChoiceField(
        label="Cidade de atuação",
        queryset=Cidade.objects.none(),
        empty_label="Selecione primeiro o estado",
    )
    escola = forms.ModelChoiceField(
        label="Escola",
        queryset=Escola.objects.none(),
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = CadastroEducador
        fields = (
            "estado",
            "cidade",
            "escola",
            "funcao_caracterizacao_turmas",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pessoa_encontrada = None

        estado_id = self.data.get("estado") if self.is_bound else self.initial.get("estado")
        if estado_id and str(estado_id).isdigit():
            self.fields["cidade"].queryset = Cidade.objects.filter(estado_id=estado_id)
            self.fields["cidade"].empty_label = "Selecione a cidade"

        cidade_id = self.data.get("cidade") if self.is_bound else self.initial.get("cidade")
        cidade = (
            Cidade.objects.filter(pk=cidade_id).select_related("estado").first()
            if cidade_id and str(cidade_id).isdigit()
            else None
        )
        if cidade and cidade.codigo_ibge:
            self.fields["escola"].queryset = Escola.objects.filter(
                id_municipio=cidade.codigo_ibge,
                sigla_uf=cidade.estado.sigla,
            )

        escola_id = self.data.get("escola") if self.is_bound else self.initial.get("escola")
        if escola_id and str(escola_id).isdigit():
            escola = Escola.objects.filter(pk=escola_id).first()
            if escola:
                self.fields["escola"].widget.attrs["data-selected-label"] = escola.nome

        self._apply_bootstrap_classes()

    def clean_cpf(self):
        cpf = "".join(character for character in self.cleaned_data["cpf"] if character.isdigit())
        validate_cpf(cpf)
        self.pessoa_encontrada = Pessoa.objects.select_related("usuario").filter(cpf=cpf).first()
        return cpf

    def clean(self):
        cleaned_data = super().clean()
        pessoa = self.pessoa_encontrada

        if pessoa:
            usuario = pessoa.usuario
            cleaned_data["nome_completo"] = usuario.get_full_name() or usuario.first_name or usuario.username
            cleaned_data["email"] = usuario.email or usuario.username
            if CadastroEducador.objects.filter(id_pessoa=pessoa).exists():
                self.add_error("cpf", "Esta pessoa já possui um cadastro de educador.")
        else:
            nome_completo = (cleaned_data.get("nome_completo") or "").strip()
            email = (cleaned_data.get("email") or "").strip().lower()
            if not nome_completo:
                self.add_error("nome_completo", "Informe o nome completo.")
            if not email:
                self.add_error("email", "Informe o e-mail.")
            elif User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
                self.add_error("email", "Já existe um usuário cadastrado com este e-mail.")
            cleaned_data["nome_completo"] = nome_completo
            cleaned_data["email"] = email

        estado = cleaned_data.get("estado")
        cidade = cleaned_data.get("cidade")
        escola = cleaned_data.get("escola")
        if estado and cidade and cidade.estado_id != estado.pk:
            self.add_error("cidade", "A cidade selecionada não pertence ao estado informado.")
        if cidade and escola and (
            not cidade.codigo_ibge
            or escola.id_municipio != cidade.codigo_ibge
            or escola.sigla_uf != cidade.estado.sigla
        ):
            self.add_error("escola", "A escola selecionada não pertence à cidade informada.")

        return cleaned_data

    @transaction.atomic
    def save_cadastro(self):
        pessoa = self.pessoa_encontrada
        if pessoa is None:
            cpf = self.cleaned_data["cpf"]
            email = self.cleaned_data["email"]
            usuario = User.objects.create_user(
                username=email,
                email=email,
                password=cpf,
                first_name=self.cleaned_data["nome_completo"],
            )
            pessoa, _ = Pessoa.objects.get_or_create(usuario=usuario)
            pessoa.cpf = cpf
            pessoa.save(update_fields=("cpf",))

        cadastro = super().save(commit=False)
        cadastro.id_pessoa = pessoa
        cadastro.save()
        return cadastro

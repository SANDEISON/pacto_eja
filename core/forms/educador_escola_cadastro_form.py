import json

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import (
    Cidade,
    Educador,
    EducadorEscola,
    Escola,
    Estado,
    FuncaoCaracterizacaoTurma,
    FuncaoEducador,
)
from ..validators import validate_cpf
from .bootstrap_form_mixin import BootstrapFormMixin


User = get_user_model()


class EducadorEscolaCadastroForm(BootstrapFormMixin, forms.Form):
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
        required=False,
    )
    cidade = forms.ModelChoiceField(
        label="Cidade de atuação",
        queryset=Cidade.objects.none(),
        empty_label="Selecione primeiro o estado",
        required=False,
    )
    escola = forms.ModelChoiceField(
        label="Escola",
        queryset=Escola.objects.none(),
        widget=forms.HiddenInput(),
        required=False,
    )
    funcao_caracterizacao_turmas = forms.ChoiceField(
        label="Atuação",
        choices=(("", "Selecione a função"), *FuncaoCaracterizacaoTurma.choices),
        required=False,
    )
    atuacoes_json = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.educador_encontrado = None
        if not self.is_bound:
            self.fields["atuacoes_json"].initial = "[]"

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
        self.educador_encontrado = Educador.objects.select_related("usuario").filter(cpf=cpf).first()
        return cpf

    def clean(self):
        cleaned_data = super().clean()
        educador = self.educador_encontrado

        if educador:
            usuario = educador.usuario
            cleaned_data["nome_completo"] = educador.nome_completo or usuario.get_full_name() or usuario.first_name or usuario.username
            cleaned_data["email"] = usuario.email
        else:
            nome_completo = (cleaned_data.get("nome_completo") or "").strip()
            email = (cleaned_data.get("email") or "").strip().lower()
            if not nome_completo:
                self.add_error("nome_completo", "Informe o nome completo.")
            if not email:
                self.add_error("email", "Informe o e-mail.")
            elif User.objects.filter(email__iexact=email).exists():
                self.add_error("email", "Já existe um usuário cadastrado com este e-mail.")
            if User.objects.filter(username=cleaned_data.get("cpf", "")).exists():
                self.add_error("cpf", "Já existe um usuário cadastrado com este CPF.")
            cleaned_data["nome_completo"] = nome_completo
            cleaned_data["email"] = email

        atuacoes = self._clean_atuacoes(cleaned_data.get("atuacoes_json"), educador)
        cleaned_data["atuacoes"] = atuacoes

        return cleaned_data

    def _clean_atuacoes(self, raw_atuacoes, educador):
        try:
            dados = json.loads(raw_atuacoes or "[]")
        except (TypeError, json.JSONDecodeError):
            self.add_error(None, "A lista de atuações está inválida. Adicione novamente os vínculos.")
            return []

        if not isinstance(dados, list) or not dados:
            self.add_error(None, "Adicione pelo menos uma atuação antes de salvar o cadastro.")
            return []
        if len(dados) > 20:
            self.add_error(None, "É permitido adicionar no máximo 20 atuações por cadastro.")
            return []

        try:
            estado_ids = {int(item["estado_id"]) for item in dados}
            cidade_ids = {int(item["cidade_id"]) for item in dados}
            escola_ids = {int(item["escola_id"]) for item in dados}
        except (KeyError, TypeError, ValueError):
            self.add_error(None, "Há uma atuação com informações incompletas.")
            return []

        estados = Estado.objects.in_bulk(estado_ids)
        cidades = Cidade.objects.select_related("estado").in_bulk(cidade_ids)
        escolas = Escola.objects.in_bulk(escola_ids)
        funcoes_validas = {choice[0] for choice in FuncaoCaracterizacaoTurma.choices}
        atuacoes = []
        chaves = set()

        for item in dados:
            estado = estados.get(int(item["estado_id"]))
            cidade = cidades.get(int(item["cidade_id"]))
            escola = escolas.get(int(item["escola_id"]))
            funcao = item.get("funcao", "")
            if not estado or not cidade or not escola or funcao not in funcoes_validas:
                self.add_error(None, "Há uma atuação com informações inválidas.")
                continue
            if cidade.estado_id != estado.pk:
                self.add_error(None, "Uma das cidades não pertence ao estado informado.")
                continue
            if (
                not cidade.codigo_ibge
                or escola.id_municipio != cidade.codigo_ibge
                or escola.sigla_uf != cidade.estado.sigla
            ):
                self.add_error(None, "Uma das escolas não pertence à cidade informada.")
                continue

            chave = (cidade.pk, escola.pk, funcao)
            if chave in chaves:
                self.add_error(None, "A lista contém uma atuação duplicada.")
                continue
            chaves.add(chave)

            if educador and FuncaoEducador.objects.filter(
                educador=educador,
                educador_escola__cidade=cidade,
                educador_escola__escola=escola,
                educador_escola__funcao_caracterizacao_turmas=funcao,
            ).exists():
                self.add_error(None, f"A atuação em {escola.nome} já está cadastrada para este educador.")
                continue
            atuacoes.append({"cidade": cidade, "escola": escola, "funcao": funcao})

        return atuacoes

    @transaction.atomic
    def save_cadastro(self):
        educador = self.educador_encontrado
        if educador is None:
            cpf = self.cleaned_data["cpf"]
            email = self.cleaned_data["email"]
            nome_completo = self.cleaned_data["nome_completo"]
            primeiro_nome, _, sobrenome = nome_completo.partition(" ")
            usuario = User.objects.create_user(
                username=cpf,
                email=email,
                password=cpf,
                first_name=primeiro_nome,
                last_name=sobrenome,
            )
            educador, _ = Educador.objects.get_or_create(usuario=usuario)
            educador.cpf = cpf
            educador.nome_completo = nome_completo
            educador.save(update_fields=("cpf", "nome_completo"))

        vinculos = []
        for atuacao in self.cleaned_data["atuacoes"]:
            vinculo = EducadorEscola.objects.create(
                cidade=atuacao["cidade"],
                escola=atuacao["escola"],
                funcao_caracterizacao_turmas=atuacao["funcao"],
            )
            FuncaoEducador.objects.create(
                educador=educador,
                educador_escola=vinculo,
            )
            vinculos.append(vinculo)
        return vinculos

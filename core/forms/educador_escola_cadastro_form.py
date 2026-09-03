import json

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import (
    Cidade,
    CorRaca,
    CursoCertificado,
    Educador,
    EducadorGenero,
    EducadorEscola,
    Endereco,
    Escola,
    Estado,
    Funcao,
    FuncaoCaracterizacaoTurma,
    FuncaoEducador,
)
from ..validators import validate_birth_date, validate_cpf
from .bootstrap_form_mixin import BootstrapFormMixin


User = get_user_model()


class EducadorEscolaCadastroForm(BootstrapFormMixin, forms.Form):
    nome_completo = forms.CharField(label="Nome completo", max_length=150)
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
    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    data_nascimento = forms.DateField(
        label="Data de nascimento",
        validators=(validate_birth_date,),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=("%Y-%m-%d",),
    )
    cor_raca = forms.ModelChoiceField(
        label="Cor/raça",
        queryset=CorRaca.objects.order_by("id"),
        empty_label="Selecione a cor/raça",
    )
    genero = forms.ModelChoiceField(
        label="Gênero",
        queryset=EducadorGenero.objects.all(),
        empty_label="Selecione o gênero",
    )
    endereco_cep = forms.CharField(
        label="CEP",
        max_length=9,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "placeholder": "00000-000",
                "autocomplete": "postal-code",
            }
        ),
    )
    endereco_logradouro = forms.CharField(
        label="Rua/Av.",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "address-line1"}),
    )
    endereco_numero = forms.CharField(
        label="Número",
        max_length=20,
        widget=forms.TextInput(attrs={"autocomplete": "address-line2"}),
    )
    endereco_complemento = forms.CharField(
        label="Complemento",
        max_length=100,
        widget=forms.TextInput(attrs={"autocomplete": "address-line3"}),
        required=False,
    )
    endereco_bairro = forms.CharField(label="Bairro", max_length=100)
    endereco_estado = forms.ModelChoiceField(
        label="UF",
        queryset=Estado.objects.all(),
        empty_label="Selecione a UF",
    )
    endereco_cidade = forms.ModelChoiceField(
        label="Município",
        queryset=Cidade.objects.none(),
        empty_label="Selecione primeiro a UF",
    )
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
    funcao = forms.ModelChoiceField(
        label="Função",
        queryset=Funcao.objects.all(),
        empty_label="Selecione a função",
        required=False,
    )
    funcao_caracterizacao_turmas = forms.ModelChoiceField(
        label="Atuação",
        queryset=FuncaoCaracterizacaoTurma.objects.all(),
        empty_label="Selecione a Atuação",
        required=False,
    )
    tempo_atuacao = forms.ChoiceField(
        label="Tempo de atuação",
        choices=(("", "Selecione o tempo de atuação"), *EducadorEscola.TempoAtuacao.choices),
        required=False,
    )
    atuacoes_json = forms.CharField(required=False, widget=forms.HiddenInput())
    curso_certificado = forms.ModelMultipleChoiceField(
        label="Solicito liberação do Certificado do Curso:",
        queryset=CursoCertificado.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.educador_encontrado = None
        if not self.is_bound:
            self.fields["atuacoes_json"].initial = "[]"

        estado_id = self.data.get("estado") if self.is_bound else self.initial.get("estado")
        if estado_id and str(estado_id).isdigit():
            self.fields["cidade"].queryset = Cidade.objects.filter(estado_id=estado_id)
            self.fields["cidade"].empty_label = "Selecione a cidade"

        endereco_estado_id = (
            self.data.get("endereco_estado") if self.is_bound else self.initial.get("endereco_estado")
        )
        if endereco_estado_id and str(endereco_estado_id).isdigit():
            self.fields["endereco_cidade"].queryset = Cidade.objects.filter(estado_id=endereco_estado_id)
            self.fields["endereco_cidade"].empty_label = "Selecione o município"

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

    def clean_endereco_cep(self):
        cep = "".join(character for character in self.cleaned_data["endereco_cep"] if character.isdigit())
        if len(cep) != 8:
            raise forms.ValidationError("Informe um CEP válido com 8 números.")
        return cep

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
            if email and User.objects.filter(email__iexact=email).exists():
                self.add_error("email", "Já existe um usuário cadastrado com este e-mail.")
            if User.objects.filter(username=cleaned_data.get("cpf", "")).exists():
                self.add_error("cpf", "Já existe um usuário cadastrado com este CPF.")
            cleaned_data["nome_completo"] = nome_completo
            cleaned_data["email"] = email

        atuacoes = self._clean_atuacoes(cleaned_data.get("atuacoes_json"), educador)
        cleaned_data["atuacoes"] = atuacoes

        endereco_estado = cleaned_data.get("endereco_estado")
        endereco_cidade = cleaned_data.get("endereco_cidade")
        if endereco_estado and endereco_cidade and endereco_cidade.estado_id != endereco_estado.pk:
            self.add_error("endereco_cidade", "O município selecionado não pertence à UF informada.")

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
        try:
            funcao_ids = {int(item.get("funcao", "")) for item in dados}
            atuacao_ids = {int(item.get("funcao_caracterizacao_turmas", "")) for item in dados}
        except (TypeError, ValueError):
            self.add_error(None, "Há uma atuação com informações inválidas.")
            return []
        funcoes = Funcao.objects.in_bulk(funcao_ids)
        caracterizacoes = FuncaoCaracterizacaoTurma.objects.in_bulk(atuacao_ids)
        tempos_atuacao_validos = {choice[0] for choice in EducadorEscola.TempoAtuacao.choices}
        atuacoes = []
        chaves = set()

        for item in dados:
            estado = estados.get(int(item["estado_id"]))
            cidade = cidades.get(int(item["cidade_id"]))
            escola = escolas.get(int(item["escola_id"]))
            funcao = funcoes.get(int(item.get("funcao", "")))
            atuacao = caracterizacoes.get(int(item.get("funcao_caracterizacao_turmas", "")))
            tempo_atuacao = item.get("tempo_atuacao", "")
            if (
                not estado
                or not cidade
                or not escola
                or not funcao
                or not atuacao
                or tempo_atuacao not in tempos_atuacao_validos
            ):
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

            chave = (cidade.pk, escola.pk, funcao.pk, atuacao.pk)
            if chave in chaves:
                self.add_error(None, "A lista contém uma atuação duplicada.")
                continue
            chaves.add(chave)

            if educador and FuncaoEducador.objects.filter(
                educador=educador,
                educador_escola__cidade=cidade,
                educador_escola__escola=escola,
                educador_escola__funcao_id=funcao.pk,
                educador_escola__funcao_caracterizacao_turmas_id=atuacao.pk,
            ).exists():
                self.add_error(None, f"A atuação em {escola.nome} já está cadastrada para este educador.")
                continue
            atuacoes.append(
                {
                    "cidade": cidade,
                    "escola": escola,
                    "funcao": funcao,
                    "funcao_caracterizacao_turmas": atuacao,
                    "tempo_atuacao": tempo_atuacao,
                }
            )

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

        educador.cor_raca = self.cleaned_data.get("cor_raca")
        educador.genero = self.cleaned_data.get("genero")
        educador.data_nascimento = self.cleaned_data.get("data_nascimento")
        educador.save(update_fields=("cor_raca", "genero", "data_nascimento"))
        educador.cursos_certificados.set(self.cleaned_data.get("curso_certificado"))

        Endereco.objects.update_or_create(
            educador=educador,
            defaults={
                "cep": self.cleaned_data["endereco_cep"],
                "logradouro": self.cleaned_data["endereco_logradouro"].strip(),
                "numero": self.cleaned_data["endereco_numero"].strip(),
                "complemento": self.cleaned_data["endereco_complemento"].strip(),
                "bairro": self.cleaned_data["endereco_bairro"].strip(),
                "cidade": self.cleaned_data["endereco_cidade"],
            },
        )

        vinculos = []
        for atuacao in self.cleaned_data["atuacoes"]:
            vinculo = EducadorEscola.objects.create(
                cidade=atuacao["cidade"],
                escola=atuacao["escola"],
                funcao=atuacao["funcao"],
                funcao_caracterizacao_turmas=atuacao["funcao_caracterizacao_turmas"],
                tempo_atuacao=atuacao["tempo_atuacao"],
            )
            FuncaoEducador.objects.create(
                educador=educador,
                educador_escola=vinculo,
            )
            vinculos.append(vinculo)
        return vinculos

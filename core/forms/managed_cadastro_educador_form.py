from django import forms

from ..models import CadastroEducador, Cidade, Escola, Estado, Pessoa
from .bootstrap_form_mixin import BootstrapFormMixin


class ManagedCadastroEducadorForm(BootstrapFormMixin, forms.ModelForm):
    id_pessoa = forms.ModelChoiceField(
        label="Pessoa",
        queryset=Pessoa.objects.none(),
        empty_label="Selecione a pessoa",
    )
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
            "id_pessoa",
            "estado",
            "cidade",
            "escola",
            "funcao_caracterizacao_turmas",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id_pessoa"].queryset = Pessoa.objects.select_related("usuario").order_by(
            "usuario__first_name",
            "usuario__username",
        )
        self.fields["id_pessoa"].label_from_instance = self._pessoa_label

        estado_id = self.data.get("estado") if self.is_bound else self.initial.get("estado") or self.instance.estado_id
        if estado_id and str(estado_id).isdigit():
            self.fields["cidade"].queryset = Cidade.objects.filter(estado_id=estado_id)
            self.fields["cidade"].empty_label = "Selecione a cidade"

        cidade_id = self.data.get("cidade") if self.is_bound else self.initial.get("cidade") or self.instance.cidade_id
        cidade = (
            Cidade.objects.select_related("estado").filter(pk=cidade_id).first()
            if cidade_id and str(cidade_id).isdigit()
            else None
        )
        if cidade and cidade.codigo_ibge:
            self.fields["escola"].queryset = Escola.objects.filter(
                id_municipio=cidade.codigo_ibge,
                sigla_uf=cidade.estado.sigla,
            )

        escola_id = self.data.get("escola") if self.is_bound else self.initial.get("escola") or self.instance.escola_id
        if escola_id and str(escola_id).isdigit():
            escola = Escola.objects.filter(pk=escola_id).first()
            if escola:
                self.fields["escola"].widget.attrs["data-selected-label"] = escola.nome

        self._apply_bootstrap_classes()

    @staticmethod
    def _pessoa_label(pessoa):
        identificacao = pessoa.cpf or pessoa.usuario.email or pessoa.usuario.username
        return f"{pessoa} — {identificacao}"

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get("estado")
        cidade = cleaned_data.get("cidade")
        escola = cleaned_data.get("escola")
        pessoa = cleaned_data.get("id_pessoa")

        if pessoa and CadastroEducador.objects.filter(id_pessoa=pessoa).exclude(pk=self.instance.pk).exists():
            self.add_error("id_pessoa", "Esta pessoa já possui um cadastro de educador.")

        if estado and cidade and cidade.estado_id != estado.pk:
            self.add_error("cidade", "A cidade selecionada não pertence ao estado informado.")
        if cidade and escola and (
            not cidade.codigo_ibge
            or escola.id_municipio != cidade.codigo_ibge
            or escola.sigla_uf != cidade.estado.sigla
        ):
            self.add_error("escola", "A escola selecionada não pertence à cidade informada.")
        return cleaned_data

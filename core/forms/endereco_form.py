from django import forms

from ..models import Cidade, Endereco, Estado
from .bootstrap_form_mixin import BootstrapFormMixin


class EnderecoForm(BootstrapFormMixin, forms.ModelForm):
    cep = forms.CharField(
        label="CEP",
        max_length=9,
        required=False,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "placeholder": "00000-000",
                "autocomplete": "postal-code",
            }
        ),
    )
    estado = forms.ModelChoiceField(
        label="UF",
        queryset=Estado.objects.all(),
        empty_label="Selecione a UF",
        required=False,
    )
    cidade = forms.ModelChoiceField(
        label="Município",
        queryset=Cidade.objects.none(),
        empty_label="Selecione primeiro a UF",
        required=False,
    )

    class Meta:
        model = Endereco
        fields = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade")
        widgets = {
            "logradouro": forms.TextInput(attrs={"autocomplete": "address-line1"}),
            "numero": forms.TextInput(attrs={"autocomplete": "address-line2"}),
            "complemento": forms.TextInput(attrs={"autocomplete": "address-line3"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estado_id = self.data.get(self.add_prefix("estado")) if self.is_bound else self.initial.get("estado")
        if not estado_id and self.instance.cidade_id:
            estado_id = self.instance.cidade.estado_id
        if estado_id and not self.is_bound:
            self.fields["estado"].initial = estado_id
        if estado_id and str(estado_id).isdigit():
            self.fields["cidade"].queryset = Cidade.objects.filter(estado_id=estado_id)
            self.fields["cidade"].empty_label = "Selecione o município"
        self._apply_bootstrap_classes()

    def clean_cep(self):
        cep = "".join(character for character in self.cleaned_data.get("cep", "") if character.isdigit())
        if cep and len(cep) != 8:
            raise forms.ValidationError("Informe um CEP válido com 8 números.")
        return cep

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get("estado")
        cidade = cleaned_data.get("cidade")
        if cidade and not estado:
            self.add_error("estado", "Selecione a UF do município.")
        elif estado and cidade and cidade.estado_id != estado.pk:
            self.add_error("cidade", "O município selecionado não pertence à UF informada.")
        return cleaned_data

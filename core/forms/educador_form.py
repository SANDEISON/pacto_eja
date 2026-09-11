from django import forms

from ..models import Educador
from ..validators import somente_digitos, validate_cpf
from .bootstrap_form_mixin import BootstrapFormMixin


class EducadorForm(BootstrapFormMixin, forms.ModelForm):
    """Edita os dados pessoais específicos do perfil de educador."""
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        required=False,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "000.000.000-00"}),
    )

    class Meta:
        model = Educador
        fields = ("nome_social", "cpf", "data_nascimento", "genero", "cor_raca", "telefone", "estado_civil")
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "telefone": forms.TextInput(attrs={"type": "tel", "placeholder": "(00) 00000-0000"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_nascimento"].input_formats = ["%Y-%m-%d"]
        self.fields["cor_raca"].empty_label = "Selecione a cor/raça"
        self.fields["genero"].empty_label = "Selecione o gênero"
        self.fields["estado_civil"].empty_label = "Selecione o estado civil"
        self._apply_bootstrap_classes()

    def clean_cpf(self):
        """Armazena o CPF validado sem caracteres de formatação."""
        cpf_informado = self.cleaned_data.get("cpf")
        if not cpf_informado:
            return None
        cpf = somente_digitos(cpf_informado)
        validate_cpf(cpf)
        return cpf

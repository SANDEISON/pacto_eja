from django import forms

from ..models import ProgramacaoSala, Sala
from .bootstrap_form_mixin import BootstrapFormMixin


class ProgramacaoSalaInlineForm(BootstrapFormMixin, forms.ModelForm):
    """Edita uma programação diretamente no formulário da sala relacionada."""
    class Meta:
        model = ProgramacaoSala
        fields = (
            "data",
            "turno",
            "modalidade",
            "link",
            "tematica",
            "descricao",
            "quantidade_max_participantes",
        )
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "link": forms.URLInput(attrs={"placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        """Configura o formato de data aceito pelo campo HTML5."""
        super().__init__(*args, **kwargs)
        self.fields["data"].input_formats = ["%Y-%m-%d"]
        self._apply_bootstrap_classes()


SalaProgramacaoFormSet = forms.inlineformset_factory(
    Sala,
    ProgramacaoSala,
    form=ProgramacaoSalaInlineForm,
    fields=ProgramacaoSalaInlineForm.Meta.fields,
    extra=0,
    can_delete=True,
)

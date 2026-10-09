from django import forms

from ..models import ProgramacaoSala, Sala
from .bootstrap_form_mixin import BootstrapFormMixin
from .user_name_choice_field import UserNameChoiceField


class ProgramacaoSalaInlineForm(BootstrapFormMixin, forms.ModelForm):
    """Edita uma programação diretamente no formulário da sala relacionada."""
    class Meta:
        model = ProgramacaoSala
        fields = (
            "data",
            "turno",
            "modalidade",
            "link",
            "responsavel",
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
        original = self.fields["responsavel"]
        self.fields["responsavel"] = UserNameChoiceField(
            queryset=original.queryset.order_by("first_name", "last_name", "pk"),
            label=original.label,
            required=original.required,
            help_text=original.help_text,
            empty_label="Selecione um responsável",
            widget=forms.Select(attrs={
                "data-searchable-user-select": "",
                "data-search-placeholder": "Buscar responsável pelo nome",
            }),
        )
        self._apply_bootstrap_classes()


class SalaAtividadeForm(BootstrapFormMixin, forms.ModelForm):
    """Cadastra uma sala a partir do formulário de uma atividade."""

    class Meta:
        model = Sala
        fields = ("nome",)

    def __init__(self, *args, **kwargs):
        """Aplica a apresentação visual comum aos campos administrativos."""
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()


SalaProgramacaoFormSet = forms.inlineformset_factory(
    Sala,
    ProgramacaoSala,
    form=ProgramacaoSalaInlineForm,
    fields=ProgramacaoSalaInlineForm.Meta.fields,
    extra=0,
    can_delete=True,
)


AtividadeSalaProgramacaoFormSet = forms.inlineformset_factory(
    Sala,
    ProgramacaoSala,
    form=ProgramacaoSalaInlineForm,
    fields=ProgramacaoSalaInlineForm.Meta.fields,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)

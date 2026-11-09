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
            "mediador",
            "tematica",
            "descricao",
            "publica",
            "quantidade_max_participantes",
        )
        widgets = {
            "data": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "link": forms.URLInput(attrs={"placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def clean(self):
        cleaned_data = super().clean()
        # Temporariamente desativado até a inclusão dos horários da programação.
        # campos = ("data", "turno", "modalidade")
        # if self.instance.sala_id and all(cleaned_data.get(campo) for campo in campos):
        #     duplicadas = ProgramacaoSala.objects.filter(
        #         sala_id=self.instance.sala_id,
        #         **{campo: cleaned_data[campo] for campo in campos},
        #     ).exclude(pk=self.instance.pk)
        #     if duplicadas.exists():
        #         raise forms.ValidationError(
        #             "Esta sala já possui uma atividade cadastrada nesta data, turno e modalidade."
        #         )
        return cleaned_data


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

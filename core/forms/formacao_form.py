from datetime import date

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from ..models import Educador, Formacao
from .bootstrap_form_mixin import BootstrapFormMixin


class FormacaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Formacao
        fields = (
            "nivel",
            "nome_curso",
            "instituicao",
            "situacao",
            "modalidade",
            "ano_inicio",
            "ano_conclusao",
        )
        widgets = {
            "ano_inicio": forms.NumberInput(attrs={"min": 1900}),
            "ano_conclusao": forms.NumberInput(attrs={"min": 1900}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = date.today().year
        self.fields["nivel"].choices = (("", "Selecione o nível"), *Formacao.Nivel.choices)
        self.fields["situacao"].choices = (("", "Selecione a situação"), *Formacao.Situacao.choices)
        self.fields["modalidade"].choices = (("", "Selecione a modalidade"), *Formacao.Modalidade.choices)
        self.fields["ano_inicio"].widget.attrs["max"] = current_year
        self.fields["ano_conclusao"].widget.attrs["max"] = current_year
        self._apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()
        current_year = date.today().year
        ano_inicio = cleaned_data.get("ano_inicio")
        ano_conclusao = cleaned_data.get("ano_conclusao")
        situacao = cleaned_data.get("situacao")

        if ano_inicio and not 1900 <= ano_inicio <= current_year:
            self.add_error("ano_inicio", f"Informe um ano entre 1900 e {current_year}.")
        if ano_conclusao and not 1900 <= ano_conclusao <= current_year:
            self.add_error("ano_conclusao", f"Informe um ano entre 1900 e {current_year}.")
        if ano_inicio and ano_conclusao and ano_conclusao < ano_inicio:
            self.add_error("ano_conclusao", "O ano de conclusão não pode ser anterior ao ano de início.")
        if situacao == Formacao.Situacao.CONCLUIDO and not ano_conclusao:
            self.add_error("ano_conclusao", "Informe o ano de conclusão da formação concluída.")
        return cleaned_data


class BaseFormacaoFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        formacoes = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            chave = (
                form.cleaned_data["nivel"],
                form.cleaned_data["nome_curso"].strip().casefold(),
                form.cleaned_data["instituicao"].strip().casefold(),
                form.cleaned_data.get("ano_inicio"),
            )
            if chave in formacoes:
                raise forms.ValidationError("Há uma formação duplicada na lista.")
            formacoes.add(chave)


FormacaoFormSet = inlineformset_factory(
    Educador,
    Formacao,
    form=FormacaoForm,
    formset=BaseFormacaoFormSet,
    extra=0,
    can_delete=True,
)


class FormacaoFormSetWithExtra(FormacaoFormSet):
    """Formset usado pelo fallback sem JavaScript do botão Adicionar formação."""

    extra = 1

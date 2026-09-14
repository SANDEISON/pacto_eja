from django import forms

from ..models import Avaliacao, CandidaturaAvaliador, ChamadaAvaliadores
from .bootstrap_form_mixin import BootstrapFormMixin


ESCALA_AVALIACAO = [(valor, str(valor)) for valor in range(1, 6)]


class ChamadaAvaliadoresForm(BootstrapFormMixin, forms.ModelForm):
    """Configura o período de seleção e o prazo de trabalho dos avaliadores."""
    class Meta:
        model = ChamadaAvaliadores
        fields = (
            "atividade", "titulo", "descricao", "requisitos", "inscricoes_inicio",
            "inscricoes_fim", "avaliacoes_fim", "ativa",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "requisitos": forms.Textarea(attrs={"rows": 5}),
            "inscricoes_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "inscricoes_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "avaliacoes_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        """Limita a escolha às atividades que aceitam submissão de trabalhos."""
        super().__init__(*args, **kwargs)
        self.fields["atividade"].queryset = self.fields["atividade"].queryset.filter(permite_submissao=True)
        for name in ("inscricoes_inicio", "inscricoes_fim", "avaliacoes_fim"):
            self.fields[name].input_formats = ["%Y-%m-%dT%H:%M"]
        self._apply_bootstrap_classes()


class CandidaturaAvaliadorForm(BootstrapFormMixin, forms.ModelForm):
    """Coleta experiência, interesses e conflitos do candidato a avaliador."""
    declaracao = forms.BooleanField(
        label="Declaro que informarei qualquer conflito de interesse antes de aceitar uma avaliação."
    )

    class Meta:
        model = CandidaturaAvaliador
        fields = ("area_atuacao", "experiencia", "temas_interesse", "conflitos_de_interesse")
        widgets = {
            "experiencia": forms.Textarea(attrs={"rows": 5}),
            "temas_interesse": forms.Textarea(attrs={"rows": 4}),
            "conflitos_de_interesse": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        """Aplica a apresentação visual comum aos campos da candidatura."""
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()


class AvaliacaoForm(BootstrapFormMixin, forms.ModelForm):
    """Registra notas e parecer, permitindo rascunho ou conclusão definitiva."""
    class Meta:
        model = Avaliacao
        fields = (
            "nota_relevancia", "nota_metodologia", "nota_clareza", "nota_contribuicao",
            "parecer", "observacoes_autor", "recomendacao",
        )
        widgets = {
            "nota_relevancia": forms.Select(choices=ESCALA_AVALIACAO),
            "nota_metodologia": forms.Select(choices=ESCALA_AVALIACAO),
            "nota_clareza": forms.Select(choices=ESCALA_AVALIACAO),
            "nota_contribuicao": forms.Select(choices=ESCALA_AVALIACAO),
            "parecer": forms.Textarea(attrs={"rows": 7}),
            "observacoes_autor": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, finalizar=False, **kwargs):
        """Exige todos os critérios apenas quando o avaliador conclui o parecer."""
        super().__init__(*args, **kwargs)
        self.finalizar = finalizar
        for nome in self.fields:
            self.fields[nome].required = finalizar
        self._apply_bootstrap_classes()

    def clean(self):
        """Garante que notas finais permaneçam dentro da escala de um a cinco."""
        cleaned_data = super().clean()
        if self.finalizar:
            for nome in ("nota_relevancia", "nota_metodologia", "nota_clareza", "nota_contribuicao"):
                nota = cleaned_data.get(nome)
                if nota is not None and nota not in range(1, 6):
                    self.add_error(nome, "A nota deve estar entre 1 e 5.")
        return cleaned_data

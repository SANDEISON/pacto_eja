from django import forms
from django.db import transaction

from ..models import (
    Cidade,
    Educador,
    EducadorEscola,
    Escola,
    Estado,
    FuncaoEducador,
)
from .bootstrap_form_mixin import BootstrapFormMixin


class EducadorEscolaForm(BootstrapFormMixin, forms.ModelForm):
    educador = forms.ModelChoiceField(
        label="Educador",
        queryset=Educador.objects.none(),
        empty_label="Selecione o educador",
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
        model = EducadorEscola
        fields = (
            "cidade",
            "escola",
            "funcao_caracterizacao_turmas",
            "tempo_atuacao",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["educador"].queryset = Educador.objects.select_related("usuario").order_by(
            "nome_completo",
            "usuario__username",
        )
        self.fields["educador"].label_from_instance = self._educador_label

        if self.instance.pk:
            funcao_educador = FuncaoEducador.objects.filter(
                educador_escola=self.instance,
            ).first()
            if funcao_educador:
                self.fields["educador"].initial = funcao_educador.educador_id

        estado_id = self.data.get("estado") if self.is_bound else self.initial.get("estado")
        if not estado_id and self.instance.cidade_id:
            estado_id = self.instance.cidade.estado_id
        if estado_id and not self.is_bound:
            self.fields["estado"].initial = estado_id
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
    def _educador_label(educador):
        identificacao = educador.cpf or educador.usuario.email or educador.usuario.username
        return f"{educador} — {identificacao}"

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get("estado")
        cidade = cleaned_data.get("cidade")
        escola = cleaned_data.get("escola")
        educador = cleaned_data.get("educador")

        if estado and cidade and cidade.estado_id != estado.pk:
            self.add_error("cidade", "A cidade selecionada não pertence ao estado informado.")
        if cidade and escola and (
            not cidade.codigo_ibge
            or escola.id_municipio != cidade.codigo_ibge
            or escola.sigla_uf != cidade.estado.sigla
        ):
            self.add_error("escola", "A escola selecionada não pertence à cidade informada.")
        funcao = cleaned_data.get("funcao_caracterizacao_turmas")
        if educador and cidade and escola and funcao:
            vinculos_iguais = FuncaoEducador.objects.filter(
                educador=educador,
                educador_escola__cidade=cidade,
                educador_escola__escola=escola,
                educador_escola__funcao_caracterizacao_turmas=funcao,
            )
            if self.instance.pk:
                vinculos_iguais = vinculos_iguais.exclude(
                    educador_escola_id=self.instance.pk,
                )
            if vinculos_iguais.exists():
                self.add_error(None, "Este vínculo do educador com a escola já está cadastrado.")
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        vinculo = super().save(commit=False)
        if commit:
            vinculo.save()
            FuncaoEducador.objects.update_or_create(
                educador_escola=vinculo,
                defaults={"educador": self.cleaned_data["educador"]},
            )
            self.save_m2m()
        return vinculo

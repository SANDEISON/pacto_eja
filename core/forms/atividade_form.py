from django import forms
from django.contrib.auth import get_user_model

from ..models import Atividade, Coautor, Educador, Trabalho
from ..validators import somente_digitos, validate_cpf
from .bootstrap_form_mixin import BootstrapFormMixin


class AtividadeForm(BootstrapFormMixin, forms.ModelForm):
    """Formulário administrativo para configurar uma atividade e seus prazos."""
    class Meta:
        model = Atividade
        fields = (
            "tipo", "titulo", "descricao", "local", "link", "data_inicio", "data_fim",
            "inscricoes_inicio", "inscricoes_fim", "vagas", "permite_submissao",
            "submissoes_fim", "ativo",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 5}),
            "local": forms.TextInput(attrs={"placeholder": "Endereço, prédio, sala ou auditório"}),
            "link": forms.URLInput(attrs={"placeholder": "https://..."}),
            "data_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "data_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "inscricoes_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "inscricoes_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "submissoes_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        """Configura formatos HTML5 e textos de ajuda exibidos na administração."""
        super().__init__(*args, **kwargs)
        self.fields["local"].help_text = (
            "Informe o endereço completo do local. O sistema criará automaticamente "
            "um link para visualização no Google Maps."
        )
        self.fields["link"].help_text = "Use este campo somente para o acesso ao evento on-line."
        for name in ("data_inicio", "data_fim", "inscricoes_inicio", "inscricoes_fim", "submissoes_fim"):
            self.fields[name].input_formats = ["%Y-%m-%dT%H:%M"]
        self._apply_bootstrap_classes()


class TrabalhoForm(BootstrapFormMixin, forms.ModelForm):
    """Recebe o título e o PDF de um trabalho vinculado à inscrição."""
    class Meta:
        model = Trabalho
        fields = ("titulo", "arquivo")
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Informe o título completo do trabalho"}),
            "arquivo": forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"}),
        }

    def __init__(self, *args, required=True, **kwargs):
        """Permite exibir o formulário sem exigir trabalho na inscrição simples."""
        super().__init__(*args, **kwargs)
        self.fields["titulo"].required = required
        self.fields["arquivo"].required = required and not bool(self.instance.pk)
        self._apply_bootstrap_classes()

    def clean_arquivo(self):
        """Confere MIME e assinatura do arquivo, além dos validadores do model."""
        arquivo = self.cleaned_data.get("arquivo")
        if arquivo and hasattr(arquivo, "content_type"):
            header = arquivo.read(5)
            arquivo.seek(0)
            if arquivo.content_type != "application/pdf" or header != b"%PDF-":
                raise forms.ValidationError("Envie um arquivo PDF válido.")
        return arquivo


class CoautorForm(BootstrapFormMixin, forms.ModelForm):
    """Seleciona um usuário ativo e copia seus dados públicos para o trabalho."""
    class Meta:
        model = Coautor
        fields = ("usuario", "nome", "email")
        widgets = {
            "usuario": forms.HiddenInput(),
            "nome": forms.TextInput(attrs={"readonly": True, "tabindex": "-1"}),
            "email": forms.EmailInput(attrs={"readonly": True, "tabindex": "-1"}),
        }

    def __init__(self, *args, **kwargs):
        self.autor = kwargs.pop("autor", None)
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = get_user_model().objects.filter(is_active=True)
        self.fields["usuario"].required = True
        self.fields["nome"].required = False
        self.fields["email"].required = False
        self._apply_bootstrap_classes()

    def clean_usuario(self):
        """Evita repetir o autor principal na lista de coautores."""
        usuario = self.cleaned_data["usuario"]
        if self.autor and usuario.pk == self.autor.pk:
            raise forms.ValidationError("O autor principal não pode ser incluído como coautor.")
        return usuario

    def clean(self):
        """Obtém nome e e-mail do cadastro, sem confiar nos campos enviados pelo navegador."""
        cleaned_data = super().clean()
        usuario = cleaned_data.get("usuario")
        if usuario:
            cleaned_data["nome"] = usuario.get_full_name() or usuario.get_username()
            cleaned_data["email"] = usuario.email
        return cleaned_data


class BaseCoautorFormSet(forms.BaseInlineFormSet):
    """Valida a coleção de coautores antes de persistir qualquer item."""

    def clean(self):
        """Rejeita o mesmo usuário informado mais de uma vez."""
        super().clean()
        usuarios = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            usuario = form.cleaned_data.get("usuario")
            if not usuario:
                continue
            if usuario.pk in usuarios:
                raise forms.ValidationError("O mesmo coautor foi informado mais de uma vez.")
            usuarios.add(usuario.pk)


CoautorFormSet = forms.inlineformset_factory(
    Trabalho,
    Coautor,
    form=CoautorForm,
    formset=BaseCoautorFormSet,
    fields=("usuario", "nome", "email"),
    extra=1,
    can_delete=True,
)


class DadosPessoaisInscricaoForm(BootstrapFormMixin, forms.ModelForm):
    """Coleta os dados mínimos do educador exigidos para uma inscrição."""
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "000.000.000-00"}),
    )

    class Meta:
        model = Educador
        fields = ("cpf", "data_nascimento", "genero", "cor_raca", "telefone", "estado_civil")
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "telefone": forms.TextInput(attrs={"type": "tel", "placeholder": "(00) 00000-0000"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("cpf", "data_nascimento", "telefone"):
            self.fields[name].required = True
        self.fields["data_nascimento"].input_formats = ["%Y-%m-%d"]
        self._apply_bootstrap_classes()

    def clean_cpf(self):
        """Valida e salva o CPF sem máscara para manter o banco consistente."""
        digits = somente_digitos(self.cleaned_data["cpf"])
        validate_cpf(digits)
        return digits

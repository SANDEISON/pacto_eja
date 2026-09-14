from django import forms
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils import timezone

from ..models import (
    Atividade,
    Cidade,
    Coautor,
    Educador,
    EvidenciaTrabalho,
    Inscricao,
    ProgramacaoSala,
    Refeicao,
    Trabalho,
    TrabalhoMunicipio,
)
from ..validators import somente_digitos, validate_cpf
from .bootstrap_form_mixin import BootstrapFormMixin


class ProgramacaoSalaCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Expõe os dados de cada programação para a filtragem no navegador."""

    def create_option(self, name, value, *args, **kwargs):
        """Adiciona modalidade, temática e data como atributos HTML da opção."""
        option = super().create_option(name, value, *args, **kwargs)
        programacao = getattr(value, "instance", None)
        if programacao is not None:
            option["attrs"]["data-modalidade"] = programacao.modalidade
            option["attrs"]["data-tematica"] = str(programacao.tematica_id)
            option["attrs"]["data-data"] = programacao.data.isoformat()
        return option


class ProgramacaoSalaMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Apresenta cada programação como um cartão informativo selecionável."""

    def label_from_instance(self, programacao):
        """Monta o resumo visual exibido no cartão de uma programação."""
        return format_html(
            '<span class="program-card-content">'
            '<span class="program-card-heading">'
            '<strong>{}</strong>'
            '<span class="program-modality program-modality-{}">{}</span>'
            '</span>'
            '<span class="program-card-meta">'
            '<span><i class="bi bi-calendar3" aria-hidden="true"></i>{}</span>'
            '<span><i class="bi bi-clock" aria-hidden="true"></i>{}</span>'
            '</span>'
            '</span>',
            programacao.sala,
            programacao.modalidade,
            programacao.get_modalidade_display(),
            programacao.data.strftime("%d/%m/%Y"),
            programacao.get_turno_display(),
        )


class AtividadeForm(BootstrapFormMixin, forms.ModelForm):
    """Formulário administrativo para configurar uma atividade e seus prazos."""
    class Meta:
        model = Atividade
        fields = (
            "tipo", "modalidade", "titulo", "descricao", "local", "data_inicio", "data_fim",
            "inscricoes_inicio", "inscricoes_fim", "vagas", "permite_submissao",
            "modelo_submissao", "submissoes_fim", "ativo",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 5}),
            "local": forms.TextInput(attrs={"placeholder": "Endereço, prédio, sala ou auditório"}),
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
        for name in ("data_inicio", "data_fim", "inscricoes_inicio", "inscricoes_fim", "submissoes_fim"):
            self.fields[name].input_formats = ["%Y-%m-%dT%H:%M"]
        self._apply_bootstrap_classes()


class RefeicaoForm(BootstrapFormMixin, forms.ModelForm):
    """Cadastra uma refeição oferecida durante uma atividade."""
    class Meta:
        model = Refeicao
        fields = ("tipo", "data", "horario")
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "horario": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        """Configura os formatos aceitos pelos controles nativos de data e hora."""
        super().__init__(*args, **kwargs)
        self.fields["data"].input_formats = ["%Y-%m-%d"]
        self.fields["horario"].input_formats = ["%H:%M"]
        self._apply_bootstrap_classes()


class BaseAtividadeRefeicaoFormSet(forms.BaseInlineFormSet):
    """Valida em conjunto as refeições vinculadas a uma atividade."""

    def clean(self):
        """Exige que cada refeição esteja dentro do período da atividade."""
        super().clean()
        if any(self.errors) or not self.instance.data_inicio or not self.instance.data_fim:
            return
        inicio = timezone.localtime(self.instance.data_inicio).date()
        fim = timezone.localtime(self.instance.data_fim).date()
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            data = form.cleaned_data.get("data")
            if data and not inicio <= data <= fim:
                form.add_error(
                    "data", "A data da refeição deve estar dentro do período da atividade."
                )


AtividadeRefeicaoFormSet = forms.inlineformset_factory(
    Atividade,
    Refeicao,
    form=RefeicaoForm,
    formset=BaseAtividadeRefeicaoFormSet,
    fields=("tipo", "data", "horario"),
    extra=0,
    can_delete=True,
)


class TrabalhoForm(BootstrapFormMixin, forms.ModelForm):
    """Combina o PDF e a autoria com os metadados do modelo da atividade."""

    LIMITES = {
        "resumo": 1100,
        "apresentacao": 1100,
        "objetivo_geral": 300,
        "objetivos_especificos": 500,
        "desenvolvimento_metodologico": 6000,
        "consideracoes": 2000,
        "referencias": 1000,
    }
    TURNOS = (("manha", "Manhã"), ("tarde", "Tarde"), ("noite", "Noite"))
    CAMPOS_COMUNS_OBRIGATORIOS = (
        "titulo",
        "arquivo",
        "aceitou_termo_relato",
        "aceitou_termo_cessao",
        "aceitou_originalidade",
    )
    CAMPOS_TRABALHO_ACADEMICO = ("eixo_tematico", "resumo", "palavras_chave")
    CAMPOS_RELATO_EXPERIENCIA = (
        "apresentacao",
        "periodo_inicio",
        "periodo_fim",
        "turnos",
        "carga_horaria",
        "estado",
        "objetivo_geral",
        "objetivos_especificos",
        "desenvolvimento_metodologico",
        "consideracoes",
        "referencias",
        "autorizacao_imagens",
        "aceitou_termo_imagem",
    )

    turnos = forms.MultipleChoiceField(
        label="Turnos de desenvolvimento da atividade",
        choices=TURNOS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Trabalho
        fields = (
            "titulo",
            "eixo_tematico",
            "resumo",
            "palavras_chave",
            "apresentacao",
            "periodo_inicio",
            "periodo_fim",
            "turnos",
            "carga_horaria",
            "estado",
            "objetivo_geral",
            "objetivos_especificos",
            "desenvolvimento_metodologico",
            "consideracoes",
            "referencias",
            "arquivo",
            "autorizacao_imagens",
            "aceitou_termo_imagem",
            "aceitou_termo_relato",
            "aceitou_termo_cessao",
            "aceitou_originalidade",
            "deseja_participar_publicacao",
        )
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Informe o título completo do trabalho"}),
            "eixo_tematico": forms.TextInput(
                attrs={"placeholder": "Informe o eixo temático do evento"}
            ),
            "resumo": forms.Textarea(attrs={"rows": 7}),
            "palavras_chave": forms.TextInput(
                attrs={"placeholder": "Educação de jovens e adultos; formação; território"}
            ),
            "apresentacao": forms.Textarea(attrs={"rows": 7}),
            "periodo_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "periodo_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "objetivo_geral": forms.Textarea(attrs={"rows": 3}),
            "objetivos_especificos": forms.Textarea(attrs={"rows": 4}),
            "desenvolvimento_metodologico": forms.Textarea(attrs={"rows": 8}),
            "consideracoes": forms.Textarea(attrs={"rows": 7}),
            "referencias": forms.Textarea(attrs={"rows": 5}),
            "autorizacao_imagens": forms.RadioSelect,
            "arquivo": forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"}),
        }

    def __init__(self, *args, required=True, modelo_submissao=Atividade.ModeloSubmissao.ACADEMICO, **kwargs):
        """Permite exibir o formulário sem exigir trabalho na inscrição simples."""
        super().__init__(*args, **kwargs)
        self.modelo_submissao = modelo_submissao
        for field in self.fields.values():
            field.required = False
        campos_obrigatorios = list(self.CAMPOS_COMUNS_OBRIGATORIOS)
        if modelo_submissao == Atividade.ModeloSubmissao.RELATO_EXPERIENCIA:
            campos_obrigatorios.extend(self.CAMPOS_RELATO_EXPERIENCIA)
        else:
            campos_obrigatorios.extend(self.CAMPOS_TRABALHO_ACADEMICO)
        for nome_campo in campos_obrigatorios:
            self.fields[nome_campo].required = required
        self.fields["arquivo"].required = required and not bool(self.instance.pk)
        for nome_campo, limite in self.LIMITES.items():
            self.fields[nome_campo].widget.attrs["maxlength"] = limite
            self.fields[nome_campo].widget.attrs["data-character-limit"] = limite
        self.fields["titulo"].widget.attrs["data-character-limit"] = 250
        self.fields["eixo_tematico"].widget.attrs["data-character-limit"] = 200
        self.fields["palavras_chave"].widget.attrs["data-character-limit"] = 300
        self.fields["periodo_inicio"].input_formats = ["%Y-%m-%d"]
        self.fields["periodo_fim"].input_formats = ["%Y-%m-%d"]
        self._apply_bootstrap_classes()

    def clean(self):
        """Valida limites e mantém apenas os campos do modelo de submissão escolhido."""
        cleaned_data = super().clean()
        for nome_campo, limite in self.LIMITES.items():
            valor = (cleaned_data.get(nome_campo) or "").strip()
            if len(valor) > limite:
                self.add_error(
                    nome_campo,
                    f"Este campo deve ter no máximo {limite} caracteres.",
                )
        inicio = cleaned_data.get("periodo_inicio")
        fim = cleaned_data.get("periodo_fim")
        if inicio and fim and fim < inicio:
            self.add_error("periodo_fim", "A data final deve ser igual ou posterior à inicial.")
        if self.modelo_submissao == Atividade.ModeloSubmissao.ACADEMICO:
            for nome_campo in self.CAMPOS_RELATO_EXPERIENCIA:
                cleaned_data[nome_campo] = None if nome_campo in {
                    "periodo_inicio", "periodo_fim", "carga_horaria", "estado"
                } else (False if nome_campo == "aceitou_termo_imagem" else "")
            cleaned_data["turnos"] = []
        else:
            for nome_campo in self.CAMPOS_TRABALHO_ACADEMICO:
                cleaned_data[nome_campo] = ""
        return cleaned_data

    def clean_arquivo(self):
        """Confere MIME e assinatura do arquivo, além dos validadores do model."""
        arquivo = self.cleaned_data.get("arquivo")
        if arquivo and hasattr(arquivo, "content_type"):
            header = arquivo.read(5)
            arquivo.seek(0)
            if arquivo.content_type != "application/pdf" or header != b"%PDF-":
                raise forms.ValidationError("Envie um arquivo PDF válido.")
        return arquivo


class TrabalhoMunicipioForm(BootstrapFormMixin, forms.ModelForm):
    """Registra um município alcançado e sua quantidade de participantes."""
    class Meta:
        model = TrabalhoMunicipio
        fields = ("cidade", "participantes")
        widgets = {"participantes": forms.NumberInput(attrs={"min": 1})}

    def __init__(self, *args, estado=None, **kwargs):
        """Limita as cidades ao estado selecionado no relato de experiência."""
        super().__init__(*args, **kwargs)
        self.fields["cidade"].queryset = Cidade.objects.none()
        if estado:
            self.fields["cidade"].queryset = Cidade.objects.filter(estado=estado)
        elif self.instance.pk:
            self.fields["cidade"].queryset = Cidade.objects.filter(
                estado=self.instance.cidade.estado
            )
        self._apply_bootstrap_classes()


class BaseTrabalhoMunicipioFormSet(forms.BaseInlineFormSet):
    """Valida a relação de municípios alcançados pelo trabalho."""

    def clean(self):
        """Exige ao menos um município e impede cidades duplicadas."""
        super().clean()
        if any(self.errors):
            return
        cidades_informadas = set()
        total_formularios_ativos = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            cidade = form.cleaned_data.get("cidade")
            participantes = form.cleaned_data.get("participantes")
            if not cidade and not participantes:
                continue
            total_formularios_ativos += 1
            if cidade and cidade.pk in cidades_informadas:
                raise forms.ValidationError("O mesmo município foi informado mais de uma vez.")
            if cidade:
                cidades_informadas.add(cidade.pk)
        if not total_formularios_ativos:
            raise forms.ValidationError("Informe pelo menos um município alcançado.")


TrabalhoMunicipioFormSet = forms.inlineformset_factory(
    Trabalho,
    TrabalhoMunicipio,
    form=TrabalhoMunicipioForm,
    formset=BaseTrabalhoMunicipioFormSet,
    fields=("cidade", "participantes"),
    extra=1,
    can_delete=True,
)


class EvidenciaTrabalhoForm(BootstrapFormMixin, forms.ModelForm):
    """Recebe uma imagem que comprova o relato de experiência."""
    class Meta:
        model = EvidenciaTrabalho
        fields = ("arquivo",)
        widgets = {
            "arquivo": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,.jpg,.jpeg,.png"}
            )
        }

    def __init__(self, *args, **kwargs):
        """Mantém evidências opcionais enquanto o usuário preenche o formulário."""
        super().__init__(*args, **kwargs)
        self.fields["arquivo"].required = False
        self._apply_bootstrap_classes()

    def clean_arquivo(self):
        """Confere a assinatura binária para aceitar somente imagens JPG ou PNG."""
        arquivo = self.cleaned_data.get("arquivo")
        if not arquivo or not hasattr(arquivo, "read"):
            return arquivo
        assinatura = arquivo.read(8)
        arquivo.seek(0)
        eh_jpeg = assinatura.startswith(b"\xff\xd8\xff")
        eh_png = assinatura == b"\x89PNG\r\n\x1a\n"
        if not (eh_jpeg or eh_png):
            raise forms.ValidationError("Envie uma imagem JPG ou PNG válida.")
        return arquivo


EvidenciaTrabalhoFormSet = forms.inlineformset_factory(
    Trabalho,
    EvidenciaTrabalho,
    form=EvidenciaTrabalhoForm,
    fields=("arquivo",),
    extra=2,
    max_num=2,
    validate_max=True,
    can_delete=True,
)


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
        """Restringe a busca a usuários ativos e guarda o autor principal."""
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
    modalidade_inscricao = forms.ChoiceField(label="Modalidade de participação")
    refeicoes = forms.ModelMultipleChoiceField(
        label="Refeições disponíveis",
        queryset=Refeicao.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Marque uma ou mais refeições. Disponível somente para participação presencial.",
    )
    programacoes = ProgramacaoSalaMultipleChoiceField(
        label="Programações disponíveis",
        queryset=ProgramacaoSala.objects.none(),
        required=False,
        widget=ProgramacaoSalaCheckboxSelectMultiple,
        help_text="Marque uma ou mais programações disponíveis para a modalidade escolhida.",
    )

    class Meta:
        model = Educador
        fields = (
            "modalidade_inscricao",
            "programacoes",
            "refeicoes",
            "nome_social",
            "cpf",
            "data_nascimento",
            "genero",
            "cor_raca",
            "telefone",
            "estado_civil",
        )
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "telefone": forms.TextInput(attrs={"type": "tel", "placeholder": "(00) 00000-0000"}),
        }

    def __init__(self, *args, **kwargs):
        """Adapta modalidades, refeições e programações à atividade selecionada."""
        atividade = kwargs.pop("atividade")
        inscricao = kwargs.pop("inscricao", None)
        super().__init__(*args, **kwargs)
        self.fields["modalidade_inscricao"].choices = atividade.modalidades_disponiveis
        programacoes = atividade.programacoes.select_related(
            "sala", "tematica"
        ).order_by("data", "turno", "sala__nome", "modalidade")
        self.fields["programacoes"].queryset = programacoes
        self.programacoes_tematicas = list(
            programacoes.order_by("tematica__nome")
            .values_list("tematica_id", "tematica__nome")
            .distinct()
        )
        self.programacoes_datas = list(
            programacoes.order_by("data").values_list("data", flat=True).distinct()
        )
        if atividade.aceita_modalidade(Inscricao.Modalidade.PRESENCIAL):
            self.fields["refeicoes"].queryset = atividade.refeicoes.order_by(
                "data", "horario", "tipo"
            )
        if inscricao:
            self.fields["modalidade_inscricao"].initial = inscricao.modalidade
            self.fields["programacoes"].initial = inscricao.programacoes.all()
            self.fields["refeicoes"].initial = inscricao.refeicoes.all()
        elif len(atividade.modalidades_disponiveis) == 1:
            self.fields["modalidade_inscricao"].initial = atividade.modalidades_disponiveis[0][0]
        for name in (
            "cpf",
            "data_nascimento",
            "genero",
            "cor_raca",
            "telefone",
            "estado_civil",
        ):
            self.fields[name].required = True
        self.fields["data_nascimento"].input_formats = ["%Y-%m-%d"]
        self._apply_bootstrap_classes()

    def clean_modalidade_inscricao(self):
        """Valida novamente a escolha contra as modalidades da atividade."""
        modalidade = self.cleaned_data["modalidade_inscricao"]
        if modalidade not in dict(self.fields["modalidade_inscricao"].choices):
            raise forms.ValidationError("Esta modalidade não está disponível para a atividade.")
        return modalidade

    def clean(self):
        """Valida programações e refeições contra a modalidade de participação."""
        cleaned_data = super().clean()
        modalidade = cleaned_data.get("modalidade_inscricao")
        programacoes = cleaned_data.get("programacoes")
        refeicoes = cleaned_data.get("refeicoes")
        if programacoes and modalidade:
            programacoes_incompativeis = programacoes.exclude(modalidade=modalidade)
            if programacoes_incompativeis.exists():
                self.add_error(
                    "programacoes",
                    "Selecione somente programações da modalidade escolhida.",
                )
        if refeicoes and modalidade != Inscricao.Modalidade.PRESENCIAL:
            self.add_error(
                "refeicoes",
                "A seleção de refeições está disponível somente para a modalidade presencial.",
            )
        return cleaned_data

    def clean_cpf(self):
        """Valida e salva o CPF sem máscara para manter o banco consistente."""
        digits = somente_digitos(self.cleaned_data["cpf"])
        validate_cpf(digits)
        return digits

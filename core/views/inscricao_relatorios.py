"""Filtros e exportações compartilhados pela lista de inscrições da atividade."""
import csv
from collections import Counter

from django import forms
from django.http import HttpResponse
from django.utils.functional import cached_property

from ..models import Educador
from .reports import datas_disponiveis_atividade, listar_participantes_detalhados


DIMENSOES = {
    "municipio": "Município de atuação", "escola": "Escola", "estado": "Estado",
    "modalidade_inscrito_atual": "Modalidade do inscrito", "funcao": "Função do educador",
    "escolaridade": "Escolaridade", "genero": "Gênero", "cor": "Cor/raça",
}


class FiltrosInscricaoForm(forms.Form):
    apresentacao = forms.ChoiceField(label="Apresentação de trabalho", required=False, choices=[("", "Todos"), ("sim", "Sim"), ("nao", "Não")])
    estado = forms.ChoiceField(label="Estado", required=False)
    municipio = forms.ChoiceField(label="Município", required=False)
    modalidade = forms.ChoiceField(label="Modalidade", required=False, choices=[("", "Todas as modalidades"), ("presencial", "Presencial"), ("online", "Remoto (On-line)")])
    representante = forms.ChoiceField(label="Rep. Undime/Consed (autodeclaração)", required=False, choices=[("", "Todos"), ("Sim", "Sim"), ("Não", "Não")])
    undime = forms.ChoiceField(label="Undime (decisão administrativa)", required=False, choices=[("", "Todas as decisões"), ("sim", "Sim — vínculo aprovado"), ("nao", "Não — vínculo não aprovado"), ("pendente", "Sem avaliação administrativa")])
    genero = forms.ChoiceField(label="Gênero", required=False)
    data = forms.ChoiceField(label="Datas disponíveis por atividade", required=False)
    programacao = forms.ChoiceField(label="Programação", required=False)
    refeicao = forms.ChoiceField(label="Escolha das refeições", required=False)
    q = forms.CharField(label="Pesquisar", required=False, widget=forms.TextInput(attrs={"placeholder": "Nome, CPF, e-mail, telefone, escola, município, estado ou trabalho"}))
    dimensao = forms.ChoiceField(label="Agrupar resumo por", required=False, choices=list(DIMENSOES.items()), initial="municipio")

    def __init__(self, *args, atividade, registros, **kwargs):
        super().__init__(*args, **kwargs)
        for campo, chave, todos in [
            ("estado", "estado", "Todos os estados"),
            ("municipio", "municipio", "Todos os municípios"),
            ("genero", "genero", "Todos os gêneros"),
        ]:
            valores = sorted({r[chave] for r in registros if r.get(chave)})
            self.fields[campo].choices = [("", todos)] + [(v, v) for v in valores]
        self.fields["data"].choices = [("", "Todas as datas")] + [
            (d, "/".join(reversed(d.split("-")))) for d in datas_disponiveis_atividade(atividade)
        ]
        self.fields["programacao"].choices = [("", "Todas as programações")] + [
            (str(p.pk), str(p)) for p in atividade.programacoes.select_related("sala")
        ]
        self.fields["refeicao"].choices = [("", "Todas as refeições")] + [
            (str(r.pk), str(r)) for r in atividade.refeicoes.all()
        ]
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select form-select-sm" if isinstance(field, forms.ChoiceField) else "form-control form-control-sm"


class InscricaoRelatoriosMixin:
    @cached_property
    def registros_inscricao(self):
        educadores = Educador.objects.filter(usuario__inscricoes_atividades__atividade=self.atividade)
        usuarios = dict(educadores.values_list("pk", "usuario_id"))
        registros = listar_participantes_detalhados(educadores, self.atividade.pk)
        return {usuarios[r["educador_id"]]: r for r in registros}

    @cached_property
    def filtros_form(self):
        return FiltrosInscricaoForm(
            self.request.GET, atividade=self.atividade,
            registros=self.registros_inscricao.values(),
        )

    def filtrar_inscricoes(self, queryset):
        if not self.filtros_form.is_valid():
            return queryset.none()
        filtros = self.filtros_form.cleaned_data
        usuarios = []
        titulos = dict(queryset.values_list("usuario_id", "trabalho__titulo"))
        for usuario_id, registro in self.registros_inscricao.items():
            atividade = next(a for a in registro["atividades"] if a["id"] == self.atividade.pk)
            if filtros["apresentacao"] and atividade["vai_apresentar_trabalho"] != (filtros["apresentacao"] == "sim"):
                continue
            if any(filtros[campo] and registro[chave] != filtros[campo] for campo, chave in [
                ("estado", "estado"), ("municipio", "municipio"),
                ("representante", "representante_undime_consed"), ("genero", "genero"),
            ]):
                continue
            if filtros["modalidade"] and atividade["modalidade"] != filtros["modalidade"]:
                continue
            if filtros["undime"] and registro["undime_confirmada"] is not {"sim": True, "nao": False, "pendente": None}[filtros["undime"]]:
                continue
            if filtros["data"] and filtros["data"] not in atividade["datas"]:
                continue
            if filtros["programacao"] and int(filtros["programacao"]) not in registro["programacoes_ids"]:
                continue
            if filtros["refeicao"] and (atividade["modalidade"] != "presencial" or int(filtros["refeicao"]) not in atividade["refeicoes_ids"]):
                continue
            termo = filtros["q"].strip().casefold()
            if termo:
                texto = " ".join(str(registro.get(c, "")) for c in ["nome", "email", "telefone", "municipio", "estado", "sigla_uf", "escola", "funcao", "cpf"])
                texto += " " + (titulos.get(usuario_id) or "")
                digitos = "".join(c for c in termo if c.isdigit())
                if termo not in texto.casefold() and not (digitos and digitos in (registro["cpf"] or "")):
                    continue
            usuarios.append(usuario_id)
        return queryset.filter(usuario_id__in=usuarios)

    def get(self, request, *args, **kwargs):
        formato = request.GET.get("exportar")
        if formato in ("participantes", "resumo") and self.filtros_form.is_valid():
            queryset = self.get_queryset()
            registros = [self.registros_inscricao[i.usuario_id] for i in queryset]
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="inscricoes-{self.atividade.pk}-{formato}.csv"'
            response.write("\ufeff")
            writer = csv.writer(response, delimiter=";")

            def escrever(valores):
                writer.writerow(["'" + str(v) if str(v).lstrip().startswith(("=", "+", "-", "@")) else v for v in valores])

            if formato == "resumo":
                dimensao = self.filtros_form.cleaned_data["dimensao"] or "municipio"
                escrever([DIMENSOES[dimensao], "Quantidade", "Percentual"])
                totais = Counter(r.get(dimensao) or "Não informado" for r in registros)
                for nome, qtd in sorted(totais.items(), key=lambda item: (-item[1], item[0])):
                    escrever([nome, qtd, f"{qtd / len(registros) * 100:.2f}%"])
            else:
                escrever(["Nome", "E-mail", "CPF", "Data de nascimento", "Telefone", "Gênero", "Cor/raça", "Estado civil", "CEP", "Logradouro, número e bairro", "UF", "Município", "Representante Undime/Consed", "Undime (decisão administrativa)", "Escola", "Função na EJA", "Tempo de atuação", "Formação acadêmica", "Atividade", "Modalidade de participação", "Programações/salas", "Refeições", "Data da inscrição"])
                for r in registros:
                    valores = [r.get(c, "") for c in ["nome", "email", "cpf", "data_nascimento", "telefone", "genero", "cor", "estado_civil", "cep"]]
                    valores += [", ".join(r[c] for c in ["logradouro", "numero", "complemento", "bairro"] if r[c]), r["uf_residencia"], r["municipio_residencia"], r["representante_undime_consed"], {True: "Sim", False: "Não", None: "Pendente"}[r["undime_confirmada"]], r["escola"], r["funcao"], r["tempo"], ", ".join(r["formacoes_academicas"]), self.atividade.titulo, r["modalidade_inscrito_atual"], ", ".join(r["programacoes_labels"]), ", ".join(r["refeicoes_inscrito_atual"]), r["data_inscricao_atual"]]
                    escrever(valores)
            return response
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        parametros.pop("exportar", None)
        context.update(filtros_form=self.filtros_form, filtros_query=parametros.urlencode())
        context["filtros_catalogo"] = {
            "modalidade": self.atividade.modalidade,
            "programacoes": {str(p.pk): p.data.isoformat() for p in self.atividade.programacoes.all()},
            "refeicoes": {str(r.pk): r.data.isoformat() for r in self.atividade.refeicoes.all()},
        }
        return context

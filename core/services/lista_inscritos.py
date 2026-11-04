from html import escape
from io import BytesIO
from unicodedata import combining, normalize

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .comprovante_inscricao import AZUL_ESCURO, CINZA, FUNDO, TEXTO, _rodape


def _chave_nome(nome):
    return "".join(c for c in normalize("NFD", nome.casefold()) if not combining(c))


def gerar_lista_inscritos(atividade, programacao, modalidade, inscricoes):
    """Lista nominal da programação, ordenada sem distinguir acentos ou caixa."""
    nomes = sorted(
        (i.usuario.get_full_name().strip() or i.usuario.get_username() for i in inscricoes),
        key=lambda nome: (_chave_nome(nome), nome),
    )
    arquivo = BytesIO()
    documento = SimpleDocTemplate(
        arquivo, pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm,
        topMargin=59 * mm, bottomMargin=23 * mm,
        title="Lista de frequência", author="Pacto EJA",
    )
    corpo = ParagraphStyle("CorpoLista", fontName="PactoSans", fontSize=9,
                           leading=13, textColor=TEXTO)
    titulo = ParagraphStyle("TituloLista", fontName="PactoSans-Bold", fontSize=17,
                            leading=21, alignment=TA_CENTER, textColor=AZUL_ESCURO)
    evento = ParagraphStyle("EventoLista", parent=corpo, fontName="PactoSans-Bold",
                            fontSize=12, leading=16, alignment=TA_CENTER)
    detalhes = ParagraphStyle("DetalhesLista", parent=corpo, textColor=CINZA,
                              alignment=TA_CENTER)
    paragrafo = lambda texto: Paragraph(escape(str(texto)), corpo)
    rotulo = "Presenciais" if modalidade == "presencial" else "On-line"
    conteudo = [
        Paragraph("LISTA DE FREQUÊNCIA", titulo), Spacer(1, 3 * mm),
        Paragraph(escape(atividade.titulo), evento), Spacer(1, 3 * mm),
        Paragraph(escape(str(programacao)), detalhes), Spacer(1, 3 * mm),
        Paragraph(f"Inscritos: {rotulo}", detalhes), Spacer(1, 4 * mm),
        paragrafo(f"Total de inscritos: {len(nomes)}"), Spacer(1, 5 * mm),
    ]
    if nomes:
        dados = [["Nº", "Nome do participante", "Assinatura"]]
        dados.extend([str(numero), paragrafo(nome), ""] for numero, nome in enumerate(nomes, 1))
        tabela = Table(dados, colWidths=[12 * mm, 80 * mm, 74 * mm],
                       minRowHeights=[10 * mm] * len(dados), repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
            ("FONTNAME", (0, 0), (-1, -1), "PactoSans"),
            ("FONTNAME", (0, 0), (-1, 0), "PactoSans-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), AZUL_ESCURO),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE7F1")),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        conteudo.append(tabela)
    else:
        conteudo.append(paragrafo("Nenhum inscrito nesta modalidade para esta programação."))

    logo = finders.find("img/ufpb-unesco-eja.png")

    def cabecalho_e_rodape(canvas, doc):
        canvas.saveState()
        if logo:
            canvas.drawImage(logo, 67 * mm, A4[1] - 54.4 * mm,
                             width=76 * mm, height=38.4 * mm, mask="auto")
        canvas.restoreState()
        _rodape(canvas, doc)

    documento.build(conteudo, onFirstPage=cabecalho_e_rodape, onLaterPages=cabecalho_e_rodape)
    arquivo.seek(0)
    return arquivo

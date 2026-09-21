from html import escape
from io import BytesIO
from pathlib import Path

import reportlab
from django.contrib.staticfiles import finders
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


AZUL = colors.HexColor("#087FE5")
AZUL_ESCURO = colors.HexColor("#075DB9")
TEXTO = colors.HexColor("#263445")
CINZA = colors.HexColor("#718096")
FUNDO = colors.HexColor("#F4F9FD")
FONTES_REPORTLAB = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("PactoSans", FONTES_REPORTLAB / "Vera.ttf"))
pdfmetrics.registerFont(TTFont("PactoSans-Bold", FONTES_REPORTLAB / "VeraBd.ttf"))
pdfmetrics.registerFontFamily(
    "PactoSans",
    normal="PactoSans",
    bold="PactoSans-Bold",
)


def _cpf_formatado(cpf):
    digitos = "".join(caractere for caractere in (cpf or "") if caractere.isdigit())
    if len(digitos) != 11:
        return "Não informado"
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def _texto(valor):
    return escape(str(valor or "—"))


def _texto_com_quebras(valor):
    return _texto(valor).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def _rodape(canvas, documento):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DCE7F1"))
    canvas.line(22 * mm, 16 * mm, 188 * mm, 16 * mm)
    canvas.setFillColor(CINZA)
    canvas.setFont("PactoSans", 8)
    canvas.drawString(22 * mm, 10 * mm, "Documento emitido eletronicamente pelo sistema Pacto EJA.")
    canvas.drawRightString(188 * mm, 10 * mm, f"Página {documento.page}")
    canvas.restoreState()


def gerar_comprovante_inscricao(inscricao):
    """Gera um comprovante nominal em PDF para uma inscrição confirmada."""
    atividade = inscricao.atividade
    usuario = inscricao.usuario
    educador = getattr(usuario, "educador", None)
    estilos_base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle(
            "TituloComprovante",
            parent=estilos_base["Title"],
            alignment=TA_CENTER,
            textColor=AZUL_ESCURO,
            fontName="PactoSans-Bold",
            fontSize=17,
            leading=21,
            spaceAfter=2 * mm,
        ),
        "evento": ParagraphStyle(
            "EventoComprovante",
            parent=estilos_base["Heading2"],
            alignment=TA_CENTER,
            textColor=TEXTO,
            fontName="PactoSans-Bold",
            fontSize=13,
            leading=17,
            spaceAfter=3 * mm,
        ),
        "descricao_evento": ParagraphStyle(
            "DescricaoEventoComprovante",
            parent=estilos_base["BodyText"],
            alignment=TA_CENTER,
            textColor=CINZA,
            fontName="PactoSans",
            fontSize=9,
            leading=13,
            spaceAfter=4 * mm,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloComprovante",
            parent=estilos_base["Heading2"],
            textColor=AZUL_ESCURO,
            fontName="PactoSans-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "corpo": ParagraphStyle(
            "CorpoComprovante",
            parent=estilos_base["BodyText"],
            textColor=TEXTO,
            fontName="PactoSans",
            fontSize=10,
            leading=15,
        ),
        "pequeno": ParagraphStyle(
            "PequenoComprovante",
            parent=estilos_base["BodyText"],
            textColor=CINZA,
            fontName="PactoSans",
            fontSize=8.5,
            leading=12,
        ),
    }
    arquivo = BytesIO()
    documento = SimpleDocTemplate(
        arquivo,
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=16 * mm,
        bottomMargin=23 * mm,
        title=f"Comprovante de inscrição - {atividade.titulo}",
        author="Pacto EJA",
    )
    elementos = []
    logo = finders.find("img/ufpb-unesco-eja.png")
    if logo:
        imagem = Image(logo, width=92 * mm, height=46.5 * mm)
        imagem.hAlign = "CENTER"
        elementos.extend((imagem, Spacer(1, 3 * mm)))

    codigo = f"INS-{inscricao.inscrito_em:%Y}-{inscricao.pk:06d}"
    nome = usuario.get_full_name().strip() or usuario.get_username()
    elementos.extend(
        (
            Paragraph("COMPROVANTE DE INSCRIÇÃO", estilos["titulo"]),
            Paragraph(_texto(atividade.titulo), estilos["evento"]),
            Paragraph(_texto_com_quebras(atividade.descricao), estilos["descricao_evento"]),
            Paragraph(
                "Declaramos, para os devidos fins, que o(a) participante abaixo está "
                "regularmente inscrito(a) na atividade indicada neste documento.",
                estilos["corpo"],
            ),
            Spacer(1, 5 * mm),
        )
    )
    dados = (
        ("Participante", nome),
        ("CPF", _cpf_formatado(getattr(educador, "cpf", ""))),
        ("Número da inscrição", codigo),
        ("Atividade", atividade.titulo),
        ("Tipo", atividade.get_tipo_display()),
        ("Modalidade", inscricao.get_modalidade_display()),
        (
            "Período",
            f"{timezone.localtime(atividade.data_inicio):%d/%m/%Y às %H:%M} a "
            f"{timezone.localtime(atividade.data_fim):%d/%m/%Y às %H:%M}",
        ),
        ("Local", atividade.local or "Atividade on-line"),
        ("Inscrição realizada em", f"{timezone.localtime(inscricao.inscrito_em):%d/%m/%Y às %H:%M}"),
    )
    tabela = Table(
        [
            (
                Paragraph(f"<b>{_texto(rotulo)}</b>", estilos["corpo"]),
                Paragraph(_texto(valor), estilos["corpo"]),
            )
            for rotulo, valor in dados
        ],
        colWidths=(52 * mm, 110 * mm),
        hAlign="LEFT",
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), FUNDO),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE7F1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elementos.append(tabela)

    programacoes = list(
        inscricao.programacoes.select_related("sala", "tematica").order_by(
            "data", "turno", "sala__nome"
        )
    )
    if programacoes:
        itens = [Paragraph("Programações selecionadas", estilos["subtitulo"])]
        for programacao in programacoes:
            itens.append(
                Paragraph(
                    f"- {_texto(programacao.data.strftime('%d/%m/%Y'))} - "
                    f"{_texto(programacao.get_turno_display())}: {_texto(programacao.sala)} "
                    f"({_texto(programacao.tematica)})",
                    estilos["corpo"],
                )
            )
        elementos.append(KeepTogether(itens))

    refeicoes = list(inscricao.refeicoes.order_by("data", "horario", "tipo"))
    if refeicoes:
        itens = [Paragraph("Refeições selecionadas", estilos["subtitulo"])]
        for refeicao in refeicoes:
            itens.append(
                Paragraph(
                    f"- {_texto(refeicao.data.strftime('%d/%m/%Y'))} às "
                    f"{_texto(refeicao.horario.strftime('%H:%M'))} - "
                    f"{_texto(refeicao.get_tipo_display())}",
                    estilos["corpo"],
                )
            )
        elementos.append(KeepTogether(itens))

    elementos.extend(
        (
            Spacer(1, 4 * mm),
            Paragraph(
                "Este comprovante confirma exclusivamente a inscrição do participante e não "
                "substitui certificado de participação, frequência ou conclusão.",
                estilos["pequeno"],
            ),
            Spacer(1, 2 * mm),
            Paragraph(
                f"Emitido em {timezone.localtime():%d/%m/%Y às %H:%M}.",
                estilos["pequeno"],
            ),
        )
    )
    documento.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    arquivo.seek(0)
    return arquivo

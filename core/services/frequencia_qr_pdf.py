from html import escape
from io import BytesIO

from django.contrib.staticfiles import finders
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from .comprovante_inscricao import AZUL_ESCURO, TEXTO, _rodape


def gerar_frequencia_qr_pdf(atividade, programacao, url):
    arquivo = BytesIO()
    documento = SimpleDocTemplate(
        arquivo, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=18 * mm, bottomMargin=24 * mm,
        title="Confirmação de presença presencial", author="Pacto EJA",
    )
    titulo = ParagraphStyle("TituloQR", fontName="PactoSans-Bold", fontSize=20,
                            leading=25, alignment=TA_CENTER, textColor=AZUL_ESCURO)
    corpo = ParagraphStyle("CorpoQR", fontName="PactoSans", fontSize=12,
                           leading=18, alignment=TA_CENTER, textColor=TEXTO)
    link = ParagraphStyle("LinkQR", parent=corpo, fontSize=9, leading=13,
                          textColor=AZUL_ESCURO, splitLongWords=True)
    conteudo = []
    logo = finders.find("img/ufpb-unesco-eja.png")
    if logo:
        conteudo.extend([Image(logo, width=76 * mm, height=38.4 * mm), Spacer(1, 5 * mm)])
    conteudo.extend([
        Paragraph("CONFIRME SUA PRESENÇA", titulo), Spacer(1, 6 * mm),
        Paragraph(escape(atividade.titulo), corpo), Spacer(1, 3 * mm),
        Paragraph(escape(str(programacao)), corpo),
        Paragraph(escape(str(programacao.tematica)), corpo), Spacer(1, 6 * mm),
    ])
    qr = QrCodeWidget(url, barLevel="M")
    x0, y0, x1, y1 = qr.getBounds()
    tamanho = 88 * mm
    desenho = Drawing(tamanho, tamanho, transform=[
        tamanho / (x1 - x0), 0, 0, tamanho / (y1 - y0), 0, 0,
    ])
    desenho.add(qr)
    desenho.hAlign = "CENTER"
    conteudo.extend([
        desenho, Spacer(1, 3 * mm),
        Paragraph("Link para confirmar a frequência:", corpo),
        Paragraph(f'<link href="{escape(url, quote=True)}"><u>{escape(url)}</u></link>', link),
        Spacer(1, 7 * mm),
        Paragraph("1. Leia o QR Code com a câmera do celular.<br/>"
                  "2. Entre com a conta utilizada na inscrição.<br/>"
                  "3. Toque em <b>Confirmar minha presença</b>.", corpo),
        Spacer(1, 5 * mm),
        Paragraph("Exclusivo para inscritos presenciais nesta programação.<br/>"
                  "Disponível na data da programação, durante o evento.", corpo),
    ])
    documento.build(conteudo, onFirstPage=_rodape, onLaterPages=_rodape)
    arquivo.seek(0)
    return arquivo

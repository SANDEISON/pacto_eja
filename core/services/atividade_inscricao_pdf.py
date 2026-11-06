"""Material para divulgação da inscrição e da programação de uma atividade."""

from html import escape
from io import BytesIO

from django.utils import timezone
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def gerar_atividade_inscricao_pdf(atividade, url, *, programacao=False):
    """Gera PDF com QR vetorial e link clicável para a atividade."""
    assunto = "Programação" if programacao else "Inscrição"
    arquivo = BytesIO()
    documento = SimpleDocTemplate(
        arquivo, pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm,
        topMargin=22 * mm, bottomMargin=22 * mm,
        title=f"{assunto} - {atividade.titulo}", author="Pacto EJA",
    )
    texto = ParagraphStyle(
        "InscricaoTexto", fontName="Helvetica", fontSize=12, leading=18,
        alignment=TA_CENTER, textColor=colors.HexColor("#263445"), spaceAfter=5 * mm,
    )
    titulo = ParagraphStyle(
        "InscricaoTitulo", parent=texto, fontName="Helvetica-Bold",
        fontSize=22, leading=28, textColor=colors.HexColor("#075DB9"),
    )
    qr = QrCodeWidget(url, barLevel="M")
    x1, y1, x2, y2 = qr.getBounds()
    tamanho = 90 * mm
    desenho = Drawing(
        tamanho, tamanho,
        transform=[tamanho / (x2 - x1), 0, 0, tamanho / (y2 - y1), 0, 0],
    )
    desenho.add(qr)
    desenho.hAlign = "CENTER"
    conteudo = [
        Paragraph("PACTO EJA", texto),
        Paragraph(escape(atividade.titulo), titulo),
        Paragraph(escape(atividade.get_modalidade_display()), texto),
        Paragraph(f"Início: {timezone.localtime(atividade.data_inicio):%d/%m/%Y às %H:%M}", texto),
    ]
    if atividade.endereco:
        conteudo.append(Paragraph(f"Local: {escape(atividade.endereco)}", texto))
    conteudo.append(Spacer(1, 5 * mm))
    if programacao:
        conteudo.extend([
            Paragraph("Baixe a programação da atividade", titulo),
            desenho,
            Paragraph("Aponte a câmera do celular para o QR code para baixar a programação.", texto),
        ])
    else:
        conteudo.extend([
            Paragraph("Inscreva-se nesta atividade", titulo),
            desenho,
            Paragraph("Aponte a câmera do celular para o QR code e acesse a página de inscrição.", texto),
            Paragraph(f'Inscrições até {timezone.localtime(atividade.inscricoes_fim):%d/%m/%Y às %H:%M}.', texto),
            Paragraph("Entre com sua conta para realizar a inscrição.", texto),
        ])
    conteudo.append(Paragraph(f'<link href="{escape(url, quote=True)}" color="#075DB9">{escape(url)}</link>', texto))
    documento.build(conteudo)
    arquivo.seek(0)
    return arquivo

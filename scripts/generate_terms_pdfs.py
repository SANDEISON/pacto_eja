"""Gera os termos oficiais exibidos na submissão de trabalhos."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
DIRETORIO_SAIDA = RAIZ_PROJETO / "static" / "docs"
VERSAO_TERMOS = "2026-01"
NOME_PROGRAMA = (
    "Programa de Formação de Alfabetizadores e Docentes dos Anos Iniciais do Ensino "
    "Fundamental pela Superação do Analfabetismo e Qualificação na Educação de Jovens e Adultos"
)


def register_fonts():
    """Usa Arial no Windows e fontes padrão do PDF nos demais sistemas."""
    fonte_regular = Path("C:/Windows/Fonts/arial.ttf")
    fonte_negrito = Path("C:/Windows/Fonts/arialbd.ttf")
    if fonte_regular.exists() and fonte_negrito.exists():
        pdfmetrics.registerFont(TTFont("PactoSans", fonte_regular))
        pdfmetrics.registerFont(TTFont("PactoSans-Bold", fonte_negrito))
        return "PactoSans", "PactoSans-Bold"
    return "Helvetica", "Helvetica-Bold"


def build_pdf(nome_arquivo, titulo, paragrafos):
    """Gera um termo institucional em PDF com cabeçalho e versão identificável."""
    fonte_regular, fonte_negrito = register_fonts()
    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)
    caminho_saida = DIRETORIO_SAIDA / nome_arquivo
    documento = SimpleDocTemplate(
        str(caminho_saida),
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=titulo,
        author="Pacto EJA",
        subject=f"Termo eletrônico - versão {VERSAO_TERMOS}",
    )
    estilos_padrao = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TermTitle",
        parent=estilos_padrao["Title"],
        fontName=fonte_negrito,
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#143B63"),
        spaceAfter=16,
    )
    estilo_corpo = ParagraphStyle(
        "TermBody",
        parent=estilos_padrao["BodyText"],
        fontName=fonte_regular,
        fontSize=11,
        leading=17,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#26384A"),
        spaceAfter=12,
    )
    estilo_auxiliar = ParagraphStyle(
        "TermSmall",
        parent=estilo_corpo,
        fontSize=9,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#66788A"),
    )
    cabecalho = Table(
        [[Paragraph("<b>PACTO EJA</b>", ParagraphStyle(
            "Brand", parent=estilo_corpo, fontName=fonte_negrito, fontSize=16,
            textColor=colors.white, alignment=TA_CENTER,
        ))]],
        colWidths=[16.6 * cm],
    )
    cabecalho.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0B67A3")),
        ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#0B67A3")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    conteudo = [
        cabecalho,
        Spacer(1, 18),
        Paragraph(titulo, estilo_titulo),
        Paragraph(NOME_PROGRAMA, estilo_auxiliar),
        Spacer(1, 16),
    ]
    conteudo.extend(Paragraph(texto, estilo_corpo) for texto in paragrafos)
    conteudo.extend([
        Spacer(1, 18),
        Table(
            [[Paragraph(
                "O aceite deste termo é realizado eletronicamente no momento da submissão. "
                "O sistema registra o usuário, a data, o horário e a versão do documento aceito.",
                estilo_auxiliar,
            )]],
            colWidths=[16.6 * cm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF6FB")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7D6E9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]),
        ),
        Spacer(1, 14),
        Paragraph(f"Versão {VERSAO_TERMOS}", estilo_auxiliar),
    ])
    documento.build(conteudo)
    return caminho_saida


def main():
    """Regenera todos os termos distribuídos nos arquivos estáticos."""
    build_pdf(
        "termo_uso_publicacao_trabalho.pdf",
        "Termo de Uso e Publicação do Trabalho",
        [
            "Declaro, por livre e espontânea vontade, que <b>AUTORIZO</b>, de forma gratuita, "
            "a Coordenação Geral do Programa a utilizar, reproduzir, publicar e divulgar o "
            "trabalho de minha autoria, sem limitação de tempo ou território, para fins "
            "institucionais, educacionais, formativos e de divulgação relacionados às ações do Pacto EJA.",
            "A autorização compreende a utilização do trabalho, integralmente ou em partes, "
            "respeitados o sentido e o contexto de seu conteúdo, em materiais impressos ou digitais, "
            "publicações, livros, revistas, materiais pedagógicos, plataformas educacionais, páginas "
            "institucionais, redes sociais, apresentações, vídeos, áudios, podcasts e demais meios de "
            "divulgação vinculados às ações do Pacto EJA.",
            "Declaro que o trabalho apresentado é de minha autoria e que, quando houver referência a "
            "outras pessoas, obras, documentos, imagens ou materiais de terceiros, comprometo-me a "
            "observar os respectivos direitos autorais, de imagem e demais direitos aplicáveis.",
        ],
    )
    build_pdf(
        "termo_cessao_direitos_autorais.pdf",
        "Termo de Cessão de Direitos Autorais",
        [
            "<b>DECLARO</b>, para os devidos fins, que cedo e transfiro, de forma gratuita e "
            "definitiva, todos os direitos autorais patrimoniais relativos ao trabalho enviado.",
            "A presente cessão compreende o direito de utilizar, reproduzir, adaptar, distribuir e "
            "divulgar o trabalho por qualquer meio físico ou digital, para fins exclusivamente "
            "educacionais, sem limitação de tempo ou território, desde que mantidos os créditos ao autor.",
            "Declaro possuir legitimidade para realizar esta cessão e responsabilizo-me pelas "
            "informações e pelos conteúdos apresentados no trabalho submetido.",
        ],
    )


if __name__ == "__main__":
    main()

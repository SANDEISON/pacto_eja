from html import escape
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .comprovante_inscricao import AZUL_ESCURO, FUNDO, TEXTO, _cpf_formatado, _rodape
from .lista_inscritos import _chave_nome


def gerar_lista_credenciamento(atividade, inscricoes):
    """Lista presencial completa para assinatura e preenchimento manual da data."""
    participantes = []
    for inscricao in inscricoes:
        usuario = inscricao.usuario
        educador = getattr(usuario, "educador", None)
        nome = usuario.get_full_name().strip() or getattr(educador, "nome_completo", "") or usuario.get_username()
        participantes.append((nome, _cpf_formatado(getattr(educador, "cpf", None))))
    participantes.sort(key=lambda item: (_chave_nome(item[0]), item[0], item[1]))
    arquivo = BytesIO()
    documento = SimpleDocTemplate(
        arquivo, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=20 * mm, bottomMargin=23 * mm,
        title="Lista de credenciamento presencial", author="Pacto EJA",
    )
    corpo = ParagraphStyle("CredenciamentoCorpo", fontName="PactoSans", fontSize=8, leading=11, textColor=TEXTO)
    titulo = ParagraphStyle("CredenciamentoTitulo", parent=corpo, fontName="PactoSans-Bold", fontSize=15, leading=20, textColor=AZUL_ESCURO)
    p = lambda texto: Paragraph(escape(str(texto)), corpo)
    inicio = timezone.localtime(atividade.data_inicio).strftime("%d/%m/%Y %H:%M")
    fim = timezone.localtime(atividade.data_fim).strftime("%d/%m/%Y %H:%M")
    conteudo = [
        Paragraph("LISTA DE CREDENCIAMENTO PRESENCIAL", titulo), Spacer(1, 4 * mm),
        p(atividade.titulo), p(f"Período do evento: {inicio} a {fim}"),
        p(f"Total de inscritos presenciais: {len(participantes)}"),
        p("Preencha a assinatura e a data do credenciamento nos campos abaixo."), Spacer(1, 5 * mm),
    ]
    if participantes:
        dados = [["Nome", "CPF", "Assinatura", "Data"]]
        dados.extend([p(nome), p(cpf), "", ""] for nome, cpf in participantes)
        tabela = Table(dados, colWidths=[63 * mm, 32 * mm, 48 * mm, 23 * mm],
                       minRowHeights=[10 * mm] + [15 * mm] * len(participantes), repeatRows=1)
        tabela.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "PactoSans"),
            ("FONTNAME", (0, 0), (-1, 0), "PactoSans-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
            ("TEXTCOLOR", (0, 0), (-1, 0), AZUL_ESCURO),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE7F1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        conteudo.append(tabela)
    else:
        conteudo.append(p("Nenhuma inscrição presencial nesta atividade."))
    documento.build(conteudo, onFirstPage=_rodape, onLaterPages=_rodape)
    arquivo.seek(0)
    return arquivo

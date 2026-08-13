import re
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal


# A planilha de origem ainda contém as colunas removidas do modelo. Elas são
# reconhecidas para validar o cabeçalho, mas não são incluídas nos registros.
EXPECTED_COLUMNS = (
    "id_escola",
    "nome",
    "id_municipio",
    "sigla_uf",
    "restricao_atendimento",
    "localizacao",
    "localidade_diferenciada",
    "categoria_administrativa",
    "endereco",
    "telefone",
    "dependencia_administrativa",
    "categoria_privada",
    "porte",
    "etapas_modalidades_oferecidas",
    "latitude",
    "longitude",
)

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
CELL_VALUE_TAG = f"{{{MAIN_NS}}}v"
TEXT_TAG = f"{{{MAIN_NS}}}t"


def _shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    values = []
    with archive.open("xl/sharedStrings.xml") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag == f"{{{MAIN_NS}}}si":
                values.append("".join(node.text or "" for node in element.iter(TEXT_TAG)))
                element.clear()
    return values


def _column_index(cell_reference):
    letters = re.match(r"[A-Z]+", cell_reference).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def _cell_value(cell, shared_strings):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(TEXT_TAG))
    value_node = cell.find(CELL_VALUE_TAG)
    if value_node is None or value_node.text is None:
        return None
    if cell_type == "s":
        return shared_strings[int(value_node.text)]
    return value_node.text


def iter_xlsx_rows(path):
    """Lê a primeira planilha do XLSX em streaming usando a biblioteca padrão."""
    with zipfile.ZipFile(path) as archive:
        shared_strings = _shared_strings(archive)
        with archive.open("xl/worksheets/sheet1.xml") as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                if element.tag != f"{{{MAIN_NS}}}row":
                    continue
                values = [None] * len(EXPECTED_COLUMNS)
                for cell in element.findall(f"{{{MAIN_NS}}}c"):
                    index = _column_index(cell.attrib["r"])
                    if index < len(values):
                        values[index] = _cell_value(cell, shared_strings)
                yield tuple(values)
                element.clear()


def _text(value):
    return "" if value is None else str(value).strip()


def _integer(value):
    if value in (None, ""):
        return None
    return int(Decimal(str(value)))


def iter_escola_records(path):
    rows = iter_xlsx_rows(path)
    header = next(rows, None)
    if header != EXPECTED_COLUMNS:
        raise ValueError(
            f"Colunas inesperadas no Excel. Esperado: {EXPECTED_COLUMNS!r}; recebido: {header!r}"
        )
    for row_number, row in enumerate(rows, start=2):
        if not any(value not in (None, "") for value in row):
            continue
        id_escola = _integer(row[0])
        id_municipio = _integer(row[2])
        if id_escola is None or id_municipio is None:
            raise ValueError(f"Identificadores obrigatórios ausentes na linha {row_number}.")
        yield {
            "id_escola": id_escola,
            "nome": _text(row[1]),
            "id_municipio": id_municipio,
            "sigla_uf": _text(row[3]),
            "restricao_atendimento": _text(row[4]),
            "localizacao": _text(row[5]),
            "localidade_diferenciada": _text(row[6]),
            "categoria_administrativa": _text(row[7]),
            "endereco": _text(row[8]),
            "telefone": _text(row[9]),
            "dependencia_administrativa": _text(row[10]),
            "categoria_privada": _text(row[11]),
            "etapas_modalidades_oferecidas": _text(row[13]),
        }

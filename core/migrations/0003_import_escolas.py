import os
from pathlib import Path

from django.conf import settings
from django.db import migrations

from core.migrations.loaders.escola_xlsx import iter_escola_records


WORKBOOK_RELATIVE_PATH = Path("staticfiles") / "base de dados das Escolas" / "br_bd_diretorios_brasil_escola.xlsx"


def _workbook_path():
    configured = os.environ.get("ESCOLAS_XLSX_PATH")
    candidates = [Path(configured)] if configured else []
    candidates.extend(
        [
            Path(settings.BASE_DIR) / WORKBOOK_RELATIVE_PATH,
            Path(settings.BASE_DIR) / "static" / "base de dados das Escolas" / "br_bd_diretorios_brasil_escola.xlsx",
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    locations = "\n - ".join(str(path) for path in candidates)
    raise RuntimeError(
        "A base de escolas não foi encontrada. Informe ESCOLAS_XLSX_PATH ou coloque o arquivo em:\n - " + locations
    )


def import_escolas(apps, schema_editor):
    database_name = str(schema_editor.connection.settings_dict.get("NAME", ""))
    if "memorydb_" in database_name:
        return

    Escola = apps.get_model("core", "Escola")
    workbook_path = _workbook_path()
    batch = []
    source_rows = 0

    print(f"Importando escolas de {workbook_path}...", flush=True)
    for record in iter_escola_records(workbook_path):
        batch.append(Escola(**record))
        source_rows += 1
        if len(batch) >= 1000:
            Escola.objects.bulk_create(batch, batch_size=500, ignore_conflicts=True)
            batch.clear()
            if source_rows % 25000 == 0:
                print(f"  {source_rows:,} linhas processadas", flush=True)
    if batch:
        Escola.objects.bulk_create(batch, batch_size=500, ignore_conflicts=True)

    imported_rows = Escola.objects.count()
    if imported_rows != source_rows:
        raise RuntimeError(
            f"Importação incompleta: {source_rows} linhas no Excel e {imported_rows} escolas no banco."
        )
    print(f"Importação concluída: {imported_rows:,} escolas cadastradas.", flush=True)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [("core", "0002_escola")]

    operations = [migrations.RunPython(import_escolas, migrations.RunPython.noop)]

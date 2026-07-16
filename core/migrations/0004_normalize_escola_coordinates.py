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
    raise RuntimeError("A base de escolas não foi encontrada para normalizar as coordenadas.")


def normalize_coordinates(apps, schema_editor):
    database_name = str(schema_editor.connection.settings_dict.get("NAME", ""))
    if "memorydb_" in database_name:
        return

    Escola = apps.get_model("core", "Escola")
    invalid_coordinates = (
        Escola.objects.exclude(latitude__isnull=True).exclude(latitude__range=(-35, 6)).exists()
        or Escola.objects.exclude(longitude__isnull=True).exclude(longitude__range=(-75, -30)).exists()
    )
    if not invalid_coordinates:
        print("Coordenadas das escolas já estão normalizadas.", flush=True)
        return

    batch = []
    processed = 0
    print("Normalizando coordenadas das escolas...", flush=True)
    for record in iter_escola_records(_workbook_path()):
        batch.append(
            Escola(
                id_escola=record["id_escola"],
                latitude=record["latitude"],
                longitude=record["longitude"],
            )
        )
        processed += 1
        if len(batch) >= 1000:
            Escola.objects.bulk_update(batch, ("latitude", "longitude"), batch_size=500)
            batch.clear()
            if processed % 50000 == 0:
                print(f"  {processed:,} coordenadas processadas", flush=True)
    if batch:
        Escola.objects.bulk_update(batch, ("latitude", "longitude"), batch_size=500)
    print(f"Coordenadas normalizadas para {processed:,} escolas.", flush=True)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [("core", "0003_import_escolas")]

    operations = [migrations.RunPython(normalize_coordinates, migrations.RunPython.noop)]

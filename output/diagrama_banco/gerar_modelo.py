import sys
import json
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from django.conf import settings
settings.configure(INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.admin', 'django.contrib.sessions', 'core'], DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}, SECRET_KEY='diagram-only', DEFAULT_AUTO_FIELD='django.db.models.BigAutoField', LANGUAGE_CODE='pt-br', USE_TZ=True)
import django
django.setup()
from django.apps import apps
from django.db.backends.postgresql.base import DatabaseWrapper
connection = DatabaseWrapper({'ENGINE': 'django.db.backends.postgresql', 'NAME': 'schema_only'})

OUT = Path(__file__).resolve().parent
models = [m for m in apps.get_models(include_auto_created=True) if not m._meta.proxy]
models.sort(key=lambda m: m._meta.db_table)
ids = {m: f'n{i}' for i, m in enumerate(models)}
esc = lambda s: html.escape(str(s), quote=True)
lines = ['digraph banco {', 'graph [rankdir=LR, bgcolor="white", pad=0.5, nodesep=0.45, ranksep=1.6, splines=polyline, outputorder=edgesfirst, fontname="Arial", fontsize=24, labelloc=t, label="PACTO EJA • Relacionamento do banco de dados\\nModelos Django atuais • Títulos: Meta.verbose_name\\nPK: chave primária | FK: chave estrangeira | UQ: único | ?: aceita NULL\\nLinhas: FK → PK • ponta simples = 1 • ponta em leque = muitos • intermediárias representam N:N"];', 'node [shape=plain, fontname="Arial"];', 'edge [color="#7695ad", penwidth=1.1, arrowsize=0.65];']
metadata = []
relations = []
for m in models:
    opt = m._meta
    auto = bool(opt.auto_created)
    title = str(opt.verbose_name)
    if auto:
        owner = opt.auto_created
        mf = next((f for f in owner._meta.many_to_many if f.remote_field.through is m), None)
        if mf:
            title = f'{owner._meta.verbose_name} / {mf.verbose_name}'
    color = '#edf4fb' if opt.app_label == 'core' else '#f3f0f8'
    if auto:
        color = '#f0f7f4'
    rows = [f'<TR><TD COLSPAN="3" ALIGN="LEFT" BGCOLOR="{color}"><FONT POINT-SIZE="14"><B>{esc(title)}</B></FONT></TD></TR>', f'<TR><TD COLSPAN="3" ALIGN="LEFT"><FONT COLOR="#516274" POINT-SIZE="10">public.{esc(opt.db_table)}</FONT></TD></TR>']
    fs = []
    for i, f in enumerate(opt.local_fields):
        flags = []
        if f.primary_key: flags.append('PK')
        if f.is_relation: flags.append('FK')
        if f.unique and not f.primary_key: flags.append('UQ')
        if f.null: flags.append('?')
        typ = f.db_type(connection) or f.get_internal_type()
        # SQL types shown in the PostgreSQL reference.
        if f.get_internal_type() in ('AutoField', 'BigAutoField'): typ = 'bigint' if f.get_internal_type() == 'BigAutoField' else 'integer'
        if f.get_internal_type() == 'JSONField': typ = 'jsonb'
        if f.get_internal_type() == 'BooleanField': typ = 'boolean'
        fg = '#a47c15' if f.primary_key else '#35749b' if f.is_relation else '#40505d'
        bg = '#ffffff' if i % 2 == 0 else '#fafcfd'
        flag_text = esc(' '.join(flags)) if flags else '&#160;'
        rows.append(f'<TR><TD ALIGN="LEFT" BGCOLOR="{bg}"><FONT COLOR="{fg}" POINT-SIZE="9">{flag_text}</FONT></TD><TD PORT="f{i}" ALIGN="LEFT" BGCOLOR="{bg}"><FONT POINT-SIZE="10">{esc(f.column)}</FONT></TD><TD ALIGN="LEFT" BGCOLOR="{bg}"><FONT COLOR="#73808c" POINT-SIZE="9">{esc(typ)}</FONT></TD></TR>')
        fs.append({'column': f.column, 'type': typ, 'flags': flags})
        if f.is_relation and f.remote_field.model in ids:
            target = f.remote_field.model
            ti = list(target._meta.local_fields).index(f.target_field)
            arrow = 'tee' if f.one_to_one else 'crow'
            relations.append(f'{ids[m]}:f{i} -> {ids[target]}:f{ti} [dir=both, arrowtail={arrow}, arrowhead=tee, tooltip="{esc(opt.db_table)}.{esc(f.column)} → {esc(target._meta.db_table)}.{esc(f.target_field.column)}"];')
    lines.append(f'{ids[m]} [label=<<TABLE BORDER="1" COLOR="#cbd6df" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5">{"".join(rows)}</TABLE>>];')
    metadata.append({'table': opt.db_table, 'verbose_name': str(opt.verbose_name), 'display_title': title, 'auto_created': auto, 'fields': fs})
lines[1] = lines[1].replace('splines=polyline', 'overlap=false, sep="+35", splines=true')
lines.extend(relations)
lines.append('}')
(OUT / 'modelo_relacionamentos.dot').write_text('\n'.join(lines), encoding='utf-8')
(OUT / 'modelo_metadados.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{len(models)} tabelas; {len(relations)} relacionamentos')

from pathlib import Path
import xml.etree.ElementTree as ET

root = ET.parse(Path(__file__).parent / 'modelo_relacionamentos.svg')
ns = {'s': 'http://www.w3.org/2000/svg'}
groups = root.findall('.//s:g', ns)
nodes = [g for g in groups if g.get('class') == 'node']
edges = [g for g in groups if g.get('class') == 'edge']
assert len(nodes) == 48 and len(edges) == 59
assert all(n.findall('.//s:text', ns) for n in nodes)
print('Verificado: 48 tabelas com texto e 59 linhas de relacionamento.')

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.join(__dirname, '../templates/reports_certificados.html'), 'utf8');
const script = template.match(/<script>\s*([\s\S]*?)<\/script>/)[1];

function verify(libraries) {
  const elements = new Map();
  const ready = [];
  const downloads = [];
  let exportedCsv = '';
  function element() {
    return {
      children: [], listeners: {}, hidden: true, value: '', textContent: '',
      set innerHTML(value) { this.html = value; this.children = []; },
      get innerHTML() { return this.html || ''; },
      appendChild(child) { this.children.push(child); },
      removeChild(child) { this.children = this.children.filter(item => item !== child); },
      addEventListener(type, callback) { this.listeners[type] = callback; },
      getAttribute() { return null; },
      getContext() { return {}; },
      setAttribute(name, value) { this[name] = value; },
      click() { downloads.push(this); },
      classList: { add() {}, remove() {} },
    };
  }
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    createElement: element,
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener(type, callback) { if (type === 'DOMContentLoaded') ready.push(callback); },
    body: element(), documentElement: element(),
  };
  for (const [, id] of template.matchAll(/json_script:"([^"]+)"/g)) {
    document.getElementById(id).textContent = '[]';
  }
  document.getElementById('participants-data').textContent = JSON.stringify([{
    nome: 'Educadora de Teste', cpf: '52998224725', email: 'teste@example.com',
    cursos_certificados: ['Curso de Teste'], sigla_uf_atuacao: 'PB',
    municipio_atuacao: 'João Pessoa', funcao: 'Formadora',
  }]);
  document.getElementById('course-chart-data').textContent = JSON.stringify([{ label: 'Curso de Teste', qtd: 1 }]);
  document.getElementById('chartMetricSelect').value = 'curso';
  const context = vm.createContext({
    document, console: { warn() {} },
    Blob: class { constructor(parts) { this.content = parts.join(''); } },
    URL: { createObjectURL(blob) { exportedCsv = blob.content; return 'blob:test'; } },
    ...libraries,
  });
  vm.runInContext(script, context);
  for (const callback of ready) callback();

  assert.match(document.getElementById('detailedTableBody').children[0].innerHTML, /Educadora de Teste/);
  assert.equal(document.getElementById('tableFilterCurso').children[0].value, 'Curso de Teste');
  assert.equal(document.getElementById('report-visualization-warning').hidden, false);
  assert.equal(typeof document.getElementById('tableSearchInput').listeners.input, 'function');

  document.getElementById('tableSearchInput').value = 'inexistente';
  document.getElementById('tableSearchInput').listeners.input();
  assert.match(document.getElementById('detailedTableBody').innerHTML, /Nenhum participante/);
  document.getElementById('tableSearchInput').value = 'Educadora';
  document.getElementById('tableSearchInput').listeners.input();
  vm.runInContext('exportFullCertificadosCSV()', context);
  assert.match(downloads[0].download, /^solicitacoes_certificados_/);
  assert.match(exportedCsv, /Educadora de Teste/);
}

verify({});
verify({ L: { map() { throw new Error('Falha do mapa'); } } });
verify({ Chart: function () { throw new Error('Falha do gráfico'); } });
console.log('OK: tabela, filtros e CSV funcionam sem bibliotecas externas e após falhas de visualização.');

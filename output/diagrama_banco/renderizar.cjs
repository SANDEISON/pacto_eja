const fs = require('fs');
const path = require('path');
const base = 'C:/Users/PactoEJA/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/';
const { instance } = require(base + '@viz-js/viz');
const sharp = require(base + 'sharp');
(async () => {
  const viz = await instance();
  const source = fs.readFileSync(path.join(__dirname, 'modelo_relacionamentos.dot'), 'utf8');
  const svg = viz.renderString(source, { format: 'svg', engine: 'neato' });
  const nodes = (svg.match(/class="node"/g) || []).length;
  const edges = (svg.match(/class="edge"/g) || []).length;
  if (nodes !== 48 || edges !== 59) throw new Error(`Incomplete diagram: ${nodes} nodes, ${edges} edges`);
  fs.writeFileSync(path.join(__dirname, 'modelo_relacionamentos.svg'), svg);
  await sharp(Buffer.from(svg), { density: 120, limitInputPixels: false }).png().toFile(path.join(__dirname, 'modelo_relacionamentos.png'));
  await sharp(Buffer.from(svg), { limitInputPixels: false }).resize({ width: 1900 }).png().toFile(path.join(__dirname, 'previa.png'));
  console.log(await sharp(path.join(__dirname, 'modelo_relacionamentos.png')).metadata());
})();




#!/usr/bin/env node
/*
 * Stage 2: force-directed layout using anvaka's ngraph stack.
 *   ngraph.graph      -> graph model
 *   ngraph.forcelayout -> the 2D force engine behind anvaka's visualizations
 *
 * Reads web/data/<p>_<l>.json (from preprocess.py), runs the layout, and writes
 * node positions back into the same JSON as "pos":[[x,y],...] plus a bounding box.
 */
const fs = require('fs');
const path = require('path');
const createGraph = require('ngraph.graph');
const createLayout = require('ngraph.forcelayout');

const ITER = parseInt(process.env.ITER || '400', 10);

function layoutFile(file) {
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  const g = createGraph();
  for (let i = 0; i < data.n; i++) g.addNode(i);
  for (const [a, b] of data.edges) g.addLink(a, b);

  const layout = createLayout(g, {
    dimensions: 2,
    springLength: 30,
    springCoefficient: 0.0008,
    gravity: -1.2,
    theta: 0.8,
    dragCoefficient: 0.02,
  });
  for (let s = 0; s < ITER; s++) layout.step();

  const pos = new Array(data.n);
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let i = 0; i < data.n; i++) {
    const p = layout.getNodePosition(i);
    pos[i] = [p.x, p.y];
    if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
  }
  data.pos = pos;
  data.bbox = [minX, minY, maxX, maxY];
  fs.writeFileSync(file, JSON.stringify(data));
  console.log(`laid out ${path.basename(file)}: V=${data.n} iters=${ITER}`);
}

const args = process.argv.slice(2);
let files = args.length
  ? args
  : fs.readdirSync(path.join(__dirname, '..', 'docs', 'data'))
      .filter((f) => f.endsWith('.json'))
      .map((f) => path.join(__dirname, '..', 'docs', 'data', f));
files.forEach(layoutFile);

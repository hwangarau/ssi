#!/usr/bin/env node
/*
 * Stage 2: symmetry-first layout on top of anvaka's ngraph stack.
 *
 * The spine (vertices with j in F_p) is placed DETERMINISTICALLY and pinned, in one
 * of three shapes chosen by preprocess.py:
 *     "ring"    -> spine spread evenly on a circle (no spine-spine edges)
 *     "line"    -> spine stacked vertically down the centre (spine is a single path)
 *     "generic" -> spine on a circle with chords (everything else)
 * Non-spine vertices are seeded on concentric shells by their graph-distance to the
 * spine (angles inherited from their BFS parent so siblings cluster), then relaxed
 * with ngraph.forcelayout while the spine stays pinned. Result: anvaka-style organic
 * layout, but anchored to a symmetric spine.
 */
const fs = require('fs');
const path = require('path');
const createGraph = require('ngraph.graph');
const createLayout = require('ngraph.forcelayout');

// Light relaxation: the concentric seed is already symmetric; a few steps just
// resolve local overlaps without destroying the structure.
const ITER = parseInt(process.env.ITER || '40', 10);
const SPINE_GAP = 52;   // spacing between adjacent spine vertices
const SHELL_GAP = 60;   // radial gap per distance level for non-spine
const SIB_ARC = 0.55;   // angular spread (rad) shared among a node's children

function buildAdj(n, edges) {
  const adj = Array.from({ length: n }, () => []);
  for (const [a, b] of edges) { adj[a].push(b); adj[b].push(a); }
  return adj;
}

function layoutFile(file) {
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  const { n, edges, dist } = data;
  const spine = data.spine;
  const order = data.spineOrder;
  const type = data.spineType || 'generic';
  const adj = buildAdj(n, edges);

  const pos = new Array(n).fill(null);
  const angle = new Array(n).fill(0);      // for circular seeding of children
  const K = order.length;

  // --- 1. place the spine deterministically ---
  if (type === 'line') {
    // vertical stack down the centre
    for (let k = 0; k < K; k++) {
      const id = order[k];
      pos[id] = [0, (k - (K - 1) / 2) * SPINE_GAP];
      angle[id] = pos[id][1] >= 0 ? Math.PI / 2 : -Math.PI / 2;
    }
  } else {
    // ring / generic: evenly on a circle. Radius keeps spine vertices from touching
    // AND stays comfortably inside the non-spine shells so it doesn't get crowded.
    const byCount = (K * SPINE_GAP) / (2 * Math.PI);
    const byDepth = 0.45 * Math.max(1, data.maxDist) * SHELL_GAP;
    const R = Math.max(70, byCount, byDepth);
    data._R = R;
    for (let k = 0; k < K; k++) {
      const id = order[k];
      const th = (2 * Math.PI * k) / Math.max(K, 1);
      angle[id] = th;
      pos[id] = [R * Math.cos(th), R * Math.sin(th)];
    }
  }

  // --- 2. BFS from spine to seed non-spine on concentric shells ---
  const parent = new Array(n).fill(-1);
  const seen = new Array(n).fill(false);
  const queue = [];
  for (const id of order) { seen[id] = true; queue.push(id); }
  const children = Array.from({ length: n }, () => []);
  for (let h = 0; h < queue.length; h++) {
    const u = queue[h];
    for (const v of adj[u]) {
      if (!seen[v]) { seen[v] = true; parent[v] = u; children[u].push(v); queue.push(v); }
    }
  }
  const R = data._R || 70;
  // assign positions in BFS order so parents are placed before children
  for (let h = 0; h < queue.length; h++) {
    const u = queue[h];
    const kids = children[u];
    for (let c = 0; c < kids.length; c++) {
      const v = kids[c];
      const spread = kids.length > 1 ? SIB_ARC * (c / (kids.length - 1) - 0.5) : 0;
      if (type === 'line') {
        // push outward to alternating sides, away from the central spine line
        const side = (h + c) % 2 === 0 ? 1 : -1;
        const baseY = pos[u][1];
        angle[v] = angle[u];
        pos[v] = [side * dist[v] * SHELL_GAP, baseY + spread * SHELL_GAP];
      } else {
        const th = angle[u] + spread;
        angle[v] = th;
        const r = R + dist[v] * SHELL_GAP;
        pos[v] = [r * Math.cos(th), r * Math.sin(th)];
      }
    }
  }
  // any vertex never reached (unreachable from spine) -> outer ring, even angles
  let stray = 0;
  for (let i = 0; i < n; i++) if (pos[i] === null) {
    const th = (2 * Math.PI * stray++) / Math.max(1, n);
    const r = R + (data.maxDist + 1) * SHELL_GAP;
    pos[i] = [r * Math.cos(th), r * Math.sin(th)];
  }

  // --- 3. relax non-spine with ngraph.forcelayout; keep spine pinned ---
  const g = createGraph();
  for (let i = 0; i < n; i++) g.addNode(i);
  for (const [a, b] of edges) g.addLink(a, b);
  const layout = createLayout(g, {
    dimensions: 2,
    springLength: SHELL_GAP,
    springCoefficient: 0.0006,
    gravity: -0.9,
    theta: 0.8,
    dragCoefficient: 0.04,
  });
  for (let i = 0; i < n; i++) layout.setNodePosition(i, pos[i][0], pos[i][1]);
  for (let i = 0; i < n; i++) if (spine[i]) layout.pinNode(g.getNode(i), true);
  for (let s = 0; s < ITER; s++) layout.step();

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const out = new Array(n);
  for (let i = 0; i < n; i++) {
    const p = layout.getNodePosition(i);
    out[i] = [p.x, p.y];
    if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
  }
  data.pos = out;
  data.bbox = [minX, minY, maxX, maxY];
  delete data._R;
  fs.writeFileSync(file, JSON.stringify(data));
  console.log(`laid out ${path.basename(file)}: V=${n} spine=${type} iters=${ITER}`);
}

const args = process.argv.slice(2);
let files = args.length
  ? args
  : fs.readdirSync(path.join(__dirname, '..', 'docs', 'data'))
      .filter((f) => f.endsWith('.json'))
      .map((f) => path.join(__dirname, '..', 'docs', 'data', f));
files.forEach(layoutFile);

'use strict';

// ---- viridis colormap (anchors; linear interpolation) ----
const VIRIDIS = [
  [68, 1, 84], [72, 40, 120], [62, 74, 137], [49, 104, 142], [38, 130, 142],
  [31, 158, 137], [53, 183, 121], [109, 205, 89], [180, 222, 44], [253, 231, 37],
];
function viridis(t) {
  t = Math.max(0, Math.min(1, t));
  const x = t * (VIRIDIS.length - 1);
  const i = Math.floor(x), f = x - i;
  const a = VIRIDIS[i], b = VIRIDIS[Math.min(i + 1, VIRIDIS.length - 1)];
  const r = Math.round(a[0] + (b[0] - a[0]) * f);
  const g = Math.round(a[1] + (b[1] - a[1]) * f);
  const bl = Math.round(a[2] + (b[2] - a[2]) * f);
  return `rgb(${r},${g},${bl})`;
}

const SPINE_COLOR = '#ff3b30';
const EDGE_COLOR = 'rgba(139,148,158,0.22)';

const els = {
  prime: document.getElementById('prime'),
  ell: document.getElementById('ell'),
  canvas: document.getElementById('graph'),
  stats: document.getElementById('stats'),
  title: document.getElementById('title'),
};
const ctx = els.canvas.getContext('2d');
let manifest = null;
let current = null; // loaded graph data

function metaFor(p, l) {
  return manifest.graphs.find((g) => g.p === p && g.l === l);
}

function populateEll(p) {
  const avail = manifest.graphs.filter((g) => g.p === p).map((g) => g.l)
    .sort((a, b) => a - b);
  const prev = parseInt(els.ell.value, 10);
  els.ell.innerHTML = '';
  for (const l of avail) {
    const o = document.createElement('option');
    o.value = l; o.textContent = `ℓ = ${l}`;
    els.ell.appendChild(o);
  }
  if (avail.includes(prev)) els.ell.value = prev;
}

async function load(p, l) {
  const res = await fetch(`data/${p}_${l}.json`);
  current = await res.json();
  location.hash = `p=${p}&l=${l}`;
  draw();
  showStats();
}

function draw() {
  const d = current;
  const cssW = els.canvas.clientWidth, cssH = els.canvas.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  els.canvas.width = cssW * dpr;
  els.canvas.height = cssH * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  const pos = d.pos;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of pos) {
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  const pad = 28;
  const spanX = maxX - minX || 1, spanY = maxY - minY || 1;
  const s = Math.min((cssW - 2 * pad) / spanX, (cssH - 2 * pad) / spanY);
  const offX = (cssW - s * spanX) / 2, offY = (cssH - s * spanY) / 2;
  const X = (x) => offX + (x - minX) * s;
  const Y = (y) => cssH - (offY + (y - minY) * s); // flip y

  // edges first
  ctx.strokeStyle = EDGE_COLOR;
  ctx.lineWidth = 0.6;
  ctx.beginPath();
  for (const [a, b] of d.edges) {
    ctx.moveTo(X(pos[a][0]), Y(pos[a][1]));
    ctx.lineTo(X(pos[b][0]), Y(pos[b][1]));
  }
  ctx.stroke();

  // non-spine nodes (shaded by distance), then spine on top
  const md = d.maxDist || 1;
  for (let i = 0; i < d.n; i++) {
    if (d.spine[i]) continue;
    ctx.fillStyle = viridis(md ? d.dist[i] / md : 0);
    ctx.beginPath();
    ctx.arc(X(pos[i][0]), Y(pos[i][1]), 2.6, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.fillStyle = SPINE_COLOR;
  ctx.strokeStyle = 'rgba(255,255,255,0.5)';
  ctx.lineWidth = 0.6;
  for (let i = 0; i < d.n; i++) {
    if (!d.spine[i]) continue;
    ctx.beginPath();
    ctx.arc(X(pos[i][0]), Y(pos[i][1]), 4.2, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
  }
}

function showStats() {
  const d = current;
  const nsp = d.spine.reduce((a, b) => a + (b ? 1 : 0), 0);
  els.title.textContent = `p = ${d.p}   ℓ = ${d.l}`;
  const maxCount = Math.max(...d.hist.map((h) => h[1]), 1);
  const rows = d.hist.map(([dist, cnt]) => {
    const w = Math.round((cnt / maxCount) * 100);
    const col = dist === 0 ? SPINE_COLOR : viridis(d.maxDist ? dist / d.maxDist : 0);
    return `<tr><td>${dist === 0 ? 'spine (d0)' : 'd' + dist}</td>
      <td class="bar"><span style="width:${w}%;background:${col}"></span></td>
      <td class="num">${cnt}</td></tr>`;
  }).join('');
  els.stats.innerHTML = `
    <div class="kv"><span>vertices</span><b>${d.n}</b></div>
    <div class="kv"><span>spine (j &isin; F_p)</span><b>${nsp}</b></div>
    <div class="kv"><span>max distance</span><b>${d.maxDist}</b></div>
    <div class="kv"><span>spine shape</span><b>${d.spineType}</b></div>
    <div class="kv"><span>edges</span><b>${d.edges.length}</b></div>
    <h3>vertices at each distance to spine</h3>
    <table class="hist">${rows}</table>`;
}

function readHash() {
  const m = /p=(\d+)&l=(\d+)/.exec(location.hash);
  return m ? { p: +m[1], l: +m[2] } : null;
}

async function main() {
  manifest = await (await fetch('manifest.json')).json();
  for (const p of manifest.primes) {
    const o = document.createElement('option');
    o.value = p; o.textContent = `p = ${p}`;
    els.prime.appendChild(o);
  }
  const want = readHash() || { p: manifest.primes[0], l: 2 };
  els.prime.value = want.p;
  populateEll(want.p);
  if (metaFor(want.p, want.l)) els.ell.value = want.l;

  els.prime.addEventListener('change', () => {
    const p = +els.prime.value;
    populateEll(p);
    load(p, +els.ell.value);
  });
  els.ell.addEventListener('change', () => load(+els.prime.value, +els.ell.value));
  window.addEventListener('resize', () => current && draw());

  load(+els.prime.value, +els.ell.value);
}
main();

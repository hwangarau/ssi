#!/usr/bin/env python3
"""Stage 1: turn an isogeny-graph .npz + nodes.txt into a compact graph.json.

Conventions (verified against the Isogeny Database, Florit & Finol, Zenodo 4304044):
  graphs/<p>/<p>_<l>.npz   scipy CSR, shape (n,n), entries = isogeny multiplicities,
                           out-regular (row sum = l+1), DIRECTED in general.
  graphs/<p>/<p>_nodes.txt one j-invariant per line; line k == vertex k.
                           A line that is a plain integer  -> j in F_p   -> SPINE.
                           A line of the form "a*z + b"     -> j in F_p^2 -> non-spine.

We symmetrize (A = A.maximum(A.T)), treat the graph as undirected & unweighted, and
compute each vertex's distance to the NEAREST spine vertex in one vectorized
multi-source Dijkstra/BFS pass.
"""
import sys, os, re, json, glob
import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra


def is_spine(j_line: str) -> bool:
    """Spine <=> j-invariant lies in F_p <=> its string has no field generator 'z'."""
    return "z" not in j_line


def load_nodes(nodes_path):
    with open(nodes_path) as f:
        lines = [ln.strip() for ln in f if ln.strip() != ""]
    return lines


def classify_spine(spine_idx, edges):
    """Classify the induced spine subgraph into one of three layout cases.

    Returns (spine_type, spine_order) where spine_order lists the spine vertex
    indices in the order they should be drawn:
      "ring"    -> no edges among spine vertices: place evenly on a circle.
      "line"    -> spine vertices form a single path: stack them down the centre,
                   spine_order following the path from one endpoint to the other.
      "generic" -> anything else (cycles, branching, mixed): generic circular layout.
    """
    sset = set(spine_idx)
    adj = {i: set() for i in spine_idx}
    for a, b in edges:
        if a in sset and b in sset:
            adj[a].add(b)
            adj[b].add(a)
    S = len(spine_idx)
    Es = sum(len(v) for v in adj.values()) // 2
    deg = {i: len(adj[i]) for i in spine_idx}
    maxdeg = max(deg.values()) if deg else 0

    if S <= 1:
        return "line", list(spine_idx)
    if Es == 0:
        return "ring", list(spine_idx)

    # connected over all spine vertices?
    start = spine_idx[0]
    seen = {start}
    stack = [start]
    while stack:
        x = stack.pop()
        for y in adj[x]:
            if y not in seen:
                seen.add(y)
                stack.append(y)
    connected = len(seen) == S

    if connected and Es == S - 1 and maxdeg <= 2:
        # a single path: order it from an endpoint (degree 1)
        ends = [i for i in spine_idx if deg[i] == 1]
        cur = ends[0] if ends else spine_idx[0]
        prev, order = None, [cur]
        while len(order) < S:
            nxt = [y for y in adj[cur] if y != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            order.append(cur)
        if len(order) == S:
            return "line", order

    return "generic", list(spine_idx)


def process(npz_path, out_dir):
    m = re.search(r"(\d+)[/\\](\d+)_(\d+)\.npz$", npz_path.replace("\\", "/"))
    if not m:
        m = re.search(r"(\d+)_(\d+)\.npz$", os.path.basename(npz_path))
        p, l = int(m.group(1)), int(m.group(2))
        nodes_path = os.path.join(os.path.dirname(npz_path), f"{p}_nodes.txt")
    else:
        p, l = int(m.group(2)), int(m.group(3))
        nodes_path = os.path.join(os.path.dirname(npz_path), f"{p}_nodes.txt")

    A = sp.load_npz(npz_path)
    n = A.shape[0]
    j_lines = load_nodes(nodes_path)
    assert len(j_lines) == n, f"{npz_path}: {len(j_lines)} node lines != {n} matrix rows"

    spine_mask = np.array([is_spine(j) for j in j_lines], dtype=bool)
    spine_idx = np.where(spine_mask)[0]

    # Undirected, unweighted adjacency (drop self-loops for layout/edges).
    S = A.maximum(A.T).tocoo()
    keep = S.row != S.col
    rows, cols = S.row[keep], S.col[keep]
    # boolean off-diagonal sparse for distances
    B = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))

    if len(spine_idx) > 0:
        dist = dijkstra(B, directed=False, unweighted=True,
                        indices=spine_idx, min_only=True)
    else:
        dist = np.full(n, np.inf)
    # unreachable -> outermost ring (max finite + 1), recorded as -1 originally
    finite = dist[np.isfinite(dist)]
    max_finite = int(finite.max()) if finite.size else 0
    dist_out = np.where(np.isfinite(dist), dist, max_finite + 1).astype(int)

    # undirected edge list i<j, deduped, no self loops
    e = set()
    for i, jx in zip(rows.tolist(), cols.tolist()):
        a, b = (i, jx) if i < jx else (jx, i)
        e.add((a, b))
    edges = sorted(e)

    # Sanity: every edge joins vertices whose spine-distance differs by <= 1.
    bad = [(i, jx) for (i, jx) in edges if abs(dist_out[i] - dist_out[jx]) > 1]
    if bad:
        print(f"  WARNING p={p} l={l}: {len(bad)} edges span >1 ring (e.g. {bad[:3]})",
              file=sys.stderr)

    hist = {}
    for d in dist_out.tolist():
        hist[d] = hist.get(d, 0) + 1

    spine_type, spine_order = classify_spine(spine_idx.tolist(), edges)
    hist_pairs = [[d, hist[d]] for d in sorted(hist)]

    out = {
        "p": p, "l": l, "n": int(n),
        "spine": spine_mask.tolist(),
        "dist": dist_out.tolist(),
        "maxDist": int(dist_out.max()) if n else 0,
        "edges": edges,
        "spineType": spine_type,
        "spineOrder": spine_order,
        "hist": hist_pairs,
    }
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{p}_{l}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, separators=(",", ":"))

    nsp = int(spine_mask.sum())
    hist_str = " ".join(f"d{d}:{hist[d]}" for d in sorted(hist))
    print(f"p={p:>5} l={l:>2}: V={n:<5} spine={nsp:<5} maxDist={out['maxDist']:<3} "
          f"edges={len(edges):<6} spine={spine_type:<7} [{hist_str}]")
    return out_path


def main():
    args = sys.argv[1:]
    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "data")
    # Treat every argument as an npz path or glob; default to all graphs.
    paths = []
    for a in (args or ["../graphs/*/*.npz"]):
        hits = glob.glob(a)
        paths.extend(hits if hits else ([a] if os.path.exists(a) else []))
    for pth in sorted(set(paths)):
        process(pth, out_dir)


if __name__ == "__main__":
    main()

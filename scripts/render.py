#!/usr/bin/env python3
"""Stage 3: render a force-laid-out graph.json to a static PNG.

Edges are drawn first as one LineCollection (thin, low alpha) for speed; nodes are
scattered on top. Spine vertices (j in F_p) use one color; non-spine vertices use a
second color, lightly shaded by graph-distance to the nearest spine vertex.
"""
import sys, os, json, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

SPINE_COLOR = "#ff3b30"     # red
NONSPINE_CMAP = "viridis"   # shaded by distance to spine


def render(json_path, out_dir):
    d = json.load(open(json_path))
    if "pos" not in d:
        print(f"  skip {os.path.basename(json_path)}: no positions (run layout.js)",
              file=sys.stderr)
        return None
    pos = np.array(d["pos"], dtype=float)
    spine = np.array(d["spine"], dtype=bool)
    dist = np.array(d["dist"], dtype=float)
    edges = d["edges"]
    p, l, n = d["p"], d["l"], d["n"]

    fig, ax = plt.subplots(figsize=(9, 9), dpi=140)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    if edges:
        segs = [[pos[a], pos[b]] for a, b in edges]
        lc = LineCollection(segs, colors="#8b949e", linewidths=0.4, alpha=0.25,
                            zorder=1)
        ax.add_collection(lc)

    # non-spine: shaded by distance; spine: solid color, larger, on top
    ns = ~spine
    if ns.any():
        ax.scatter(pos[ns, 0], pos[ns, 1], c=dist[ns], cmap=NONSPINE_CMAP,
                   s=14, linewidths=0, zorder=2)
    if spine.any():
        ax.scatter(pos[spine, 0], pos[spine, 1], c=SPINE_COLOR,
                   s=34, edgecolors="white", linewidths=0.4, zorder=3)

    ax.set_aspect("equal")
    ax.axis("off")
    nsp = int(spine.sum())
    ax.set_title(f"p = {p}   ℓ = {l}    V = {n}   spine = {nsp}",
                 color="#e6edf3", fontsize=13, pad=12)
    fig.tight_layout()

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{p}_{l}.png")
    fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"rendered {os.path.basename(out_path)}")
    return out_path


def main():
    args = sys.argv[1:]
    here = os.path.dirname(__file__)
    out_dir = os.path.join(here, "..", "docs", "img")
    if args:
        files = []
        for a in args:
            files.extend(glob.glob(a))
    else:
        files = sorted(glob.glob(os.path.join(here, "..", "docs", "data", "*.json")))
    for f in files:
        render(f, out_dir)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build docs/manifest.json: the index the interactive picker loads.

One entry per computed graph with the stats shown in the UI (including the count of
vertices at each distance to the spine). Re-run after adding graphs.
"""
import os, json, glob

HERE = os.path.dirname(__file__)
DOCS = os.path.join(HERE, "..", "docs")


def main():
    graphs = []
    primes = set()
    for jp in sorted(glob.glob(os.path.join(DOCS, "data", "*.json"))):
        d = json.load(open(jp))
        primes.add(d["p"])
        graphs.append({
            "p": d["p"],
            "l": d["l"],
            "n": d["n"],
            "spine": int(sum(d["spine"])),
            "maxDist": d["maxDist"],
            "spineType": d["spineType"],
            "hist": d.get("hist", []),
        })
    graphs.sort(key=lambda g: (g["p"], g["l"]))
    ells = sorted({g["l"] for g in graphs})
    manifest = {
        "primes": sorted(primes),
        "ells": ells,
        "count": len(graphs),
        "graphs": graphs,
    }
    out = os.path.join(DOCS, "manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, separators=(",", ":"))
    print(f"wrote {out}: {len(graphs)} graphs over {len(primes)} primes, ell={ells}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stage 4: build docs/index.html — a static gallery of every rendered graph.

Scans docs/data/*.json + docs/img/*.png and writes a self-contained dark-theme
page (no JS framework). Re-run after adding graphs.
"""
import os, json, glob, html

HERE = os.path.dirname(__file__)
DOCS = os.path.join(HERE, "..", "docs")


def main():
    metas = []
    for jp in sorted(glob.glob(os.path.join(DOCS, "data", "*.json"))):
        d = json.load(open(jp))
        img = f"img/{d['p']}_{d['l']}.png"
        if os.path.exists(os.path.join(DOCS, img)):
            metas.append((d, img))
    # sort by prime then degree
    metas.sort(key=lambda t: (t[0]["p"], t[0]["l"]))

    cards = []
    for d, img in metas:
        nsp = sum(d["spine"])
        hist = {}
        for x in d["dist"]:
            hist[x] = hist.get(x, 0) + 1
        hist_str = ", ".join(f"d{k}:{hist[k]}" for k in sorted(hist))
        cards.append(f"""
      <figure class="card">
        <a href="{img}"><img loading="lazy" src="{img}" alt="p={d['p']} l={d['l']}"></a>
        <figcaption>
          <span class="pl">p = {d['p']} &nbsp; &#8467; = {d['l']}
            <em class="type">{d.get('spineType','')}</em></span>
          <span class="stat">V={d['n']} &middot; spine={nsp} &middot; maxDist={d['maxDist']}</span>
          <span class="hist">{html.escape(hist_str)}</span>
        </figcaption>
      </figure>""")

    primes = sorted({d["p"] for d, _ in metas})
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Supersingular Isogeny Graphs</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; background:#0d1117; color:#e6edf3;
         font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  header {{ padding:2rem 1.5rem 1rem; max-width:1100px; margin:0 auto; }}
  h1 {{ margin:0 0 .3rem; font-size:1.6rem; }}
  p.sub {{ margin:.2rem 0; color:#8b949e; line-height:1.5; }}
  a {{ color:#58a6ff; }}
  .legend {{ display:flex; gap:1.2rem; margin:.8rem 0; flex-wrap:wrap; font-size:.9rem; }}
  .legend span::before {{ content:""; display:inline-block; width:.7rem; height:.7rem;
         border-radius:50%; margin-right:.4rem; vertical-align:middle; }}
  .spine::before {{ background:#ff3b30; }}
  .nonspine::before {{ background:#21918c; }}
  .grid {{ display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
          max-width:1100px; margin:1rem auto 4rem; padding:0 1.5rem; }}
  .card {{ margin:0; background:#161b22; border:1px solid #30363d; border-radius:10px;
          overflow:hidden; }}
  .card img {{ width:100%; display:block; background:#0d1117; }}
  figcaption {{ padding:.6rem .8rem; display:flex; flex-direction:column; gap:.15rem; }}
  .pl {{ font-weight:600; }}
  .type {{ float:right; font-style:normal; font-size:.72rem; color:#0d1117;
          background:#58a6ff; border-radius:4px; padding:.05rem .4rem; }}
  .stat {{ color:#8b949e; font-size:.85rem; }}
  .hist {{ color:#6e7681; font-size:.78rem; font-family:ui-monospace,monospace; }}
  footer {{ max-width:1100px; margin:0 auto 3rem; padding:0 1.5rem; color:#6e7681;
           font-size:.82rem; }}
</style>
</head>
<body>
<header>
  <h1>Supersingular Isogeny Graphs</h1>
  <p class="sub">Force-directed layouts (anvaka's
    <a href="https://github.com/anvaka/ngraph.forcelayout">ngraph.forcelayout</a>)
    of supersingular &#8467;-isogeny graphs over &#120125;<sub>p&sup2;</sub>.
    Data: the <a href="https://zenodo.org/records/4304044">Isogeny Database</a>
    (Florit &amp; Finol, ODC-BY).</p>
  <p class="sub">The <b>spine</b> is the set of vertices whose j-invariant lies in
    &#120125;<sub>p</sub>; other vertices are shaded by graph distance to the
    nearest spine vertex.</p>
  <div class="legend">
    <span class="spine">spine (j &isin; &#120125;<sub>p</sub>)</span>
    <span class="nonspine">non-spine (shaded by distance to spine)</span>
  </div>
  <p class="sub">{len(metas)} graphs &middot; primes: {", ".join(map(str, primes))}</p>
</header>
<main class="grid">{''.join(cards)}
</main>
<footer>
  Built with a Python (numpy/scipy) &rarr; anvaka ngraph.forcelayout &rarr; matplotlib
  pipeline. Source in <code>/scripts</code>.
</footer>
</body>
</html>
"""
    out = os.path.join(DOCS, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {out} ({len(metas)} cards)")


if __name__ == "__main__":
    main()

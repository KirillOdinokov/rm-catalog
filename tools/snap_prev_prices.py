# -*- coding: utf-8 -*-
"""Снимок старых цен из собранного dist (до пересборки) для отчёта о повышении."""
import json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(BASE, "dist")
OUT = os.path.join(BASE, "data", "prices_prev_snapshot.json")

pat = re.compile(r'class="prod__price">([\d\s\xa0]+)\s*<small>')
found = {}
for fn in os.listdir(DIST):
    if not fn.endswith(".html") or fn in ("index.html", "404.html"):
        continue
    html = open(os.path.join(DIST, fn), encoding="utf-8").read()
    m = pat.search(html)
    if m:
        found[fn[:-5]] = int(re.sub(r"\D", "", m.group(1)))
json.dump(found, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("страниц с ценой:", len(found), "->", OUT)
print(list(found.items())[:5])

# -*- coding: utf-8 -*-
"""Печать разобранного прайса для проверки."""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(BASE, "data", "prices.json"), encoding="utf-8"))
print(d["stats"])
cur = None
for it in d["items"]:
    sec = " / ".join(it["section"])
    if sec != cur:
        print("\n### " + sec)
        cur = sec
    p = it["packs"][0]
    pr = p["retail"]
    fmt = (lambda v: "—" if v is None else "{:,.2f}".format(v).replace(",", " "))
    extra = " ".join(it.get(k, "") for k in ("width", "thickness") if it.get(k))
    print(f"  [{it['sheet'][:12]:<12} {it['row']:>3}] {it['name'][:58]:<58} | {p['pack'][:34]:<34} | {extra:<16} | {fmt(pr):>10} {fmt(p['t3']):>10} {fmt(p['t10']):>10} {fmt(p['dist']):>10}"
          + (f"  (+{len(it['packs'])-1} упак.)" if len(it["packs"]) > 1 else ""))

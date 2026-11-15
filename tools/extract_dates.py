# -*- coding: utf-8 -*-
"""Даты статей из дампа БД -> data/post_dates.json (для Article и sitemap)."""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL = os.path.join(BASE, "data", "_db", "rex.sql")
OUT = os.path.join(BASE, "data", "post_dates.json")

src = io.open(SQL, encoding="utf-8", errors="replace").read()
ns = {"__file__": __file__}
exec(compile(io.open(os.path.join(BASE, "tools", "export_unpublished.py"), encoding="utf-8")
             .read().split("def strip_blocks")[0], "eu", "exec"), ns)
rows = ns["table_rows"]("posts")

dates = {}
for r in rows:
    if len(r) < 21 or r[20] != "post" or r[7] != "publish":
        continue
    d = (r[2] or "").strip()
    m = (r[14] or "").strip()
    if d and d != "0000-00-00 00:00:00":
        dates[r[11]] = {"published": d.split(" ")[0],
                        "modified": (m.split(" ")[0] if m and not m.startswith("0000") else d.split(" ")[0])}

io.open(OUT, "w", encoding="utf-8").write(json.dumps(dates, ensure_ascii=False, indent=1))
print("статей с датой:", len(dates), "->", OUT)
ys = sorted(v["published"] for v in dates.values())
print("диапазон:", ys[0], "—", ys[-1])

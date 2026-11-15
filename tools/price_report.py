# -*- coding: utf-8 -*-
"""Отчёт: старые цены (снимок dist) vs новые (model.json) + список позиций прайса."""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
prev = json.load(open(os.path.join(BASE, "data", "prices_prev_snapshot.json"), encoding="utf-8"))
model = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
prices = json.load(open(os.path.join(BASE, "data", "prices.json"), encoding="utf-8"))

rows, up, down, newp = [], 0, 0, 0
for p in model["products"]:
    old = prev.get(p["slug"], 0)
    new = p.get("price") or 0
    if not old and not new:
        continue
    d = (new - old) / old * 100 if old else None
    if old and new and new > old:
        up += 1
    elif old and new and new < old:
        down += 1
    elif not old and new:
        newp += 1
    rows.append(dict(slug=p["slug"], name=p["name"], old=old, new=new,
                     delta_pct=(round(d, 1) if d is not None else None),
                     pack=p.get("pack", ""), unit=p.get("unit", ""),
                     sku=p.get("sku", "")))
rows.sort(key=lambda r: -(r["delta_pct"] or 0))
json.dump(rows, open(os.path.join(BASE, "data", "price_sync.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("позиций с ценой: %d | подорожали: %d | подешевели: %d | появилась цена: %d" % (len(rows), up, down, newp))
print("%-36s %8s %8s %7s" % ("slug", "было", "стало", "Δ%"))
for r in rows:
    print("%-36s %8s %8s %7s" % (r["slug"][:36], r["old"] or "—", r["new"] or "—",
                                 ("%+.1f%%" % r["delta_pct"]) if r["delta_pct"] is not None else "new"))

# --- покрытие прайса каталогом
site = {r["slug"] for r in rows}
items = prices["items"]
print("\nпрайс: позиций %d, с ценой %d" % (len(items), prices["stats"]["priced"]))

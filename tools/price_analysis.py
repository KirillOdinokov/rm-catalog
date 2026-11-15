# -*- coding: utf-8 -*-
"""Аналитика прайса: структура скидок, ₽/кг по разделам, запросные позиции."""
import json, os, re, statistics, sys
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(BASE, "data", "prices.json"), encoding="utf-8"))
items = d["items"]

# --- структура скидок
triples = Counter()
for it in items:
    for pk in it["packs"]:
        if not pk["retail"]:
            continue
        t3 = (pk["t3"] / pk["retail"]) if pk["t3"] else None
        t10 = (pk["t10"] / pk["retail"]) if pk["t10"] else None
        dist = (pk["dist"] / pk["retail"]) if pk["dist"] else None
        key = (round(t3, 3) if t3 else None, round(t10, 3) if t10 else None, round(dist, 3) if dist else None)
        triples[key] += 1
print("ТРОЙКИ МНОЖИТЕЛЕЙ (t3, t10, dist) -> сколько позиций:")
for k, n in triples.most_common(12):
    print("  %-28s %d" % (str(k), n))

# --- вес из упаковки
W = re.compile(r"(\d+(?:[.,]\d+)?)\s*кг")
KG = re.compile(r"(\d+(?:[.,]\d+)?)\s*кг")
per_kg = defaultdict(list)
for it in items:
    pk = it["packs"][0]
    if not pk["retail"]:
        continue
    m = KG.search(pk["pack"])
    if not m:
        continue
    w = float(m.group(1).replace(",", "."))
    if w < 0.2 or w > 1200:
        continue
    per_kg[it["section"][0] if it["section"] else "?"].append(pk["retail"] / w)
print("\n₽/кг (розница) по разделам:")
for sec, vals in sorted(per_kg.items(), key=lambda kv: -statistics.median(kv[1])):
    print("  %-62s n=%-3d медиана %6.0f  min %5.0f  max %6.0f"
          % (sec[:62], len(vals), statistics.median(vals), min(vals), max(vals)))

# --- по запросу
print("\nПО ЗАПРОСУ (%d позиций):" % sum(1 for it in items if not any(p["retail"] for p in it["packs"])))
cnt = Counter(it["section"][0] if it["section"] else "?" for it in items
              if not any(p["retail"] for p in it["packs"]))
for sec, n in cnt.most_common():
    print("  %-70s %d" % (sec[:70], n))

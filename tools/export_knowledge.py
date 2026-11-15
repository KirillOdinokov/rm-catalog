# -*- coding: utf-8 -*-
"""Выгрузка прайс-листа ТД РЕКС в базу знаний E:\\Оптимизация\\Knowledge\\rex.moscow.

Пишет:
  price_items.csv   — все позиции, по строке на вариант упаковки, 4 уровня цен
  price_tech.csv    — технические параметры, извлечённые из описаний
  price_stats.json  — статистика для README
"""
import csv
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES = os.path.join(BASE, "data", "prices.json")
OUT = r"E:\Оптимизация\Knowledge\rex.moscow"
os.makedirs(OUT, exist_ok=True)

d = json.load(open(PRICES, encoding="utf-8"))
items = d["items"]

# ---------------------------------------------------------------- items.csv
rows = []
for it in items:
    sec = it["section"] + [""] * (2 - len(it["section"]))
    for i, pk in enumerate(it["packs"]):
        rows.append({
            "лист": it["sheet"],
            "раздел": it["section"][0] if it["section"] else "",
            "подраздел": it["section"][1] if len(it["section"]) > 1 else "",
            "наименование": it["name"],
            "упаковка": pk["pack"],
            "ед": pk["unit"] or it["unit"],
            "цена_розница": pk["retail"] if pk["retail"] is not None else "",
            "цена_от3т": pk["t3"] if pk["t3"] is not None else "",
            "цена_от10т": pk["t10"] if pk["t10"] is not None else "",
            "цена_дистрибьютор": pk["dist"] if pk["dist"] is not None else "",
            "ширина_мм": it.get("width", ""),
            "толщина_мм": it.get("thickness", ""),
            "компоненты": "; ".join(it.get("components") or []),
            "описание": it["desc"],
        })
with open(os.path.join(OUT, "price_items.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(rows)
print("price_items.csv: строк %d" % len(rows))

# ---------------------------------------------------------------- tech.csv
FROST = re.compile(r"F[₂2]?\s*\u2080?\s*(\d{2,3})|F\s*(\d{2,3})")
WATER = re.compile(r"\bW\s*(\d{1,2})\b")
COMPR = re.compile(r"(?:прочность на сжатие|на сжатие)[^\d]{0,60}?(\d{2,3})\s*МПа", re.I)
FLEX = re.compile(r"на изгиб[^\d]{0,40}?(\d{1,3}(?:[.,]\d)?)\s*МПа", re.I)
ADH = re.compile(r"на отрыв[^\d]{0,40}?(\d(?:[.,]\d)?)\s*МПа", re.I)
RASHOD = re.compile(r"Расход[^.]{0,160}", re.I)
LAYER = re.compile(r"толщин[а-я]*\s*(?:нанесения|заливки|слоя)[^.]{0,60}", re.I)
LIFE = re.compile(r"Жизнеспособность[^.]{0,80}", re.I)
MAXF = re.compile(r"заполнитель[^.]{0,40}", re.I)

tech = []
for it in items:
    desc = it["desc"] or ""
    if not desc:
        continue
    def first(rx, flags=0):
        m = rx.search(desc)
        if not m:
            return ""
        return next((g for g in m.groups() if g), "") if m.groups() else m.group(0)
    frost = ""
    ms = FROST.findall(desc)
    if ms:
        vals = [int(a or b) for a, b in ms if (a or b)]
        if vals:
            frost = "F%s" % max(vals)
    water = WATER.findall(desc)
    pk = it["packs"][0]
    tech.append({
        "наименование": it["name"],
        "раздел": " / ".join(it["section"]),
        "упаковка": pk["pack"],
        "цена_розница": pk["retail"] if pk["retail"] is not None else "",
        "морозостойкость": frost,
        "водонепроницаемость": ("W%s" % max(int(x) for x in water)) if water else "",
        "прочность_сжатие_МПа": first(COMPR),
        "прочность_изгиб_МПа": first(FLEX),
        "адгезия_отрыв_МПа": first(ADH),
        "макс_заполнитель": (MAXF.search(desc).group(0)[:60] if MAXF.search(desc) else ""),
        "расход": (RASHOD.search(desc).group(0)[:200] if RASHOD.search(desc) else ""),
        "толщина_слоя": (LAYER.search(desc).group(0)[:120] if LAYER.search(desc) else ""),
        "жизнеспособность": (LIFE.search(desc).group(0)[:100] if LIFE.search(desc) else ""),
        "описание": desc,
    })
with open(os.path.join(OUT, "price_tech.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(tech[0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(tech)
print("price_tech.csv: строк %d (из них с F/W: %d)"
      % (len(tech), sum(1 for t in tech if t["морозостойкость"] or t["водонепроницаемость"])))

# ---------------------------------------------------------------- статистика
priced = [it for it in items if it["packs"][0]["retail"]]
ratios = defaultdict(list)
for it in items:
    for pk in it["packs"]:
        if not pk["retail"]:
            continue
        for lvl in ("t3", "t10", "dist"):
            if pk[lvl]:
                ratios[lvl].append(pk[lvl] / pk["retail"])

def stat(vals):
    return {"n": len(vals), "min": round(min(vals), 4), "median": round(statistics.median(vals), 4),
            "max": round(max(vals), 4)} if vals else None

by_section = Counter(it["section"][0] for it in items)
by_sheet = Counter(it["sheet"] for it in items)
pack_words = Counter()
for it in items:
    for pk in it["packs"]:
        low = pk["pack"].lower()
        for word in ("меш", "ведро", "канистра", "комплект", "бочка", "барабан", "рулон",
                     "картридж", "канистры", "биг-бэг", "коробка", "куб", "цистерн", "п.м."):
            if word in low:
                pack_words[word] += 1
                break

stats = {
    "source": d["source_file"],
    "valid_from": d["valid_from"],
    "items": len(items),
    "packs": sum(len(i["packs"]) for i in items),
    "priced": sum(1 for i in items if any(p["retail"] for p in i["packs"])),
    "on_request": sum(1 for i in items if not any(p["retail"] for p in i["packs"])),
    "by_sheet": dict(by_sheet),
    "by_section": dict(by_section.most_common()),
    "level_ratios": {k: stat(v) for k, v in ratios.items()},
    "pack_types": dict(pack_words.most_common()),
    "price_min": min(p["retail"] for i in items for p in i["packs"] if p["retail"]),
    "price_max": max(p["retail"] for i in items for p in i["packs"] if p["retail"]),
}
json.dump(stats, open(os.path.join(OUT, "price_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(json.dumps({k: stats[k] for k in ("items", "packs", "priced", "on_request", "price_min", "price_max")},
                 ensure_ascii=False, indent=1))
print("уровни (медиана к рознице):", json.dumps(stats["level_ratios"], ensure_ascii=False))
print("разделы:", json.dumps(by_section.most_common(), ensure_ascii=False))

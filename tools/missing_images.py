# -*- coding: utf-8 -*-
"""Список товаров каталога без изображения -> missing-images-rex.csv в корне проекта.

Колонки: №; артикул; товар; раздел; подраздел; цена; фасовка; url; статус цены.
Разделитель `;`, кодировка UTF-8 с BOM — открывается в Excel двойным щелчком.
"""
import csv
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "missing-images-rex.csv")


def main():
    model = json.load(io.open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
    man = json.load(io.open(os.path.join(BASE, "data", "images.json"), encoding="utf-8"))
    have = set(man.get("products", {}))
    cats = {c["slug"]: c for c in model["cats"]}
    roots = {c["slug"]: c for c in model["cats"] if not c["parent"]}

    def chain(p):
        rows = [cats[s] for s in p["cats"] if s in cats]
        if not rows:
            return "", ""
        best = max(rows, key=lambda c: _depth(c))
        top = best
        while top.get("parent"):
            top = next(c for c in model["cats"] if c["id"] == top["parent"])
        return top["name"], (best["name"] if best["id"] != top["id"] else "")

    def _depth(c):
        d = 0
        while c.get("parent"):
            c = next(x for x in model["cats"] if x["id"] == c["parent"])
            d += 1
        return d

    rows = []
    for p in model["products"]:
        if p["slug"] in have:
            continue
        top, sub = chain(p)
        rows.append([
            len(rows) + 1,
            p.get("sku") or "",
            p["name"],
            top,
            sub,
            p["price"] if p.get("price") else "по запросу",
            p.get("pack") or "",
            "https://rex.moscow/" + p["slug"],
            {"retail": "розница (с НДС)"}.get(p.get("price_level") or "", "—"),
        ])

    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["№", "артикул", "товар", "раздел", "подраздел", "цена, ₽",
                    "фасовка", "url", "уровень цены"])
        w.writerows(rows)

    total = len(model["products"])
    print("товаров в каталоге: %d" % total)
    print("с изображением: %d" % len(have))
    print("без изображения: %d" % len(rows))
    print("файл:", OUT)
    from collections import Counter
    for k, v in Counter(r[3] for r in rows).most_common():
        print("  %-32s %d" % (k or "(без раздела)", v))


if __name__ == "__main__":
    main()

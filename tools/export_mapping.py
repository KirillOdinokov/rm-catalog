#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""export_mapping.py — карта соответствия «карточка сайта → строка прайса».

Источники: tools\apply_prices.py (словарь MAP), data\prices.json, data\model.json.
Выход:    mapping.md в корне проекта (пересобирается, руками не правится).

Запуск: python tools\export_mapping.py
"""
import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "tools"))

from apply_prices import MAP  # noqa: E402  (импорт безопасен: main() под __main__)

OUT = os.path.join(BASE, "mapping.md")


def money(v):
    if v in (None, "", 0):
        return "—"
    return "{:,}".format(int(round(float(v)))).replace(",", " ")


def main():
    model = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
    prices = json.load(open(os.path.join(BASE, "data", "prices.json"), encoding="utf-8"))

    items = {}
    for it in prices["items"]:
        items[(it["sheet"], it["row"])] = it

    prods = {p["slug"]: p for p in model["products"]}
    rows, miss, problems = [], [], []
    used = set()

    for slug, (sheet, row, variant) in MAP.items():
        p = prods.get(slug)
        it = items.get((sheet, row))
        if not p:
            problems.append((slug, sheet, row, "карточки на сайте нет"))
            continue
        if not it:
            problems.append((slug, sheet, row, "строки нет в prices.json"))
            continue
        used.add((sheet, row))
        packs = it.get("packs") or []
        pk = packs[variant] if variant < len(packs) else (packs[0] if packs else {})
        pr_ret = pk.get("retail")
        site_pr = p.get("price") or 0
        if not pr_ret:
            status = "в прайсе без цены"
        elif site_pr and abs(float(site_pr) - float(pr_ret)) < 1:
            status = "совпадает"
        elif site_pr:
            status = "цена отличается"
        else:
            status = "на сайте не проставлена"
        rows.append(dict(slug=slug, name=p["name"], sku=p.get("sku") or "—",
                         sheet=sheet, row=row, variant=variant,
                         pname=it.get("name") or "",
                         pack=(pk.get("pack") or p.get("pack") or "—"),
                         retail=pr_ret, site=site_pr, status=status))

    no_map = [p for s, p in prods.items() if s not in MAP]
    unused = [(k, v) for k, v in items.items() if k not in used]

    rows.sort(key=lambda r: (r["sheet"], r["row"], r["variant"]))

    L = []
    L.append("# Карта соответствия: карточка сайта → строка прайса")
    L.append("")
    L.append("Файл генерируется: `python tools\\export_mapping.py` "
             "(источники — `tools/apply_prices.py` → `MAP` + `data/price_map_auto.json`, "
             "`data/prices.json`, `data/model.json`). Руками не правится.")
    L.append("Прайс: дистрибьюторский прайс завода от %s, действует с %s, цены %s." % (
        prices.get("generated") or "—", prices.get("valid_from", "—"),
        "с НДС" if prices.get("vat_included") else "без НДС"))
    L.append("")
    L.append("## Как читать таблицу")
    L.append("")
    L.append("- **Лист** — лист xlsx (`Прайс РиЗБ`, `Комплектующие для хим.анкеров`, "
             "`Прайс ИНЪЕКЦИИ`, `Прайс Гидролента`).")
    L.append("- **Строка** — номер строки на листе, **вар.** — номер фасовки в этой строке "
             "(в прайсе у одной позиции бывает 2–3 фасовки, на сайте это отдельные карточки).")
    L.append("- **Цена прайса** — колонка «ЦЕНА реализации» (розница, с НДС); "
             "**цена сайта** — то, что стоит в карточке.")
    L.append("- Статусы: `совпадает`, `цена отличается`, `в прайсе без цены` "
             "(строка есть, цена не заполнена — карточка показывает «по запросу»).")
    L.append("")
    L.append("## Сводка")
    L.append("")
    L.append("| | Позиций |")
    L.append("|---|---|")
    L.append("| Карточек на сайте | %d |" % len(prods))
    L.append("| Сопоставлено со строкой прайса | %d |" % len(rows))
    L.append("| Без строки в прайсе (цена «по запросу») | %d |" % len(no_map))
    L.append("| Строк прайса без карточки на сайте | %d |" % len(unused))
    L.append("")
    L.append("## Соответствие")
    order = ["Прайс РиЗБ", "Прайс ИНЪЕКЦИИ", "Прайс Гидролента",
             "Комплектующие для хим.анкеров"]
    for sheet in order:
        grp = [r for r in rows if r["sheet"] == sheet]
        if not grp:
            continue
        L.append("")
        L.append("### %s — %d карточек" % (sheet, len(grp)))
        L.append("")
        L.append("| slug | Карточка на сайте | Артикул | Строка | Вар. | Позиция прайса | "
                 "Фасовка | Цена прайса, ₽ | Цена сайта, ₽ | Статус |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in grp:
            pack = r["pack"]
            if pack.strip() in ("-", "—", ""):
                pack = prods[r["slug"]].get("pack") or "—"
            L.append("| `%s` | %s | %s | %d | %d | %s | %s | %s | %s | %s |" % (
                r["slug"], r["name"].replace("|", "/"), r["sku"], r["row"], r["variant"],
                (r["pname"] or "—").replace("|", "/"), pack.replace("|", "/"),
                money(r["retail"]), money(r["site"]), r["status"]))
    L.append("")
    L.append("## Карточки без строки в прайсе")
    L.append("")
    L.append("Эти позиции есть на сайте, но в действующем прайсе их нет: цена выводится как "
             "«по запросу» или осталась от прежнего прайса. Причина у каждой — своя "
             "(другой прайс направления, снято с производства, позиция не поставляется).")
    L.append("")
    L.append("| slug | Карточка на сайте | Артикул | Цена сайта, ₽ |")
    L.append("|---|---|---|---|")
    for p in sorted(no_map, key=lambda x: x["name"]):
        L.append("| `%s` | %s | %s | %s |" % (p["slug"], p["name"].replace("|", "/"),
                                              p.get("sku") or "—", money(p.get("price"))))
    L.append("")
    L.append("## Строки прайса без карточки на сайте")
    L.append("")
    L.append("Ассортимент, который прайс предлагает, но на сайте не заведён. "
             "Разбор — `E:\\Оптимизация\\Knowledge\\rex.moscow\\assortment_gap.md`.")
    L.append("")
    L.append("| Лист | Строка | Позиция прайса | Фасовок | Цена розницы, ₽ |")
    L.append("|---|---|---|---|---|")
    for (sheet, row), it in sorted(unused, key=lambda kv: (kv[0][0], kv[0][1])):
        packs = it.get("packs") or []
        ret = next((p.get("retail") for p in packs if p.get("retail")), None)
        L.append("| %s | %d | %s | %d | %s |" % (sheet, row, (it.get("name") or "").replace("|", "/"),
                                                 len(packs), money(ret)))
    L.append("")
    if problems:
        L.append("## Требует внимания")
        L.append("")
        for slug, sheet, row, why in problems:
            L.append("- `%s` → %s, строка %d: %s" % (slug, sheet, row, why))
        L.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("карточек: %d, сопоставлено: %d, без прайса: %d, строк прайса без карточки: %d"
          % (len(prods), len(rows), len(no_map), len(unused)))
    print("файл:", OUT)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Отчёт о расширении каталога rex.moscow (для базы знаний)."""
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Сайты\rex.moscow"
OUT = r"E:\Оптимизация\Knowledge\rex.moscow\catalog_expansion_2026-11-14.md"

model = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
prices = json.load(open(os.path.join(BASE, "data", "prices.json"), encoding="utf-8"))
cats = {c["slug"]: c for c in model["cats"]}
idx = {(i["sheet"], i["row"]): i for i in prices["items"]}

new = [p for p in model["products"] if p.get("source_row")]
by_cat = defaultdict(list)
for p in new:
    by_cat[p["cats"][0]].append(p)

lines = [
    "# Расширение каталога rex.moscow — 14.11.2026",
    "",
    "Каталог вырос с **91** до **%d** позиций: добавлены все позиции прайса ТД РЕКС," % len(model["products"]),
    "которых на сайте не было (%d шт.). Названия, фасовка и технические описания взяты из прайса," % len(new),
    "цены — розничный уровень («ЦЕНА реализации», с НДС).",
    "",
    "| Показатель | Было | Стало |",
    "|---|---|---|",
    "| Позиций в каталоге | 91 | %d |" % len(model["products"]),
    "| С ценой | 68 | %d |" % sum(1 for p in model["products"] if p.get("price")),
    "| По запросу | 23 | %d |" % sum(1 for p in model["products"] if not p.get("price")),
    "| Категорий | 32 | %d |" % len(model["cats"]),
    "| Страниц в sitemap | 239 | 352 |",
    "",
    "## Новые категории",
    "",
    "| Категория | Родитель | Позиций |",
    "|---|---|---|",
]
for slug in ("osnastka-dlya-ankerov", "oborudovanie-dlya-inekcii", "nabuhajushhie-shvy",
             "podzemnoe-stroitelstvo", "torkretirovanie"):
    c = cats.get(slug)
    if not c:
        continue
    parent = cats.get(next((k for k, v in cats.items() if v["id"] == c["parent"]), ""), None)
    lines.append("| %s | %s | %d |" % (c["name"], parent["name"] if parent else "—",
                                       sum(1 for p in model["products"] if slug in p["cats"])))

lines += ["", "## Что добавлено по категориям", ""]
for slug, items in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
    name = cats.get(slug, {}).get("name", slug)
    lines.append("### %s — %d" % (name, len(items)))
    lines.append("")
    lines.append("| Позиция | Фасовка | Цена, ₽ |")
    lines.append("|---|---|---|")
    for p in items:
        lines.append("| %s | %s | %s |" % (p["name"], p.get("pack", "—")[:44],
                                           "{:,}".format(p["price"]).replace(",", " ") if p["price"] else "по запросу"))
    lines.append("")

lines += [
    "## Что осталось за каталогом",
    "",
    "Не выведены 7 позиций «Сопутствующих материалов» — защитные чехлы (4), щётка, кисть; "
    "это упаковочный инвентарь, а не товар каталога. Компоненты комплектов "
    "(HASOIL Сойл, HACUT Кат, HACUT Флекс СНВ и катализаторы) отдельными карточками не созданы: "
    "они продаются только в составе комплекта, и на сайте уже есть карточки комплектов.",
    "",
    "## Фотографии",
    "",
    "Из бэкапа взят сайт целиком (`D:\\Old Sites\\rex.moscow`): 2 300 изображений и дамп базы "
    "MySQL. Для 91 карточки, у которых есть фото упаковки, изображения сконвертированы в WebP "
    "(900 px, ~21 КБ каждое) и выведены на карточках каталога и в карточке товара.",
    "Для 74 статей блога найдены и сконвертированы обложки (760×428, ~40 КБ).",
    "Новые позиции прайса фото не имеют — для них остаётся параметрическая пластина-«паспорт»; "
    "для анкерных шпилек добавлен отдельный чертёж стержня с резьбой и размером.",
]
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("записано:", OUT, "| новых:", len(new))

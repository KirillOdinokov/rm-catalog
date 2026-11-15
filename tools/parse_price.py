# -*- coding: utf-8 -*-
"""Разбор прайс-листа ТД РЕКС в data/prices.json.

Прайс: 4 листа, 4 уровня цен (розница / от 3 т / от 10 т СТОП / дистрибьютор).
Структура листа: шапка (стр. 9), строка единиц, затем блоки «раздел -> подраздел ->
позиция -> варианты упаковки».
"""
import json
import os
import re
import sys
from datetime import date

from openpyxl import load_workbook

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "Прайс-лист ТД РЕКС_ДИСТРИБЬЮТОР_сентябрь 2026 (10.09.2026).xlsx")
OUT = os.path.join(BASE, "data", "prices.json")

# раскладка колонок по листам
LAYOUT = {
    "Прайс РиЗБ": dict(name=1, desc=2, pack=3, money=[4, 5, 6, 7], header_row=9),
    "Комплектующие для хим.анкеров": dict(name=1, desc=2, pack=3, money=[4, 5, 6, 7], header_row=9),
    "Прайс ИНЪЕКЦИИ": dict(name=1, desc=2, pack=3, money=[4, 5, 6, 7], header_row=8),
    "Прайс Гидролента": dict(name=1, desc=2, pack=6, money=[7, 8, 9, 10], header_row=8,
                             extra={"width": 4, "thickness": 5}),
}

# верхнеуровневые разделы: сравниваем по началу строки заголовка
TOP = {
    "Прайс РиЗБ": [
        "Составы для ремонтных работ",
        "Инъекционные составы для упрочнения конструкций",
        "Составы для ремонтных работ на полимерной основе",
        "Защитные составы",
        "Составы для устройства пола",
        "Составы для ПОДЗЕМНОГО СТРОИТЕЛЬСТВА",
        "Адгезионные составы и связующие",
        "Изделия для ГЕРМЕТИЗАЦИИ и ГИДРОИЗОЛЯЦИИ швов",
        "Сопутствующие материалы",
    ],
    "Комплектующие для хим.анкеров": [
        "Комплектующие для монтажа",
        "Оборудование для установки",
        "Перфорированные втулки",
    ],
    "Прайс ИНЪЕКЦИИ": [
        "Гидроактивный жесткий полиуретановый",
        "Однокомпонентные гидроактивные",
        "Двухкомпонентные полиуретановые",
        "Двухкомпонентные составы на основе акриловых смол",
        "Комплектующие для инъектирования",
        "Оборудование для инъектирование за",
        "Оборудование для инъектирования",
        "Составы для подготоки и очистки",
    ],
    "Прайс Гидролента": [
        "Гидроизоляционные ленты",
        "Адгезионный состав",
    ],
}

COMPONENT_RE = re.compile(r"(катализатор|инициатор|TE300|SP200|Бенто Свелло\s*\(круглого)", re.I)

UNIT_RE = re.compile(r"^(упаковка|шт\.?|п\.?м\.?|Цена за (п\.?м\.?|упаковку|шт\.?))$", re.I)

NOTE_RE = re.compile(
    r"^(¹|Важные примечания|Важные|Примечан|\d+\.\s|-\s|МО,|Калужская|Затворение|Для затворения|"
    r"Стоимость|Условия|Цены указаны|Прайс-лист действ)", re.I)


def money(v):
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    if isinstance(v, str):
        s = v.strip().replace(" ", "").replace("\xa0", "").replace(",", ".")
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            return round(float(s), 2)
    return None


def clean(v):
    if v is None:
        return ""
    s = str(v).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", " ", s)
    return s.strip()


def main():
    wb = load_workbook(SRC, data_only=True)
    items, sheets_meta = [], []

    for ws in wb.worksheets:
        lay = LAYOUT[ws.title]
        cols = lay["money"]
        path, unit = [], ""
        last_item = None
        sheets_meta.append({"name": ws.title, "rows": ws.max_row, "cols": ws.max_column,
                            "header_row": lay["header_row"]})

        for r in range(lay["header_row"] + 1, ws.max_row + 1):
            name = clean(ws.cell(row=r, column=lay["name"]).value)
            pack = clean(ws.cell(row=r, column=lay["pack"]).value)
            vals = [money(ws.cell(row=r, column=c).value) for c in cols]
            desc = clean(ws.cell(row=r, column=lay["desc"]).value)
            desc = "" if desc == name else desc

            if not name and not pack and not any(v is not None for v in vals):
                continue
            text = (name + " " + pack).strip()
            if NOTE_RE.match(text) or NOTE_RE.match(name):
                continue

            # строка-единица измерения: только короткий текст в колонке A
            if name and not pack and not any(v is not None for v in vals) and UNIT_RE.match(name):
                unit = name
                continue

            is_header = name and not pack and not any(v is not None for v in vals)
            is_component = bool(is_header and last_item
                                and last_item["name"].split()[0].lower() == name.split()[0].lower())
            if is_component:
                last_item["components"].append(name)
                continue
            if is_header:
                if any(name.startswith(p) for p in TOP.get(ws.title, [])):
                    path = [name]
                else:
                    path = ([path[0], name] if path else [name])
                last_item = None
                continue

            if not name and pack and last_item:
                # доп. вариант упаковки той же позиции
                if pack in ("-", "—") or desc.lower().startswith("для затворения"):
                    continue
                last_item["packs"].append(dict(pack=pack, unit=unit,
                                               retail=vals[0], t3=vals[1], t10=vals[2], dist=vals[3]))
                continue

            if not name:
                continue

            item = {
                "sheet": ws.title,
                "row": r,
                "section": list(path),
                "name": name,
                "desc": desc,
                "unit": unit,
                "components": [],
                "packs": [dict(pack=pack, unit=unit,
                               retail=vals[0], t3=vals[1], t10=vals[2], dist=vals[3])],
            }
            if "extra" in lay:
                for k, c in lay["extra"].items():
                    item[k] = clean(ws.cell(row=r, column=c).value)
            items.append(item)
            last_item = item

    # «по запросу» -> цены None, но позиция остаётся
    priced = sum(1 for i in items if any(p["retail"] is not None for p in i["packs"]))
    on_request = len(items) - priced
    data = {
        "source_file": os.path.basename(SRC),
        "valid_from": "2026-09-10",
        "vat_included": True,
        "currency": "RUB",
        "levels": ["retail", "t3", "t10", "dist"],
        "level_titles": {
            "retail": "ЦЕНА реализации",
            "t3": "от 3 т.",
            "t10": "от 10 т. (СТОП-цена)",
            "dist": "для ДИСТРИБЬЮТОРА",
        },
        "generated": date.today().isoformat(),
        "sheets": sheets_meta,
        "stats": {"items": len(items), "priced": priced, "on_request": on_request,
                  "packs": sum(len(i["packs"]) for i in items)},
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("позиций: %d (с ценой %d, по запросу %d), вариантов упаковки: %d -> %s"
          % (len(items), priced, on_request, data["stats"]["packs"], OUT))


if __name__ == "__main__":
    main()

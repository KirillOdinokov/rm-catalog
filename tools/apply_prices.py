# -*- coding: utf-8 -*-
"""Перенос цен из прайс-листа ТД РЕКС в model.json.

Источник: data/prices.json (см. tools/parse_price.py).
Что делает:
  1) проставляет price = «ЦЕНА реализации» (розница, с НДС) из прайса;
  2) фиксирует фасовку и единицу измерения (шт / п.м.);
  3) переписывает цену в meta_title;
  4) пишет отчёт data/price_sync.json (что изменилось, несоответствия).
Старый model.json сохраняется рядом как model.backup.json.
"""
import json
import os
import re
import shutil
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
PRICES = os.path.join(BASE, "data", "prices.json")
REPORT = os.path.join(BASE, "data", "price_sync.json")
BACKUP = os.path.join(BASE, "data", "model.backup.json")

RIZB, INJ, TAPE = "Прайс РиЗБ", "Прайс ИНЪЕКЦИИ", "Прайс Гидролента"
ANK = "Комплектующие для хим.анкеров"

# slug товара на сайте -> (лист, строка прайса, номер варианта упаковки)
MAP = {
    # --- составы для ремонта бетона
    "reks-fab-10p": (RIZB, 13, 0),
    "reks-struktofljuid": (RIZB, 14, 0),
    "reks-graut-3-0": (RIZB, 15, 0),
    "reks-litoj": (RIZB, 17, 0),
    "reks-graut-m": (RIZB, 19, 0),
    "reks-graut-gp": (RIZB, 20, 0),
    "reks-grip-ultra": (RIZB, 21, 0),
    "reks-r3": (RIZB, 23, 0),
    "reks-strukto-r3": (RIZB, 24, 0),
    "reks-r4": (RIZB, 25, 0),
    "reks-strukto-r4": (RIZB, 26, 0),
    "reks-strukto-100": (RIZB, 27, 0),
    "reks-ar": (RIZB, 28, 0),
    "reks-strukto-70": (RIZB, 29, 0),
    "reks-strukto-300": (RIZB, 31, 0),
    "reks-ol": (RIZB, 32, 0),
    "reks-ar-fm": (RIZB, 33, 0),
    "reks-tikso": (RIZB, 36, 0),
    "reks-bs": (RIZB, 37, 0),
    "reks-fljuid": (RIZB, 40, 0),
    "reks-fajber-l": (RIZB, 41, 0),
    "reks-strukto-bs-3": (RIZB, 42, 0),
    "reks-prajmer": (RIZB, 44, 0),
    "reks-prajmer-antikor": (RIZB, 46, 1),
    "reks-strukto-lit": (RIZB, 54, 0),
    "reks-specrastvor": (RIZB, 55, 0),
    "reks-epo-inzh": (RIZB, 57, 1),
    # --- эпоксидные / акриловые
    "reks-fiks-epo-t-vn": (RIZB, 61, 0),
    "reks-epo-lik": (RIZB, 66, 0),
    "reks-akrisil-vn": (RIZB, 70, 0),
    "reks-akrilik-elast-vn": (RIZB, 72, 0),
    "reks-akrilik-vn": (RIZB, 73, 0),
    # --- гидроизоляционные
    "reks-plag-plag-30": (RIZB, 75, 0),
    "reks-sil": (RIZB, 77, 0),
    "reks-elast-110": (RIZB, 81, 0),
    "reks-elast-122": (RIZB, 82, 0),
    "reks-elast-100": (RIZB, 84, 0),
    "reks-super": (RIZB, 86, 0),
    "reks-anti-kapillyar": (RIZB, 88, 0),
    # --- защитные
    "reks-dekor": (RIZB, 91, 0),
    "reks-dekor-bk": (RIZB, 94, 0),
    "reks-protekt": (RIZB, 98, 0),
    "reks-gidrofob": (RIZB, 103, 0),
    "reks-epo-dekos": (RIZB, 107, 0),
    "severus-tikso": (RIZB, 108, 0),
    "severus-prajmer": (RIZB, 109, 0),
    # --- полы
    "reks-np-5000": (RIZB, 112, 0),
    "reks-53s": (RIZB, 113, 0),
    "reks-epo-top": (RIZB, 115, 0),
    "reks-epo-prajmer": (RIZB, 116, 0),
    "reks-fleks-epo-lik": (RIZB, 117, 1),
    # --- адгезионные, анкеры, клеи
    "reks-fiks-epo-tiks": (RIZB, 130, 0),
    "reks-fiks-akrep": (RIZB, 131, 0),
    "reks-epo-rezin": (RIZB, 135, 1),
    "reks-fiks-epo-t": (RIZB, 137, 0),
    "reks-epo-uni-shot-long": (RIZB, 139, 0),
    "reks-klej-pljus": (RIZB, 142, 0),
    # --- инъекции
    "hasoil-sojl": (INJ, 11, 0),
    "hacut-kat": (INJ, 15, 0),
    "hacut-fleks-snv": (INJ, 18, 0),
    "hasoil-rokstab": (INJ, 22, 0),
    "hasoil-rokstab-fast": (INJ, 23, 0),
    "hasoil-gelakril": (INJ, 25, 0),
    "hasoil-gelakril-ar": (INJ, 29, 0),
    "hacut-ochistitel": (INJ, 50, 0),
    # --- гидролента (цена за п.м.)
    "reks-gidrolenta": (TAPE, 11, 0),
    "reks-gidrolenta-200": (TAPE, 13, 0),
    "reks-gidrolenta-120-70": (TAPE, 14, 0),
    # --- адгезионные составы из листа гидроленты
    "reks-epo-uni-long": (TAPE, 24, 0),
    # --- оснастка
    "smesitelnaja-nasadka-mikser-dlja-him-ankera": (ANK, 50, 0),
}

# автодополнение карты: точные совпадения названий (tools\build_price_map.py)
AUTO_MAP_FILE = os.path.join(BASE, "data", "price_map_auto.json")
if os.path.exists(AUTO_MAP_FILE):
    try:
        _auto = json.load(open(AUTO_MAP_FILE, encoding="utf-8"))
        for _slug, _key in _auto.items():
            MAP.setdefault(_slug, tuple(_key))
    except Exception as _e:
        print("не прочитал %s: %s" % (AUTO_MAP_FILE, _e))

PRICE_RE = re.compile(r"по цене\s*[\d\s]+\s*руб")
TITLE_TAIL = " - купить по цене %d руб с НДС"
TITLE_NOPRICE = " - характеристики, аналоги, цена по запросу"


def title_with_price(old, price):
    base = re.sub(r"\s*[-—]\s*.*$", "", old or "").strip() or ""
    return base + (TITLE_TAIL % price if price else TITLE_NOPRICE)


def main():
    prices = json.load(open(PRICES, encoding="utf-8"))
    index = {(i["sheet"], i["row"]): i for i in prices["items"]}
    shutil.copy2(MODEL, BACKUP)
    model = json.load(open(MODEL, encoding="utf-8"))

    changed, same, problems = [], [], []
    for p in model["products"]:
        key = MAP.get(p["slug"])
        if not key:
            if p.get("price"):
                problems.append((p["slug"], p["name"], p.get("price"), "нет в прайсе"))
            continue
        item = index.get((key[0], key[1]))
        if not item:
            problems.append((p["slug"], p["name"], p.get("price"), "строка не найдена: %s" % (key,)))
            continue
        pack = item["packs"][key[2]] if key[2] < len(item["packs"]) else item["packs"][0]
        retail = pack["retail"]
        old = p.get("price") or 0
        # строка без цены (оснастка, шпильки, пакеры): цену не обнуляем и фасовку не портим
        new = int(round(retail)) if retail else old
        p["price"] = new
        p["old"] = 0
        pk = (pack["pack"] or "").strip()
        if pk and pk not in ("-", "—"):
            p["pack"] = pk
        p["unit"] = "п.м." if key[0] == TAPE else "шт"
        if retail:
            p["price_level"] = "retail"
            p["price_date"] = prices["valid_from"]
        if new:
            p["meta_title"] = title_with_price(p.get("meta_title"), new)
        (changed if new != old else same).append(
            (p["slug"], p["name"], old, new, item["name"], pack["pack"]))

    # у товаров без цены убираем цену из title и правим опечатку
    for p in model["products"]:
        if not p.get("price"):
            t = p.get("meta_title") or ""
            if PRICE_RE.search(t):
                p["meta_title"] = title_with_price(t, 0)
        if p.get("meta_title"):
            p["meta_title"] = p["meta_title"].replace("характеритики", "характеристики")

    json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    rows = []
    print("ИЗМЕНЕНО ЦЕН: %d, без изменений: %d, проблем: %d\n" % (len(changed), len(same), len(problems)))
    print("%-34s %-42s %9s %9s %7s  %s" % ("slug", "товар", "было", "стало", "Δ%", "позиция прайса"))
    for slug, name, old, new, pname, pack in sorted(changed, key=lambda r: -abs((r[3] - r[2]) / max(r[2], 1))):
        delta = (new - old) / old * 100 if old else 0
        print("%-34s %-42s %9d %9d %6.1f%%  %s / %s" % (slug[:34], name[:42], old, new, delta, pname[:40], pack[:36]))
        rows.append(dict(slug=slug, name=name, old=old, new=new, delta_pct=round(delta, 1),
                         price_name=pname, pack=pack))
    if problems:
        print("\nБЕЗ СООТВЕТСТВИЯ В ПРАЙСЕ (цена оставлена как была):")
        for slug, name, price, why in problems:
            print("  %-40s %8s  %s" % (slug, price, why))

    json.dump({
        "updated": date.today().isoformat(),
        "price_date": prices["valid_from"],
        "source": prices["source_file"],
        "mapped": len(MAP),
        "changed": rows,
        "unchanged": [s for s, _n, _o, _w, _p, _pk in same],
        "unmapped_priced": [dict(slug=s, name=n, price=pr, why=w) for s, n, pr, w in problems],
    }, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if os.path.exists(BACKUP):
        os.remove(BACKUP)
    shutil.copy2(MODEL, BACKUP)
    print("\nотчёт: %s" % REPORT)


if __name__ == "__main__":
    main()

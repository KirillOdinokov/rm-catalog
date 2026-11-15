# -*- coding: utf-8 -*-
"""Починка meta_title у товаров: одинаковые заголовки и обрезки по внутреннему дефису.

Две проблемы, обе от старого нормализатора, который резал title по первому дефису:

1) «Анкерная шпилька SKA-F 10×100» → база «Анкерная шпилька SKA», и у 13 шпилек SKA-F
   и 4 позиций МСЦ выходил одинаковый <title> без размера/варианта;
2) «РЕКС® анти-капилляр» → «РЕКС® анти», «РЕКС® фаб-10п» → «РЕКС® фаб» — название
   обрывалось на внутреннем дефисе.

Скрипт берёт название товара (или его брендовую часть) и собирает title тем же
нормализатором, что и sync_prices.title_with_price(). Идемпотентен.

    & $py tools\fix_titles.py           # показать и записать
    & $py tools\fix_titles.py --dry     # только показать
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sync_prices import title_base, title_with_price  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
BRANDS = ("РЕКС®", "Hasoil", "Hacut", "Северус")


def brand_part(name):
    """Название без описательного префикса: «1К смесь РЕКС® сил» -> «РЕКС® сил»."""
    low = (name or "").lower()
    for b in BRANDS:
        i = low.find(b.lower())
        if i >= 0:
            return name[i:].strip()
    return (name or "").strip()


def main():
    dry = "--dry" in sys.argv
    model = json.load(open(MODEL, encoding="utf-8"))
    products = model["products"]

    by_title = {}
    for p in products:
        by_title.setdefault((p.get("meta_title") or "").strip(), []).append(p)

    fixed = []
    for p in products:
        name = p.get("name") or ""
        title = (p.get("meta_title") or "").strip()
        if not title:
            continue
        base = title_base(title, name)
        brand = brand_part(name)
        same = len(by_title.get(title, [])) > 1
        cut = (base.lower() != brand.lower() and brand.lower().startswith(base.lower())
               and brand[len(base):].startswith("-"))
        if not (same or cut):
            continue
        new = title_with_price("", p.get("price") or 0, brand)
        if new != title:
            fixed.append((p["slug"], "дубль" if same else "обрезка", title, new))
            p["meta_title"] = new

    print("исправлено: %d (дубли/обрезки: %d/%d)" % (
        len(fixed), sum(1 for f in fixed if f[1] == "дубль"),
        sum(1 for f in fixed if f[1] == "обрезка")))
    for slug, why, old, new in fixed:
        print("  [%s] %-38s\n    было: %s\n    стало: %s" % (why, slug, old, new))

    if dry:
        print("\n--dry: файл не изменён")
        return

    if fixed:
        json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    again = {}
    for p in products:
        again.setdefault((p.get("meta_title") or "").strip(), []).append(p["slug"])
    dup = {k: v for k, v in again.items() if len(v) > 1}
    print("осталось дублей: %d" % len(dup))
    for k, v in dup.items():
        print("  %s -> %s" % (k, v))


if __name__ == "__main__":
    main()

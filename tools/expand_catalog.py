# -*- coding: utf-8 -*-
"""Расширение каталога rex.moscow позициями прайса.

Берёт data/prices.json, отбрасывает уже опубликованные (MAP из apply_prices) и
добавляет остальные позиции в data/model.json:
  - имя (из прайса, очищенное), слаг (транслит), категории (по правилам + оверрайды),
  - цена (розница), фасовка, единица, краткое и полное описание из прайса,
  - артикул REKS93… , meta_title/meta_desc.

Запуск без аргументов — сухой прогон (только печать), с --apply — запись в model.json.
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from apply_prices import MAP, RIZB, INJ, TAPE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
PRICES = os.path.join(BASE, "data", "prices.json")

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "j", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh",
    "щ": "shh", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "ju", "я": "ja",
}

# новые категории (добавляются, если их нет)
NEW_CATS = [
    ("nabuhajushhie-shvy", "Набухающие швы и профили",
     "Бентонитовые и резиновые набухающие шнуры, профили и пробки для герметизации рабочих швов.", "gidroizolyaciya-betona"),
    ("podzemnoe-stroitelstvo", "Подземное строительство",
     "Модификаторы струйной цементации и кондиционеры грунта для тоннельных работ.", "gidroizolyaciya-betona"),
    ("torkretirovanie", "Торкретирование и набрызг",
     "Смеси для механизированного нанесения: мокрый набрызг и сухое торкретирование.", "na-mineralnoj-osnove"),
    ("osnastka-dlya-ankerov", "Оснастка для анкеров",
     "Анкерные шпильки SKA, пистолеты, смесительные насадки и сетчатые гильзы.", "ankerovochnye-sostavy"),
    ("oborudovanie-dlya-inekcii", "Оборудование для инъекций",
     "Пакеры, инъекционные насосы и иглы для подачи составов за гидроизоляцию.", "inekcionnaya"),
]

# правила: (лист, начало раздела) -> категория
BY_SECTION = {
    ("Комплектующие для монтажа",): ["osnastka-dlya-ankerov", "ankerovochnye-sostavy"],
    ("Оборудование для установки",): ["osnastka-dlya-ankerov"],
    ("Перфорированные втулки",): ["osnastka-dlya-ankerov"],
    ("Комплектующие для инъектирования",): ["oborudovanie-dlya-inekcii", "inekcionnaya"],
    ("Оборудование для инъектирования",): ["oborudovanie-dlya-inekcii"],
    ("Составы для подготоки",): ["inekcionnaya"],
    ("Набухающие",): ["nabuhajushhie-shvy", "gidroizolyaciya-betona"],
    ("Гидроизоляционные ленты",): ["germetizaciya-deformacionnyh-shvov", "gidroizolyaciya-betona"],
    ("Адгезионный состав",): ["adgezionnye-sostavy"],
    ("Составы для ПОДЗЕМНОГО",): ["podzemnoe-stroitelstvo", "gidroizolyaciya-betona"],
    ("Гидроактивный",): ["inekcionnaya", "gidroizolyaciya-betona"],
    ("Однокомпонентные гидроактивные",): ["inekcionnaya", "gidroizolyaciya-betona"],
    ("Двухкомпонентные полиуретановые",): ["inekcionnaya", "gidroizolyaciya-betona"],
    ("Двухкомпонентные составы на основе акриловых",): ["inekcionnaya", "gidroizolyaciya-betona"],
}
# правила: (лист, раздел, подраздел) -> категория
BY_SUB = {
    ("Составы для ремонтных работ", "Подливочные составы для монтажа"): ["podlivochnogo-tipa", "smesi-dlya-remonta-betona"],
    ("Составы для ремонтных работ", "Подливочные составы для конструкционного"): ["podlivochnogo-tipa", "smesi-dlya-remonta-betona"],
    ("Составы для ремонтных работ", "Тиксотропные"): ["tiksotropnogo-tipa", "smesi-dlya-remonta-betona"],
    ("Составы для ремонтных работ", "Составы для неконструкционного"): ["tiksotropnogo-tipa", "smesi-dlya-remonta-betona"],
    ("Составы для ремонтных работ", "Составы для ремонта бетона при ОТРИЦАТЕЛЬНЫХ"): ["tiksotropnogo-tipa", "smesi-dlya-remonta-betona"],
    ("Составы для ремонтных работ", "Антикоррозионная защита арматуры"): ["antikorrozionnaya-obrabotka", "smesi-dlya-zashhity-betona-i-zhbi"],
    ("Составы для ремонтных работ", "Составы для механизированного"): ["torkretirovanie", "smesi-dlya-remonta-betona"],
    ("Инъекционные составы для упрочнения", "Минеральные составы"): ["inekcionnaya", "gidroizolyaciya-betona"],
    ("Инъекционные составы для упрочнения", "Полимерные составы"): ["inekcionnaya", "gidroizolyaciya-betona"],
    ("Составы для ремонтных работ на полимерной основе", "Эпоксидные составы"): ["na-polimernoj-osnove", "smesi-dlya-remonta-betona"],
    ("Составы для ремонтных работ на полимерной основе", "Акриловые составы"): ["na-polimernoj-osnove", "smesi-dlya-remonta-betona"],
    ("Составы для ремонтных работ на полимерной основе", "Гидроизоляционные составы"): ["obmazochnaya", "gidroizolyaciya-betona"],
    ("Защитные составы", "Минеральные составы"): ["mineralnye", "smesi-dlya-zashhity-betona-i-zhbi"],
    ("Защитные составы", "Полимерные составы"): ["polimernye", "smesi-dlya-zashhity-betona-i-zhbi"],
    ("Составы для устройства пола", "Минеральные составы"): ["rovniteli", "polimernye-poly"],
    ("Составы для устройства пола", "Полимерные составы"): ["pokrytiya-dlya-promyshlennyh-polov", "polimernye-poly"],
    ("Адгезионные составы и связующие", "Химические анкера"): ["ankerovochnye-sostavy"],
    ("Адгезионные составы и связующие", "Полимерные адгезионные"): ["adgezionnye-sostavy"],
    ("Адгезионные составы и связующие", "Минеральные клеевые"): ["plitochnye-kleyashhie-sostavy", "adgezionnye-i-kleyashie-sostavy"],
    ("Составы для ПОДЗЕМНОГО СТРОИТЕЛЬСТВА", "Модификаторы"): ["podzemnoe-stroitelstvo", "gidroizolyaciya-betona"],
    ("Составы для ПОДЗЕМНОГО СТРОИТЕЛЬСТВА", "Кондиционеры"): ["podzemnoe-stroitelstvo", "gidroizolyaciya-betona"],
    ("Сопутствующие материалы", ""): ["osnastka-dlya-ankerov"],
}

# точечные оверрайды: (лист, строка) -> категории
OVERRIDES = {
    (RIZB, 76): ["gidroizolyaciya-betona", "likvidirovanie-aktivnyh-protechek"],   # ПЛАГ 30
    (RIZB, 79): ["gidroizolyaciya-betona", "obmazochnaya"],                        # СИЛ белый
    (RIZB, 83): ["gidroizolyaciya-betona", "obmazochnaya"],                        # ЭЛАСТ 122 белый
    (RIZB, 85): ["gidroizolyaciya-betona", "obmazochnaya"],                        # ЭЛАСТ 100 белый
    (RIZB, 87): ["gidroizolyaciya-betona", "pronikajushhaya"],                      # Супер белый
    (RIZB, 62): ["ankerovochnye-sostavy"], (RIZB, 63): ["ankerovochnye-sostavy"],
    (RIZB, 64): ["ankerovochnye-sostavy"],
    (RIZB, 65): ["na-polimernoj-osnove", "smesi-dlya-remonta-betona"],              # Эполит
    (RIZB, 68): ["antikorrozionnaya-obrabotka", "smesi-dlya-zashhity-betona-i-zhbi"],  # Аква Денсит
    (RIZB, 71): ["na-polimernoj-osnove", "smesi-dlya-remonta-betona"],              # Акрисил Л
    (RIZB, 104): ["polimernye", "smesi-dlya-zashhity-betona-i-zhbi"],               # Гидрофоб А
    (RIZB, 133): ["adgezionnye-sostavy", "adgezionnye-i-kleyashie-sostavy"],        # Акрил
    (RIZB, 138): ["adgezionnye-sostavy"],                                           # Фикс Эпо Т красный
    (RIZB, 140): ["adgezionnye-sostavy"],                                           # Эпо Уни Шот
    (RIZB, 143): ["plitochnye-kleyashhie-sostavy", "adgezionnye-i-kleyashie-sostavy"],
    (RIZB, 157): ["inekcionnaya", "gidroizolyaciya-betona"],                        # Смывка МСЦ
}

# позиции, которые не выводим в каталог (аксессуары-упаковка)
SKIP_NAMES = ("Защитный чехол", "Щетка", "Кисть")


def slugify(name):
    s = name.lower().replace("®", "").replace("™", "")
    s = s.replace("ø", "o").replace("Ø", "O").replace("№", "n")
    s = re.sub(r"[«»\"'()]", " ", s)
    out = []
    for ch in s:
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isalnum():
            out.append(ch)
        else:
            out.append("-")
    s = "".join(out)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:70]


NAME_FIX = {
    "Универсальный электрический шнековый насос - Агрегат электронасосный одновинтовой марка АПНВ25Н":
        "Насос шнековый АПНВ25Н",
    "Смесительная насадка (миксер) для смешивания двухкомпонентной массы химического анкера":
        "Смесительная насадка (миксер) для хим. анкера",
}


def clean_name(raw):
    """«РЕКС® Фикс Эпо Тикс (картридж 410 мл)» -> имя + уточнение в фасовку."""
    n = raw.strip()
    if n in NAME_FIX:
        return NAME_FIX[n]
    m = re.match(r"^\(SK[АA](-F)?\)\s*Анкерная шпилька\s+(\d+)[xх×](\d+)$", n)
    if m:
        return "Анкерная шпилька SKA%s %s×%s" % (m.group(1) or "", m.group(2), m.group(3))
    if n.startswith("РЕКС® Бенто Свелло размером"):
        return "РЕКС® Бенто Свелло (другие сечения)"
    n = re.sub(r"\s*\((лента-эластомер[^)]*|эластомер[^)]*)\)", "", n, flags=re.I)
    n = re.sub(r"\s*\(пр\.-во Россия\)", "", n)
    n = re.sub(r"\s*\(картридж [^)]*\)", "", n)
    n = re.sub(r"\s*\(модификатор[^)]*\)", "", n)
    n = re.sub(r"\s+", " ", n).strip(" ,.")
    return n


def cat_for(item):
    key = (item["sheet"], item["row"])
    if key in OVERRIDES:
        return OVERRIDES[key]
    sec = item["section"][0] if item["section"] else ""
    sub = item["section"][1] if len(item["section"]) > 1 else ""
    for (s, ss), cats in BY_SUB.items():
        if sec.startswith(s) and sub.startswith(ss):
            return cats
    for prefixes, cats in BY_SECTION.items():
        if sec.startswith(prefixes[0]) or sub.startswith(prefixes[0]):
            return cats
    if item["sheet"] == INJ:
        return ["inekcionnaya", "gidroizolyaciya-betona"]
    if item["sheet"] == TAPE:
        return ["germetizaciya-deformacionnyh-shvov", "gidroizolyaciya-betona"]
    return ["smesi-dlya-remonta-betona"]


def first_sentence(text, limit=320):
    t = re.sub(r"\s+", " ", text or "").strip()
    if not t:
        return ""
    cut = re.split(r"(?<=[.!?])\s", t)
    out = cut[0]
    for s in cut[1:]:
        if len(out) + len(s) > limit:
            break
        out += " " + s
    return out[:limit].rstrip(" ,;") + ("" if out.endswith(".") else ".")


def main():
    apply = "--apply" in sys.argv
    model = json.load(open(MODEL, encoding="utf-8"))
    prices = json.load(open(PRICES, encoding="utf-8"))
    used = {(s, r) for (s, r, _i) in MAP.values()}
    have_slugs = {p["slug"] for p in model["products"]}
    next_id = max(p["id"] for p in model["products"]) + 1
    next_sku = 93

    new, skipped = [], []
    for it in prices["items"]:
        if (it["sheet"], it["row"]) in used:
            continue
        if any(it["name"].startswith(s) for s in SKIP_NAMES):
            skipped.append((it["name"], "аксессуар"))
            continue
        name = clean_name(it["name"])
        slug = slugify(name)
        if slug in have_slugs:
            skipped.append((it["name"], "слаг занят: " + slug))
            continue
        pk = it["packs"][0]
        cats = cat_for(it)
        price = int(round(pk["retail"])) if pk["retail"] else 0
        unit = "п.м." if it["sheet"] == TAPE else "шт"
        desc = re.sub(r"\s+", " ", it["desc"] or "").strip()
        short = first_sentence(desc)
        meta = "%s - купить по цене %d руб с НДС" % (name, price) if price else \
               "%s - характеристики, аналоги, цена по запросу" % name
        row = dict(
            id=next_id, slug=slug, name=name, cats=cats,
            price=price, old=0, sku="REKS%d" % next_sku,
            short=short, desc=("<p>%s</p>" % desc) if desc else "",
            img="", meta_title=meta, meta_desc=first_sentence(desc, 160),
            posts_link="", pack=pk["pack"], unit=unit, price_level="retail",
            price_date=prices["valid_from"], source_row=[it["sheet"], it["row"]],
        )
        new.append(row)
        have_slugs.add(slug)
        next_id += 1
        next_sku += 1

    print("новых позиций: %d, пропущено: %d" % (len(new), len(skipped)))
    cnt = Counter()
    for r in new:
        cnt[r["cats"][0]] += 1
    print("по категориям:", dict(cnt.most_common()))
    print()
    for r in new:
        print("%-52s %-42s %-22s %8s" % (r["name"][:52], r["slug"][:42], r["cats"][0][:22],
                                         r["price"] or "по запросу"))
    if not apply:
        if skipped:
            print("\nпропущено:")
            for n, why in skipped:
                print("   %-60s %s" % (n[:60], why))
        print("\n(сухой прогон; для записи добавьте --apply)")
        return

    # категории
    cats = model["cats"]
    by_slug = {c["slug"]: c for c in cats}
    root = {c["slug"]: c for c in cats if not c["parent"]}
    cid = max(c["id"] for c in cats) + 1
    for slug, nm, descr, parent in NEW_CATS:
        if slug in by_slug:
            continue
        par = by_slug.get(parent) or root.get(parent)
        cats.append(dict(id=cid, slug=slug, name=nm, parent=par["id"] if par else 0, count=0,
                         meta_title="%s РЕКС - купить, виды, цены" % nm, meta_desc=descr, desc=descr))
        cid += 1
    model["products"].extend(new)
    model["max_id"] = max(p["id"] for p in model["products"])
    json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nзаписано: товаров %d, категорий %d" % (len(model["products"]), len(model["cats"])))


if __name__ == "__main__":
    main()

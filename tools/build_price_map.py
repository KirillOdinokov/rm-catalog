#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""build_price_map.py — автодополнение карты «карточка сайта → строка прайса».

Ручной словарь MAP в tools\apply_prices.py покрывает не все карточки: часть позиций
(цветовые варианты, размерные ряды гидроленты, гидрошпонки, оснастка) в прайсе есть,
но в MAP их не заводили. Скрипт ищет точные совпадения названий и пишет
data\price_map_auto.json, который apply_prices.py подмешивает к MAP.

Правила (жёсткие, чтобы не перепутать позиции):
  • сходство нормализованных названий ≥ 0.995 (фактически «то же имя»);
  • пара «лист + строка + вариант» не занята ручной картой и не выдана другой карточке;
  • если у строки несколько фасовок — берём ту, чей текст ближе к фасовке карточки;
  • строку без цены подключаем только к карточке без цены (иначе не трогаем — цена важнее.

Запуск: python tools\build_price_map.py [--apply]
  --apply  сразу запустить tools\apply_prices.py после генерации
"""
import difflib
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "tools"))
from apply_prices import MAP  # noqa: E402

OUT = os.path.join(BASE, "data", "price_map_auto.json")
MODEL = os.path.join(BASE, "data", "model.json")
PRICES = os.path.join(BASE, "data", "prices.json")
THRESHOLD = 0.995

# apply_prices подмешивает прошлый автофайл в MAP — для пересборки берём только ручную часть
_prev_auto = {}
if os.path.exists(OUT):
    try:
        _prev_auto = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        _prev_auto = {}
MANUAL = {k: v for k, v in MAP.items() if k not in _prev_auto}


def norm(s):
    s = (s or "").lower().replace("ё", "е").replace("®", " ")
    s = re.sub(r"(?<=\d)\s*[х×x]\s*(?=\d)", "x", s)
    s = re.sub(r"[^0-9a-zа-я.]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# латинские двойники кириллицы — чтобы «SKA» и «SKА» считались одним
LOOKALIKE = str.maketrans("аеорсхукмтвн", "aeopcxykmtbh")
FAMILY = [
    ("шпильк", "анкерная шпилька"),
    ("гильз", "гильза"),
    ("пакер", "пакер"),
    ("насос", "насос"),
    ("игл", "игла"),
    ("насадк", "насадка"),
    ("пистолет", "пистолет"),
    ("катализатор", "катализатор"),
]


def numbers(s):
    """Размеры и числа из названия: 10x100, 380, 19 и т. п."""
    s = norm(s)
    return set(re.findall(r"\d+(?:x\d+)?", s))


def family(s):
    n = norm(s)
    for key, name in FAMILY:
        if key in n:
            return name
    return ""


def fam_variant(s):
    """SKA-F против SKA: буква F в названии модели."""
    return "f" if re.search(r"\bska\s*-\s*f\b|\bska\s?f\b", norm(s).translate(LOOKALIKE)) else ""


def numeric_pass(model, items, used, auto, report):
    """Оснастка и крепёж: совпадение семейства + полный набор размеров."""
    added = 0
    for p in model["products"]:
        if p["slug"] in MANUAL or p["slug"] in auto:
            continue
        fam = family(p["name"])
        nums = numbers(p["name"])
        if not fam or not nums:
            continue
        var = fam_variant(p["name"])
        cands = []
        for it in items:
            if (it["sheet"], it["row"]) in used:
                continue
            if family(it["name"]) != fam:
                continue
            if numbers(it["name"]) != nums:
                continue
            if fam == "анкерная шпилька" and fam_variant(it["name"]) != var:
                continue
            cands.append(it)
        if len(cands) != 1:
            continue
        it = cands[0]
        packs = it.get("packs") or [{}]
        pk = packs[0]
        if not pk.get("retail") and (p.get("price") or 0):
            continue
        auto[p["slug"]] = [it["sheet"], it["row"], 0]
        used.add((it["sheet"], it["row"]))
        added += 1
        report.append((p["slug"], "→ %s, строка %d (%s)" % (it["sheet"], it["row"], it["name"])))
    return added


def main():
    model = json.load(open(MODEL, encoding="utf-8"))
    prices = json.load(open(PRICES, encoding="utf-8"))
    items = prices["items"]

    used = {(v[0], v[1]) for v in MANUAL.values()}
    auto, report = {}, []
    for p in model["products"]:
        if p["slug"] in MANUAL:
            continue
        n = norm(p["name"])
        best, best_r = None, 0.0
        for it in items:
            r = difflib.SequenceMatcher(None, n, norm(it["name"])).ratio()
            if r > best_r:
                best, best_r = it, r
        if not best or best_r < THRESHOLD:
            continue
        if (best["sheet"], best["row"]) in used:
            report.append((p["slug"], "строка уже занята другой карточкой"))
            continue
        packs = best.get("packs") or []
        if not packs:
            continue
        # фасовка: ближайшая по тексту, при равенстве — с ценой
        pn = norm(p.get("pack") or "")
        idx, sc = 0, -1
        for i, pk in enumerate(packs):
            s = difflib.SequenceMatcher(None, pn, norm(pk.get("pack") or "")).ratio()
            if pk.get("retail") and not packs[idx].get("retail"):
                s += 0.2
            if s > sc:
                idx, sc = i, s
        pk = packs[idx]
        site_price = p.get("price") or 0
        if not pk.get("retail") and site_price:
            report.append((p["slug"], "в прайсе нет цены, а на сайте цена есть — пропуск"))
            continue
        auto[p["slug"]] = [best["sheet"], best["row"], idx]
        used.add((best["sheet"], best["row"]))
        report.append((p["slug"], "→ %s, строка %d, вар. %d (%s)" % (
            best["sheet"], best["row"], idx, best["name"])))

    n_numeric = numeric_pass(model, items, used, auto, report)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(auto, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("автосопоставлений: %d (по названию: %d, по размерам: %d), было в MAP: %d"
          % (len(auto), len(auto) - n_numeric, n_numeric, len(MANUAL)))
    for slug, msg in report:
        print("  %-52s %s" % (slug[:52], msg))
    print("файл:", OUT)

    if "--apply" in sys.argv:
        print("\n--- apply_prices.py ---")
        subprocess.run([sys.executable, os.path.join(BASE, "tools", "apply_prices.py")],
                       cwd=BASE)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Синхронизация цен rex.moscow из Базы (вариант A).

Тянет GET https://ai.enix.ru:10443/base/api/site/6/prices -> {"slug": цена},
обновляет в model.json: price, old, meta_title, price_level.
Пишет отчёт data/price_sync.json. Замена ручного parse_price + apply_prices.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
BACKUP = os.path.join(BASE, "data", "model.backup.json")
REPORT = os.path.join(BASE, "data", "price_sync.json")
PENDING = os.path.join(BASE, "data", "price_pending.json")

API_URL = os.environ.get(
    "REX_API_URL",
    "https://ai.enix.ru:10443/base/api/site/6/prices",
)

TITLE_TAIL = " - купить по цене %d руб с НДС"
TITLE_NOPRICE = " - характеристики, аналоги, цена по запросу"
TITLE_NOPRICE_SHORT = " - характеристики, цена по запросу"
TITLE_MAX = 70
PRICE_RE = re.compile(r"по цене\s*[\d\s]+\s*руб")
PRICE_TAIL_RE = re.compile(r"\s+[-–—]\s+купить по цене\s*[\d\s]*\s*руб с НДС$")
LEGACY_TAIL_RE = re.compile(r"\s+[-–—]\s+(?=(?:купить|характеристик|техническ|цена по запросу))", re.I)


def title_base(old, name=""):
    """Название без хвоста «… - купить по цене …» / «… - характеристики …».

    Резать по первому дефису нельзя: в «Анкерная шпилька SKA-F 10×100» и
    «РЕКС® МСЦ-АНТИГЛИНА» дефис — часть названия. Именно из-за этого 17 карточек
    теряли размер/вариант и получали одинаковый title.
    """
    s = (old or "").strip()
    for tail in (TITLE_NOPRICE, TITLE_NOPRICE_SHORT):
        if s.endswith(tail):
            s = s[:-len(tail)].strip()
            break
    else:
        m = PRICE_TAIL_RE.search(s)
        if m:
            s = s[:m.start()].strip()
    m = LEGACY_TAIL_RE.search(s)  # остатки старых WP-хвостов
    if m:
        s = s[:m.start()].strip()
    return s or (name or "").strip()


def title_with_price(old, price, name=""):
    """Title = база (старый title или название) + хвост по цене.

    Хвост берём самый длинный из тех, что укладываются в 70 знаков: иначе product_title()
    обрежет title при рендере. Не влезло ничего — оставляем длинный хвост, его обрежет рендер.
    """
    base = title_base(old, name)
    tails = [TITLE_TAIL % price] if price else [TITLE_NOPRICE, TITLE_NOPRICE_SHORT]
    for tail in tails:
        if len(base) + len(tail) <= TITLE_MAX:
            return base + tail
    return base + tails[0]


def fetch_prices():
    req = urllib.request.Request(API_URL, headers={"User-Agent": "rex-price-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data.get("prices", {})


def main():
    prices = fetch_prices()
    model = json.load(open(MODEL, encoding="utf-8"))

    changed, same, problems = [], [], []
    for p in model["products"]:
        slug = p.get("slug")
        if slug not in prices:
            if p.get("price"):
                problems.append((slug, p["name"], p["price"], "нет строки в прайсе"))
            continue
        raw = prices[slug]
        new = int(round(raw)) if raw is not None else 0
        old = p.get("price") or 0
        p["price"] = new
        p["old"] = 0
        p["price_level"] = "retail"
        p["meta_title"] = title_with_price(p.get("meta_title"), new, p.get("name"))
        (changed if new != old else same).append((slug, p["name"], old, new))

    for p in model["products"]:
        if not p.get("price"):
            t = p.get("meta_title") or ""
            if PRICE_RE.search(t):
                p["meta_title"] = title_with_price(t, 0, p.get("name"))

    if changed:
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        with open(MODEL, encoding="utf-8") as f:
            open(BACKUP, "w", encoding="utf-8").write(f.read())
    json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(
        {"prices": {p["slug"]: (p.get("price") or 0) for p in model["products"]}},
        open(PENDING, "w", encoding="utf-8"), ensure_ascii=False, indent=0,
    )

    json.dump({
        "updated": date.today().isoformat(),
        "changed": [{"slug": s, "name": n, "old": o, "new": w} for s, n, o, w in changed],
        "unchanged": [s for s, _n, _o, _w in same],
        "problems": [{"slug": s, "name": n, "price": pr, "why": w} for s, n, pr, w in problems],
    }, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("изменено цен: %d, без изменений: %d, проблем: %d" % (len(changed), len(same), len(problems)))
    for slug, name, old, new in changed[:15]:
        print("  %-34s %s -> %s" % (slug[:34], old, new))


if __name__ == "__main__":
    main()

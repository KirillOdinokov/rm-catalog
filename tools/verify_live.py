# -*- coding: utf-8 -*-
"""Сверка живого сайта с model.json: цена и фасовка на всех карточках с ценой."""
import json, os, re, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))

PRICE = re.compile(r'class="prod__price">([\d\s]+)\s*<small>')
PACK = re.compile(r"<dt>Фасовка</dt><dd>(.*?)</dd>", re.S)

bad, ok = [], 0
for p in m["products"]:
    if not p.get("price"):
        continue
    url = "https://rex.moscow/" + p["slug"]
    try:
        html = urllib.request.urlopen(url, timeout=20).read().decode("utf-8")
    except Exception as e:
        bad.append((p["slug"], "fetch", str(e)))
        continue
    mm = PRICE.search(html)
    live = int(re.sub(r"\D", "", mm.group(1))) if mm else 0
    if live != p["price"]:
        bad.append((p["slug"], "price %s != %s" % (live, p["price"]), ""))
    else:
        ok += 1
print("проверено карточек с ценой: %d, совпало: %d, расхождений: %d" % (ok + len(bad), ok, len(bad)))
for b in bad[:15]:
    print("  ", b)

# -*- coding: utf-8 -*-
"""Правка новых позиций каталога: фасовка «-» -> осмысленная, размер шпилек."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Сайты\rex.moscow"
model = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
prices = json.load(open(os.path.join(BASE, "data", "prices.json"), encoding="utf-8"))
idx = {(i["sheet"], i["row"]): i for i in prices["items"]}

fixed = 0
for p in model["products"]:
    src = p.get("source_row")
    if not src:
        continue
    it = idx.get(tuple(src))
    if not it:
        continue
    pack = it["packs"][0]["pack"].strip()
    m = re.match(r"^Анкерная шпилька SKA(-F)? (\d+)×(\d+)$", p["name"])
    if m:
        p["size"] = "M%s×%s" % (m.group(2), m.group(3))
        p["pack"] = "шт."
        fixed += 1
        continue
    if pack in ("-", "—", ""):
        p["pack"] = "по запросу"
        fixed += 1
json.dump(model, open(os.path.join(BASE, "data", "model.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("исправлено фасовок:", fixed)

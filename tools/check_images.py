# -*- coding: utf-8 -*-
"""Проверяем, какие img из model.json есть локально в бэкапе."""
import json, os, re, sys
from urllib.parse import unquote
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"E:\Сайты\rex.moscow"
UP = r"D:\Old Sites\rex.moscow\public_html\wp-content\uploads"
m = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))

def local(url):
    u = unquote(url or "")
    i = u.find("/wp-content/uploads/")
    if i < 0:
        return None
    rel = u[i + len("/wp-content/uploads/"):].split("?")[0]
    return os.path.join(UP, rel.replace("/", os.sep))

have = miss = noimg = 0
misses = []
for p in m["products"]:
    img = p.get("img")
    if not img:
        noimg += 1
        continue
    fp = local(img)
    if fp and os.path.isfile(fp):
        have += 1
    else:
        miss += 1
        misses.append((p["slug"], img))
print("товаров: %d | img есть локально: %d | нет файла: %d | без img: %d" % (len(m["products"]), have, miss, noimg))
for s, u in misses[:10]:
    print("  MISS", s, u)

# размеры и форматы найденных
from collections import Counter
ext = Counter()
for p in m["products"]:
    fp = local(p.get("img"))
    if fp and os.path.isfile(fp):
        ext[os.path.splitext(fp)[1].lower()] += 1
print("форматы:", dict(ext))

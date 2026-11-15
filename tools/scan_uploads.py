# -*- coding: utf-8 -*-
"""Сколько уникальных картинок (без ресайзов) и какие не используются товарами."""
import json, os, re, sys
from collections import defaultdict
from urllib.parse import unquote
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"E:\Сайты\rex.moscow"
UP = r"D:\Old Sites\rex.moscow\public_html\wp-content\uploads"
m = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))

SIZE = re.compile(r"-\d+x\d+(?=\.[a-z]+$)", re.I)
bases = defaultdict(list)
for root, _d, files in os.walk(UP):
    for f in files:
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            continue
        base = SIZE.sub("", f)
        rel = os.path.relpath(os.path.join(root, f), UP).replace("\\", "/")
        bases[base].append(rel)

used = set()
for p in m["products"]:
    u = unquote(p.get("img") or "")
    i = u.find("/wp-content/uploads/")
    if i >= 0:
        used.add(os.path.basename(u[i + len("/wp-content/uploads/"):]))

# картинка считается использованной, если её базовое имя совпадает с использованной
used_bases = {SIZE.sub("", x) for x in used}
free = {b: v for b, v in bases.items() if b not in used_bases}
print("уникальных картинок: %d, использовано товарами: %d, свободных: %d" % (len(bases), len(used_bases), len(free)))
big = {b: sorted(v, key=len)[0] for b, v in free.items()}
print("свободных с исходником: %d" % len(big))
for b in sorted(big)[:40]:
    print("  ", big[b])
json.dump(big, open(os.path.join(BASE, "data", "_db", "free_images.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

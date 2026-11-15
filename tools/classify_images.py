# -*- coding: utf-8 -*-
"""Классификация свободных картинок: обложки статей, фото товаров, прочее."""
import json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Сайты\rex.moscow"
free = json.load(open(os.path.join(BASE, "data", "_db", "free_images.json"), encoding="utf-8"))
arts = {k: v for k, v in free.items() if re.match(r"2026/08/[A-Z][A-Za-z0-9-]+\.jpg$", k)}
other = {k: v for k, v in free.items() if k not in arts and not k.startswith("porto_placeholders")}
print("обложек статей: %d, прочих: %d" % (len(arts), len(other)))
for k in sorted(other):
    print("  ", k)

# -*- coding: utf-8 -*-
"""Собираем галерею нескольких товаров для визуальной оценки."""
import json, os, shutil, sys
from urllib.parse import unquote
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"E:\Сайты\rex.moscow"
UP = r"D:\Old Sites\rex.moscow\public_html\wp-content\uploads"
OUT = os.path.join(BASE, "data", "_db", "_preview")
os.makedirs(OUT, exist_ok=True)
m = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))


def local(url):
    u = unquote(url or "")
    i = u.find("/wp-content/uploads/")
    if i < 0:
        return None
    return os.path.join(UP, u[i + len("/wp-content/uploads/"):].split("?")[0].replace("/", os.sep))


picks = ["reks-elast-100", "reks-fiks-epo-tiks", "hasoil-sojl", "reks-dekor", "hacut-fleks-snv",
         "reks-strukto-300", "severus-tikso", "reks-gidrolenta", "reks-graut-3-0", "reks-epo-top"]
for slug in picks:
    p = next(x for x in m["products"] if x["slug"] == slug)
    fp = local(p["img"])
    im = Image.open(fp)
    print("%-22s %-14s %s" % (slug, "%dx%d" % im.size, os.path.basename(fp)))
    shutil.copy2(fp, os.path.join(OUT, slug + os.path.splitext(fp)[1]))

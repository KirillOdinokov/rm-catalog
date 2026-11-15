# -*- coding: utf-8 -*-
"""Конвертация картинок из бэкапа в WebP для сайта.

Источник: D:\\Old Sites\\rex.moscow\\public_html\\wp-content\\uploads
Выход:    assets/img/p/<slug>.webp  (товары), assets/img/a/<slug>.webp (обложки статей)
Манифест: data/images.json
"""
import json
import os
import sys
from urllib.parse import unquote

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = r"D:\Old Sites\rex.moscow\public_html\wp-content\uploads"
IMG = os.path.join(BASE, "assets", "img")
MANIFEST = os.path.join(BASE, "data", "images.json")


def src_path(rel):
    return os.path.join(UP, rel.replace("/", os.sep))


def url_to_rel(url):
    u = unquote(url or "")
    i = u.find("/wp-content/uploads/")
    return u[i + len("/wp-content/uploads/"):].split("?")[0] if i >= 0 else None


def save_webp(im, out, quality):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, "WEBP", quality=quality, method=6)
    return os.path.getsize(out)


def product_img(rel, out):
    im = Image.open(src_path(rel)).convert("RGB")
    im.thumbnail((900, 900), Image.LANCZOS)
    return save_webp(im, out, 82)


def cover_img(rel, out, size=(760, 428)):
    im = Image.open(src_path(rel)).convert("RGB")
    tw, th = size
    ratio = max(tw / im.width, th / im.height)
    im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))), Image.LANCZOS)
    left = (im.width - tw) // 2
    top = (im.height - th) // 2
    im = im.crop((left, top, left + tw, top + th))
    return save_webp(im, out, 72)


def main():
    model = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
    covers = json.load(open(os.path.join(BASE, "data", "_db", "post_covers.json"), encoding="utf-8"))
    free = json.load(open(os.path.join(BASE, "data", "_db", "free_images.json"), encoding="utf-8"))
    man = {"products": {}, "articles": {}}
    total = 0

    for p in model["products"]:
        rel = url_to_rel(p.get("img"))
        if not rel or not os.path.isfile(src_path(rel)):
            continue
        out = os.path.join(IMG, "p", p["slug"] + ".webp")
        try:
            size = product_img(rel, out)
        except Exception as e:
            print("  ! %s: %s" % (p["slug"], e))
            continue
        man["products"][p["slug"]] = {"file": "p/%s.webp" % p["slug"], "bytes": size}
        total += size

    for post in model["posts"]:
        rel = free.get(covers.get(post["slug"]) or "")
        if not rel or not os.path.isfile(src_path(rel)):
            continue
        out = os.path.join(IMG, "a", post["slug"] + ".webp")
        try:
            size = cover_img(rel, out)
        except Exception as e:
            print("  ! %s: %s" % (post["slug"], e))
            continue
        man["articles"][post["slug"]] = {"file": "a/%s.webp" % post["slug"], "bytes": size}
        total += size

    man["total_bytes"] = total
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("товаров с фото: %d, обложек статей: %d, всего %.1f МБ"
          % (len(man["products"]), len(man["articles"]), total / 1e6))


if __name__ == "__main__":
    main()

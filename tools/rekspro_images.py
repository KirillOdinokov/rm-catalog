#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""rekspro_images.py — фото завода reks.pro -> assets\img\p\<slug>.webp.

Берём только позиции, у которых нет фото из бэкапа старого сайта.
Завод отдаёт уже WebP; пережимаем в 900 px / q82 и приводим к белому фону,
чтобы фото вставали в карточку так же, как снятые с бэкапа.

Запуск: python tools\rekspro_images.py [--force]
"""
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "rekspro")
IMG_SRC = os.path.join(SRC, "img")
DST = os.path.join(ROOT, "assets", "img", "p")
MANIFEST = os.path.join(ROOT, "data", "images.json")
MATCH = os.path.join(SRC, "match.json")
KB = os.path.join(SRC, "kb.json")

SIZE = 900
Q = 82


def load_jsonl(p):
    out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def main():
    force = "--force" in sys.argv
    model = json.load(open(os.path.join(ROOT, "data", "model.json"), encoding="utf-8"))
    kb = json.load(open(KB, encoding="utf-8"))
    match = json.load(open(MATCH, encoding="utf-8"))
    man = json.load(open(MANIFEST, encoding="utf-8"))
    man.setdefault("products", {})

    # файл на диске по странице товара завода
    by_page = {}
    for r in load_jsonl(os.path.join(SRC, "images.jsonl")):
        pg = (r.get("page") or "").rstrip("/")
        slug = pg.rsplit("/", 1)[-1]
        by_page.setdefault(slug, r["file"])

    os.makedirs(DST, exist_ok=True)
    added, skipped, failed = [], [], []
    for p in model["products"]:
        slug = p["slug"]
        if slug in man["products"] and os.path.exists(os.path.join(ROOT, "assets", "img",
                                                                   man["products"][slug]["file"])):
            skipped.append(slug)
            continue
        m = match.get(slug) or {}
        k = m.get("kb")
        if not k or k not in kb:
            failed.append((slug, "нет пары с заводом"))
            continue
        cand = []
        for u in kb[k].get("img") or []:
            cand.append(u.rsplit("/", 1)[-1])
        f = by_page.get(k)
        if f:
            cand.append(f)
        src = None
        for name in cand:
            if name and os.path.exists(os.path.join(IMG_SRC, name)):
                src = os.path.join(IMG_SRC, name)
                break
        if not src:
            failed.append((slug, "нет файла фото"))
            continue
        try:
            im = Image.open(src)
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
            w, h = im.size
            scale = min(1.0, float(SIZE) / max(w, h))
            if scale < 1.0:
                im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
            out = os.path.join(DST, slug + ".webp")
            im.save(out, "WEBP", quality=Q, method=6)
            man["products"][slug] = {"file": "p/%s.webp" % slug, "bytes": os.path.getsize(out)}
            added.append(slug)
        except Exception as e:
            failed.append((slug, str(e)))
    man["total_bytes"] = sum(v.get("bytes", 0) for k in ("products", "articles")
                             for v in man.get(k, {}).values())
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)

    print("добавлено фото: %d, уже было: %d, без фото: %d" % (len(added), len(skipped), len(failed)))
    for s, why in failed[:40]:
        print("  -", s, "|", why)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Обложки статей из пакета картинок (FLUX / Krea) -> assets/img/a/<slug>.webp + data/images.json.

Имена файлов в архиве — post_id из articles-future/metadata.csv (это же id в flux-prompts.csv),
поэтому связь «картинка -> статья» восстанавливается по metadata.csv, без ручного переименования.

    & $py13 tools\\import_article_covers.py                 # images/images.zip -> сборка
    & $py13 tools\\import_article_covers.py --dry           # только отчёт, без записи
    & $py13 tools\\import_article_covers.py --zip path.zip  # другой архив
    & $py13 tools\\import_article_covers.py --dir path      # папка с webp вместо архива

Геометрия: карточка блога 760×428 (q72). Исходник 1024×576 (16:9) кропится по центру
до нужного соотношения и уменьшается LANCZOS — без искажений и без обрезки сюжета по краям.
"""
import argparse
import csv
import io
import json
import os
import sys
import zipfile

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(BASE, "articles-future", "metadata.csv")
MODEL = os.path.join(BASE, "data", "model.json")
IMAGES = os.path.join(BASE, "data", "images.json")
OUTDIR = os.path.join(BASE, "assets", "img", "a")
W, H, Q = 760, 428, 72


def id_to_slug():
    rows = list(csv.DictReader(open(META, encoding="utf-8-sig")))
    return {str(r["post_id"]).strip(): r["slug"].strip() for r in rows}


def iter_images(zip_path, dir_path):
    """(имя без расширения, функция чтения байтов)."""
    if dir_path:
        for fn in sorted(os.listdir(dir_path)):
            if fn.lower().endswith(".webp"):
                p = os.path.join(dir_path, fn)
                yield os.path.splitext(fn)[0], (lambda p=p: open(p, "rb").read())
        return
    z = zipfile.ZipFile(zip_path)
    for n in z.namelist():
        if n.lower().endswith(".webp"):
            yield os.path.splitext(os.path.basename(n))[0], (lambda n=n: z.read(n))


def fit(im):
    """Кроп по центру до 760:428 и ресайз — соотношение сторон сохраняется."""
    tw, th = W, H
    sw, sh = im.size
    if sw / sh > tw / th:
        nw = int(round(sh * tw / th))
        left = (sw - nw) // 2
        im = im.crop((left, 0, left + nw, sh))
    else:
        nh = int(round(sw * th / tw))
        top = (sh - nh) // 2
        im = im.crop((0, top, sw, top + nh))
    return im.resize((tw, th), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description="Обложки статей из пакета картинок")
    ap.add_argument("--zip", default=os.path.join(BASE, "images", "images.zip"))
    ap.add_argument("--dir", default=None)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    if not a.dir and not os.path.exists(a.zip):
        sys.exit("нет архива: %s" % a.zip)

    i2s = id_to_slug()
    model = json.load(open(MODEL, encoding="utf-8"))
    slugs = {p["slug"] for p in model["posts"]}
    manifest = json.load(open(IMAGES, encoding="utf-8"))
    covers = manifest.setdefault("articles", {})

    done, skipped = [], []
    for pid, reader in iter_images(a.zip, a.dir):
        slug = i2s.get(pid)
        if not slug or slug not in slugs:
            skipped.append((pid, "нет статьи с таким id"))
            continue
        dst = os.path.join(OUTDIR, slug + ".webp")
        if not a.dry:
            os.makedirs(OUTDIR, exist_ok=True)
            im = Image.open(io.BytesIO(reader()))
            if im.mode != "RGB":
                im = im.convert("RGB")
            fit(im).save(dst, "WEBP", quality=Q, method=6)
            covers[slug] = {"file": "a/%s.webp" % slug}
        done.append(slug)

    if not a.dry:
        with open(IMAGES, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)

    size = 0
    for s in done:
        p = os.path.join(OUTDIR, s + ".webp")
        if os.path.exists(p):
            size += os.path.getsize(p)
    print("%s обложек: %d | пропущено: %d | вес файлов: %.1f КБ"
          % ("проверено" if a.dry else "готово", len(done), len(skipped), size / 1024))
    for pid, why in skipped[:10]:
        print("  пропуск %s: %s" % (pid, why))
    if not a.dry:
        print("манифест: %s (статей с обложкой: %d)" % (IMAGES, len(covers)))


if __name__ == "__main__":
    main()

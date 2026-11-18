# -*- coding: utf-8 -*-
"""Починка отдельных обложек статей: умный кроп от рук или брендовая «пластина».

Зачем: генератор иногда рисует крупный план кисти руки (артефакты пальцев) или длинный
текст/чужой логотип, хотя в ТЗ этого не должно быть. Перегенерировать картинку мы не можем,
поэтому два локальных приёма:

  --zoom   взять исходник 1024×576 из images/images.zip и выбрать окно 0.6–0.78 кадра так,
           чтобы в него попала «материя» (инструмент, поверхность), а не кисть: перебор
           сетки смещений по минимуму «телесных» пикселей и максимуму детализации.
  --plate  нарисовать «пластину» в стиле сайта (бумажный фон, сетка, акцентная полоса,
           рубрика, заголовок) — для кадров, где текста/людей слишком много.

    & $py13 tools\\fix_cover.py --zoom beton-kontakt-eto drugoy-slug
    & $py13 tools\\fix_cover.py --plate importozameshhenie-stroitelnoj-himii
    & $py13 tools\\fix_cover.py --revert beton-kontakt-eto     # вернуть исходную версию
"""
import argparse
import io
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(BASE, "images", "images.zip")
META = os.path.join(BASE, "articles-future", "metadata.csv")
MODEL = os.path.join(BASE, "data", "model.json")
COVERS = os.path.join(BASE, "assets", "img", "a")
W, H, Q = 760, 428, 72

INK = (13, 43, 62)
ACC = (0, 136, 204)
PAPER = (242, 248, 252)
GRID = (220, 233, 243)
MUTED = (69, 106, 131)

FONT_DIR = r"C:\Windows\Fonts"
F_TITLE = ("segoeuib.ttf", "arialbd.ttf", "ariblk.ttf")
F_TEXT = ("segoeui.ttf", "arial.ttf")
F_MONO = ("consola.ttf", "cour.ttf")


def font(names, size):
    for n in names:
        p = os.path.join(FONT_DIR, n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def slug_to_id():
    import csv
    out = {}
    with open(META, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["slug"].strip()] = str(r["post_id"]).strip()
    return out


def origin(slug, i2s):
    """Байты исходной картинки из архива по post_id."""
    pid = i2s.get(slug)
    if not pid:
        return None
    z = zipfile.ZipFile(ZIP)
    for n in z.namelist():
        if os.path.splitext(os.path.basename(n))[0] == pid:
            return z.read(n)
    return None


def skin_score(im):
    """Относительная «телесность»: тёплые средненасыщенные пиксели."""
    small = im.resize((im.width // 3, im.height // 3)).convert("RGB")
    px = small.load()
    w, h = small.size
    hit = 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            mx, mn = max(r, g, b), min(r, g, b)
            if mx < 70 or mx > 250:
                continue
            sat = (mx - mn) / mx
            if r >= g >= b and 0.18 <= sat <= 0.62 and (r - b) >= 20 and (r - g) >= 8:
                hit += 1
    return hit / float(w * h)


def detail(im):
    g = im.convert("L")
    hist = g.histogram()
    return sum(hist[40:]) / float(sum(hist) or 1)


def zoom_fix(raw, keep=0.68):
    """Выбрать окно keep×keep кадра с минимумом «кожи» и достаточной детализацией."""
    src = Image.open(io.BytesIO(raw)).convert("RGB")
    sw, sh = src.size
    ww, wh = int(sw * keep), int(sh * keep)
    best = None
    for fy in (0.0, 0.15, 0.3, 0.45, 0.6):
        for fx in (0.0, 0.15, 0.3, 0.45, 0.6):
            x = int((sw - ww) * fx)
            y = int((sh - wh) * fy)
            win = src.crop((x, y, x + ww, y + wh))
            sc = skin_score(win)
            dt = detail(win)
            # меньше кожи — лучше; при равенстве — больше деталей
            key = (round(sc, 4), -round(dt, 4))
            if best is None or key < best[0]:
                best = (key, win, sc, dt)
    win = best[1]
    # дотягиваем до 760×428 с сохранением пропорций
    tw, th = W, H
    ww2, wh2 = win.size
    if ww2 / wh2 > tw / th:
        nw = int(round(wh2 * tw / th))
        left = (ww2 - nw) // 2
        win = win.crop((left, 0, left + nw, wh2))
    else:
        nh = int(round(ww2 * th / tw))
        top = (wh2 - nh) // 2
        win = win.crop((0, top, ww2, top + nh))
    return win.resize((tw, th), Image.LANCZOS), best[2], best[3]


def plate_cover(slug, title, category):
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 38):
        d.line([(x, 0), (x, H)], fill=GRID)
    for y in range(0, H, 38):
        d.line([(0, y), (W, y)], fill=GRID)
    d.rectangle([0, 0, 8, H], fill=ACC)
    fm = font(F_MONO, 13)
    ft = font(F_TITLE, 30)
    d.text((34, 30), (category or "СТАТЬЯ").upper()[:52], font=fm, fill=MUTED)
    # заголовок: подбираем кегль и переносим по словам
    words = (title or slug).split()
    for size in (34, 31, 28, 25, 22):
        ft = font(F_TITLE, size)
        line_h = int(size * 1.22)
        lines, cur = [], ""
        for wd in words:
            probe = (cur + " " + wd).strip()
            if d.textlength(probe, font=ft) <= W - 70:
                cur = probe
            else:
                if cur:
                    lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        if len(lines) <= 3:
            break
    y = 62
    for line in lines[:3]:
        d.text((34, y), line, font=ft, fill=INK)
        y += line_h
    d.line([(34, H - 46), (W - 34, H - 46)], fill=GRID, width=2)
    d.text((34, H - 36), "Rex.moscow", font=fm, fill=ACC)
    return im


def main():
    ap = argparse.ArgumentParser(description="Починка обложек: умный кроп или пластина")
    ap.add_argument("--zoom", nargs="+", metavar="SLUG")
    ap.add_argument("--keep", type=float, default=0.68, help="доля кадра при кропе (0.55–0.8)")
    ap.add_argument("--plate", nargs="+", metavar="SLUG")
    ap.add_argument("--revert", nargs="+", metavar="SLUG")
    a = ap.parse_args()

    i2s = slug_to_id()
    model = {p["slug"]: p for p in json.load(open(MODEL, encoding="utf-8"))["posts"]}
    os.makedirs(COVERS, exist_ok=True)

    if a.zoom:
        for slug in a.zoom:
            raw = origin(slug, i2s)
            if not raw:
                print("  нет исходника: %s" % slug)
                continue
            im, sc, dt = zoom_fix(raw, keep=a.keep)
            im.save(os.path.join(COVERS, slug + ".webp"), "WEBP", quality=Q, method=6)
            print("  кроп %-58s кожа %.3f детали %.3f" % (slug[:58], sc, dt))

    if a.plate:
        cat = {"gidroizolyaciya": "Гидроизоляция", "remont-betona": "Ремонт бетона",
               "promyshlennye-poly": "Промышленные полы", "zashhita-betona": "Защита бетона",
               "kleevye-ankernye-sistemy": "Клеевые и анкерные системы"}
        for slug in a.plate:
            p = model.get(slug)
            if not p:
                print("  нет статьи: %s" % slug)
                continue
            im = plate_cover(slug, p.get("title", ""), cat.get(p.get("category"), "Статья"))
            im.save(os.path.join(COVERS, slug + ".webp"), "WEBP", quality=Q, method=6)
            print("  пластина %s" % slug)

    if a.revert:
        from PIL import Image as I
        for slug in a.revert:
            raw = origin(slug, i2s)
            if not raw:
                print("  нет исходника: %s" % slug)
                continue
            src = I.open(io.BytesIO(raw)).convert("RGB")
            sw, sh = src.size
            nw = int(round(sh * W / H))
            left = (sw - nw) // 2
            src = src.crop((left, 0, left + nw, sh)).resize((W, H), I.LANCZOS)
            src.save(os.path.join(COVERS, slug + ".webp"), "WEBP", quality=Q, method=6)
            print("  возвращено как было: %s" % slug)


if __name__ == "__main__":
    main()

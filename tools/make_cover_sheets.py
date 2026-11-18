# -*- coding: utf-8 -*-
"""Контактные листы обложек для визуальной вычитки (по 30 штук на лист).

    & $py13 tools\\make_cover_sheets.py            # -> shots/sheets/sheet-01.png ...
"""
import os
import sys

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "assets", "img", "a")
OUT = os.path.join(BASE, "shots", "sheets")
COLS, ROWS, TW, TH, PAD, LABEL = 6, 5, 240, 135, 6, 16
PER = COLS * ROWS


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".webp"))
    sheets = 0
    for si in range(0, len(files), PER):
        chunk = files[si:si + PER]
        w = COLS * (TW + PAD) + PAD
        h = ROWS * (TH + LABEL + PAD) + PAD
        sheet = Image.new("RGB", (w, h), (13, 43, 62))
        d = ImageDraw.Draw(sheet)
        for i, fn in enumerate(chunk):
            col, row = i % COLS, i // COLS
            x = PAD + col * (TW + PAD)
            y = PAD + row * (TH + LABEL + PAD)
            im = Image.open(os.path.join(SRC, fn)).convert("RGB").resize((TW, TH), Image.LANCZOS)
            sheet.paste(im, (x, y))
            d.text((x + 2, y + TH + 2), "%d. %s" % (si + i + 1, fn[:-5][:34]), fill=(200, 220, 235))
        sheets += 1
        sheet.save(os.path.join(OUT, "sheet-%02d.png" % sheets), "PNG", optimize=True)
    print("листов: %d | обложек: %d | папка: %s" % (sheets, len(files), OUT))


if __name__ == "__main__":
    main()

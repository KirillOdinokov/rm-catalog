# -*- coding: utf-8 -*-
"""Починка двойной перекодировки UTF-8 -> CP1251 -> UTF-8 (побайтово)."""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Сайты\rex.moscow"

MARKERS = ("РЎ", "С‚", "Р°", "Рµ", "Рѕ", "СЂ", "РїСЂ", "РЎР")


def looks_broken(text):
    return sum(text.count(m) for m in MARKERS) >= 5


def to_bytes(text):
    """Обратное преобразование: символы U+0080..U+04FF -> байты windows-1251."""
    out = bytearray()
    for ch in text:
        o = ord(ch)
        if o < 0x100:
            out.append(o)
        elif 0x410 <= o <= 0x44F:
            out.append(o - 0x410 + 0xC0)
        elif ch == "Ё":
            out.append(0xA8)
        elif ch == "ё":
            out.append(0xB8)
        else:
            out.extend(ch.encode("cp1251", errors="replace"))
    return bytes(out)


def repair(text):
    if text.startswith("\ufeff"):
        text = text[1:]
    return to_bytes(text).decode("utf-8", errors="strict")


fixed, failed = [], []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in ("dist", "__pycache__", "_db", "img", "fonts", ".git")]
    for f in files:
        if not f.endswith((".py", ".md", ".css", ".js", ".json", ".sh")):
            continue
        p = os.path.join(root, f)
        if os.path.abspath(p) == os.path.abspath(__file__):
            continue
        try:
            t = open(p, encoding="utf-8").read()
        except Exception:
            continue
        if not looks_broken(t):
            continue
        try:
            fixed_t = repair(t)
        except Exception as e:
            failed.append((p, str(e)))
            continue
        open(p, "w", encoding="utf-8", newline="\n").write(fixed_t)
        fixed.append(p)

print("починено:", len(fixed))
for p in fixed:
    print("   ", os.path.relpath(p, BASE))
for p, why in failed:
    print("ОШИБКА", os.path.relpath(p, BASE), why)

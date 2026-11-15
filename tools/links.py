# -*- coding: utf-8 -*-
"""Проверка внутренних ссылок и ассетов в собранном rex."""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

files = []
for r, _d, fs in os.walk(ROOT):
    for f in fs:
        if f.endswith(".html"):
            files.append(os.path.join(r, f))

exists = set()
for r, _d, fs in os.walk(ROOT):
    for f in fs:
        rel = os.path.relpath(os.path.join(r, f), ROOT).replace("\\", "/")
        exists.add(rel)
        if rel.endswith(".html") and rel != "index.html":
            exists.add(rel[:-5])
        if rel.endswith("index.html"):
            exists.add(os.path.dirname(rel).rstrip("/") or "/")

bad = {}
links = 0
for fp in files:
    html = open(fp, encoding="utf-8").read()
    for m in re.finditer(r'(?:href|src)="(/[^"#?]*)"', html):
        u = m.group(1)
        if u.startswith("/assets"):
            key = u.lstrip("/")
            if key not in exists:
                bad.setdefault(u, set()).add(os.path.relpath(fp, ROOT))
            links += 1
            continue
        key = u.lstrip("/").rstrip("/")
        links += 1
        if key and key not in exists:
            bad.setdefault(u, set()).add(os.path.relpath(fp, ROOT))

print("html:", len(files), "links checked:", links, "broken:", len(bad))
for u, srcs in sorted(bad.items(), key=lambda x: -len(x[1]))[:25]:
    print("  %-60s in %d files, e.g. %s" % (u, len(srcs), list(srcs)[0]))

# -*- coding: utf-8 -*-
"""Сверка собранных сайтов с архивными URL."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# архивный CDX-снимок rex.moscow (внешний источник, см. AGENTS.md)
CDX = r"E:\Design\rex_audit\cdx_rex_moscow.json"


def rex_urls():
    rows = json.load(open(CDX, encoding="utf-8"))
    out = {}
    for r in rows:
        if r["statuscode"] != "200" or "html" not in (r["mimetype"] or ""):
            continue
        u = r["original"].split("?")[0]
        if re.search(r"/(tag|wp-|feed|xmlrpc|my-account|wordfence|sitemap|robots|cart|checkout|wishlist)", u):
            continue
        if "?s=" in r["original"]:
            continue
        path = u.split("rex.moscow", 1)[-1] or "/"
        out[path.rstrip("/") or "/"] = u
    return out


def spb_urls():
    inv = json.load(open(r"E:\Design\gidroshponki_build\data\spb_inventory.json", encoding="utf-8"))
    urls = [p["url"] for p in inv["products"]] + [c["url"] for c in inv["cats"]] + \
           [a["url"] for a in inv["attrs"]] + ["/", "/shop/", "/kontakty/", "/enquiry-cart/", "/sample-page/"]
    return {u: u for u in urls}


def check_rex():
    root = os.path.join(BASE, "dist")
    files = set()
    for r, _d, fs in os.walk(root):
        for f in fs:
            rel = os.path.relpath(os.path.join(r, f), root).replace("\\", "/")
            files.add(rel)
            if rel.endswith(".html"):
                files.add(rel[:-5])
    urls = rex_urls()
    ok, miss = [], []
    for path, orig in urls.items():
        key = path.lstrip("/")
        (ok if (key == "" or key in files) else miss).append(path)
    print("REX: архивных URL %d, совпало %d, нет %d" % (len(urls), len(ok), len(miss)))
    for m in sorted(miss):
        print("   MISS", m)
    return len(urls), len(ok), miss


def check_spb():
    root = r"E:\Design\spb\dist"
    urls = spb_urls()
    ok, miss = [], []
    for path in urls:
        rel = path.strip("/")
        fp = os.path.join(root, rel, "index.html")
        (ok if os.path.exists(fp) else miss).append(path)
    print("SPB: архивных URL %d, совпало %d, нет %d" % (len(urls), len(ok), len(miss)))
    for m in sorted(miss)[:20]:
        print("   MISS", m)
    return len(urls), len(ok), miss


if __name__ == "__main__":
    check_rex()
    check_spb()

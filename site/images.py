# -*- coding: utf-8 -*-
"""Фотографии товаров и обложки статей (WebP), собранные из бэкапа сайта.

Манифест готовит tools/make_images.py -> data/images.json.
"""
import json
import os

import config as C

_M = None


def manifest():
    global _M
    if _M is None:
        path = os.path.join(C.DATA, "images.json")
        if os.path.exists(path):
            _M = json.load(open(path, encoding="utf-8"))
        else:
            _M = {"products": {}, "articles": {}}
    return _M


def product(p):
    """Относительный путь к фото товара или ''."""
    rec = manifest()["products"].get(p.get("slug") or "")
    return rec["file"] if rec else ""


def article(post):
    rec = manifest()["articles"].get(post.get("slug") or "")
    return rec["file"] if rec else ""


def tag(path, alt, cls="", w=600, h=600, eager=False):
    return ('<img src="/assets/img/%s" alt="%s"%s width="%d" height="%d" '
            'loading="%s" decoding="async">'
            % (path, alt, (' class="%s"' % cls) if cls else "", w, h,
               "eager" if eager else "lazy"))

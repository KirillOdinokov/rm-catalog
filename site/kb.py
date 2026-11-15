# -*- coding: utf-8 -*-
r"""kb.py — факты завода РЕКС из базы знаний (data\rekspro\kb.json + match.json).

Данные собраны с официального сайта производителя https://reks.pro скриптами
tools\rekspro_crawl.py, tools\rekspro_assets.py, tools\build_kb_rekspro.py.
Сопоставление карточек сайта с карточками завода — tools\rekspro_match.py
(ручные пары и исключения — data\rekspro\manual_match.json).

Используется: site\content.py (описания товаров), site\pages.py (характеристики).
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "data", "rekspro")

_kb = None
_match = None


def _load():
    global _kb, _match
    if _kb is not None:
        return
    _kb, _match = {}, {}
    p = os.path.join(_SRC, "kb.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            _kb = json.load(f)
    p = os.path.join(_SRC, "match.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            _match = json.load(f)


def facts(slug):
    """Факты завода для карточки сайта или None."""
    _load()
    m = _match.get(slug) or {}
    key = m.get("kb")
    if not key:
        return None
    f = _kb.get(key)
    if not f:
        return None
    out = dict(f)
    out["color_site"] = m.get("color") or ""
    out["kb_slug"] = key
    return out


def sections():
    _load()
    return _kb.get("_sections") or {}


def section_name(parts):
    """Названия разделов завода по списку slug'ов из URL."""
    names = sections()
    return [names.get(x, x.replace("-", " ")) for x in (parts or [])]


def docs():
    _load()
    return _kb.get("_docs") or {}


def stats():
    _load()
    return {"kb": len([k for k in _kb if not k.startswith("_")]),
            "matched": len([k for k, v in _match.items() if v.get("kb")])}

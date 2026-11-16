# -*- coding: utf-8 -*-
"""Сколько цен отличается от последнего успешного деплоя.

Сравнивает data/price_pending.json (цены, которые сейчас в model.json)
с data/price_deployed.json (снимок, сделанный после выкладки).
Печатает число различающихся позиций; если снимка нет — 1 (нужен деплой).
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING = os.path.join(BASE, "data", "price_pending.json")
DEPLOYED = os.path.join(BASE, "data", "price_deployed.json")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("prices") or {}
    except Exception:
        return None


pending = load(PENDING)
deployed = load(DEPLOYED)
if pending is None:
    print(0)
    sys.exit(0)
if deployed is None:
    print(1)
    sys.exit(0)

keys = set(pending) | set(deployed)
diff = 0
for key in keys:
    if (pending.get(key) or 0) != (deployed.get(key) or 0):
        diff += 1
print(diff)

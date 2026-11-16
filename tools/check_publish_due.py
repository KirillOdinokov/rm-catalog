# -*- coding: utf-8 -*-
"""Проверка: есть ли статьи, которые должны быть опубликованы (publish_at <= сегодня),
но которых ещё нет в dist (т.е. сборка не запускалась после наступления даты).

Печатает ЧИСЛО таких статей (0 = всё актуально). Используется в sync_and_deploy.sh,
чтобы триггерить пересборку при отложенной публикации.
"""
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
DIST = os.path.join(BASE, "dist")

today = date.today().isoformat()

try:
    m = json.load(open(MODEL, encoding="utf-8"))
except Exception:
    print(0)
    sys.exit(0)

due = []
for p in m.get("posts", []):
    pa = (p.get("publish_at") or "").strip()
    if not pa:
        continue
    m2 = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", pa)
    if m2:
        pa = "%s-%s-%s" % (m2.group(3), m2.group(2), m2.group(1))
    if pa <= today:
        if not os.path.exists(os.path.join(DIST, p["slug"] + ".html")):
            due.append({"slug": p["slug"], "title": p.get("title") or p["slug"]})

if "--json" in sys.argv:
    print(json.dumps(due, ensure_ascii=False))
else:
    print(len(due))

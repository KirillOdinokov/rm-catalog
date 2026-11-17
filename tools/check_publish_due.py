# -*- coding: utf-8 -*-
"""Проверка: есть ли статьи, которые должны быть опубликованы (publish_at <= сегодня),
но которых ещё нет в dist (т.е. сборка не запускалась после наступления даты).

Печатает ЧИСЛО таких статей (0 = всё актуально). Используется в sync_and_deploy.sh,
чтобы триггерить пересборку при отложенной публикации.

Время публикации: статья выходит не раньше PUBLISH_HOUR (по умолчанию 10:00) —
cron на flux ходит часто, поэтому фактический выход попадает в 10:00–11:00.
Просроченные статьи (publish_at раньше сегодня) публикуются сразу, без ожидания часа:
если сервер лежал, догоняем при первом же запуске.

    python tools/check_publish_due.py          # число статей к публикации
    python tools/check_publish_due.py --json   # те же статьи списком
    python tools/check_publish_due.py --why    # объяснение, что и почему ждёт
"""
import json
import os
import re
import sys
from datetime import date, datetime

sys.stdout.reconfigure(encoding="utf-8", errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
DIST = os.path.join(BASE, "dist")

# час, раньше которого статьи не выходят (по местному времени сервера — flux в Москве)
try:
    PUBLISH_HOUR = int(os.environ.get("PUBLISH_HOUR", "10"))
except ValueError:
    PUBLISH_HOUR = 10

now = datetime.now()
today = date.today().isoformat()

try:
    m = json.load(open(MODEL, encoding="utf-8"))
except Exception:
    print(0)
    sys.exit(0)

due = []
waiting = []
for p in m.get("posts", []):
    pa = (p.get("publish_at") or "").strip()
    if not pa:
        continue
    m2 = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", pa)
    if m2:
        pa = "%s-%s-%s" % (m2.group(3), m2.group(2), m2.group(1))
    if pa > today:
        continue
    if os.path.exists(os.path.join(DIST, p["slug"] + ".html")):
        continue                      # уже в сборке
    if pa < today:
        due.append({"slug": p["slug"], "title": p.get("title") or p["slug"],
                    "publish_at": pa})
    elif now.hour >= PUBLISH_HOUR:
        due.append({"slug": p["slug"], "title": p.get("title") or p["slug"],
                    "publish_at": pa})
    else:
        waiting.append({"slug": p["slug"], "publish_at": pa})

if "--json" in sys.argv:
    print(json.dumps(due, ensure_ascii=False))
elif "--why" in sys.argv:
    print("сейчас %s, публикация не раньше %02d:00" % (now.strftime("%Y-%m-%d %H:%M"),
                                                      PUBLISH_HOUR))
    print("к публикации: %d" % len(due))
    for d in due:
        print("  %s  %s" % (d["publish_at"], d["slug"]))
    if waiting:
        print("ждём %02d:00 сегодня: %d" % (PUBLISH_HOUR, len(waiting)))
        for w in waiting:
            print("  %s  %s" % (w["publish_at"], w["slug"]))
else:
    print(len(due))

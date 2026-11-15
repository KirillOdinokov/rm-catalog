# -*- coding: utf-8 -*-
"""Пересборка расписания импортированных статей: по одной в рабочий день.

Выходные и праздники пропускаются. Праздники — фиксированный список (его легко
пополнить, когда выйдет производственный календарь на 2027 год: переносы там ещё
не утверждены, поэтому учитываем только сами даты).

    & $py tools\\reschedule_articles.py --start 2026-11-16          # записать
    & $py tools\\reschedule_articles.py --start 2026-11-16 --dry    # показать
"""
import json
import os
import sys
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
DATES = os.path.join(BASE, "data", "post_dates.json")

HOLIDAYS = {
    # 2026 (переносы уже действуют)
    "2026-11-04", "2026-12-31",
    # 2027 — федеральные праздники; переносы добавить после публикации календаря
    "2027-01-01", "2027-01-02", "2027-01-03", "2027-01-04", "2027-01-05",
    "2027-01-06", "2027-01-07", "2027-01-08",
    "2027-02-23", "2027-03-08", "2027-05-01", "2027-05-09", "2027-06-12", "2027-11-04",
}


def workdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
            out.append(d)
        d += timedelta(days=1)
    return out


def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    start = date.fromisoformat(args[args.index("--start") + 1]) if "--start" in args \
        else date(2026, 11, 16)

    model = json.load(open(MODEL, encoding="utf-8"))
    posts = [p for p in model["posts"] if p.get("file")]
    order = sorted(posts, key=lambda p: (p.get("publish_at") or "", p["slug"]))
    days = workdays(start, len(order))
    print("статей:", len(order), "| первая:", days[0], "| последняя:", days[-1])

    dates = json.load(open(DATES, encoding="utf-8"))
    for p, d in zip(order, days):
        p["publish_at"] = d.isoformat()
        rec = dates.setdefault(p["slug"], {})
        rec["published"] = d.isoformat()

    months = {}
    for d in days:
        months[d.strftime("%Y-%m")] = months.get(d.strftime("%Y-%m"), 0) + 1
    print("по месяцам:", ", ".join("%s: %d" % (k, v) for k, v in sorted(months.items())))

    if dry:
        print("--dry: не записано")
        return
    json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(dates, open(DATES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("записано")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Сообщить «Базе» о вышедших статьях — для уведомлений в веб-интерфейсе.

Запускается из sync_and_deploy.sh после успешной сборки и выкладки.
 BASE_NOTIFY_URL — http://127.0.0.1:8001/api/site/events
 BASE_NOTIFY_KEY — ключ (METRICS_KEY из /home/kirill/flux/.env)
"""
import argparse
import json
import os
import sys
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="JSON со списком {slug,title}")
    parser.add_argument("--site-id", type=int, default=6)
    args = parser.parse_args()

    key = os.getenv("BASE_NOTIFY_KEY", "")
    if not key:
        print("BASE_NOTIFY_KEY пуст — уведомление не отправлено")
        return 0
    try:
        items = json.load(open(args.file, encoding="utf-8"))
    except Exception as exc:
        print("не прочитать %s: %s" % (args.file, exc))
        return 1
    if not items:
        return 0

    url = os.getenv("BASE_NOTIFY_URL", "http://127.0.0.1:8001/api/site/events")
    payload = json.dumps(
        {"site_id": args.site_id, "items": items}, ensure_ascii=False
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "X-Notify-Key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("notify:", resp.status, resp.read().decode())
    except Exception as exc:
        print("notify failed:", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

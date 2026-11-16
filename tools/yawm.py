# -*- coding: utf-8 -*-
"""Яндекс.Вебмастер: состояние сайта, sitemap, диагностика, запросы, переобход.

Токен берётся из deploy/yandex-token.json (см. tools/ya_api.py --url / --code).

    python tools/yawm.py                  # сводка по rex.moscow
    python tools/yawm.py --sitemaps       # только sitemap: известные и добавленные вручную
    python tools/yawm.py --add-sitemap https://rex.moscow/sitemap.xml
    python tools/yawm.py --del-sitemap <sitemap_id>
    python tools/yawm.py --diag           # диагностика: что Вебмастер считает проблемой
    python tools/yawm.py --queries 20     # популярные поисковые запросы
    python tools/yawm.py --recrawl https://rex.moscow/reks-sil
    python tools/yawm.py --quota          # остаток квоты на переобход
"""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ya_api as Y

WM = Y.WEBMASTER_API


def ctx(cfg, token):
    uid = Y.api(WM + "/user/", token)["user_id"]
    hosts = Y.api("%s/user/%s/hosts/" % (WM, uid), token).get("hosts", [])
    want = cfg.get("WEBMASTER_HOST", "rex.moscow")
    for h in hosts:
        if want in (h.get("ascii_host_url") or "") or want in (h.get("unicode_host_url") or ""):
            return uid, h["host_id"], h
    sys.exit("в Вебмастере нет хоста %s; есть: %s"
             % (want, ", ".join(h["host_id"] for h in hosts)))


def days_back(n):
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - n * 86400))


def sitemaps(uid, hid, token):
    allsm = Y.api("%s/user/%s/hosts/%s/sitemaps/" % (WM, uid, hid), token).get("sitemaps", [])
    added = Y.api("%s/user/%s/hosts/%s/user-added-sitemaps" % (WM, uid, hid),
                  token).get("sitemaps", [])
    added_ids = {s["sitemap_id"] for s in added}
    print("sitemap, известные Вебмастеру: %d" % len(allsm))
    for s in allsm:
        src = ",".join(s.get("sources") or [])
        print("  %-58s URL=%s ошибок=%s источник=%s%s"
              % (s.get("sitemap_url"), s.get("urls_count"), s.get("errors_count"), src,
                 "  [добавлен вручную]" if s.get("sitemap_id") in added_ids else ""))
        if s.get("last_access_date"):
            print("      последнее скачивание: %s" % s["last_access_date"][:16])
    # в Вебмастере наш sitemap живёт под именем sitemap_index.xml (имя сменить нельзя,
    # POST-методы API отдают 504) — сборка пишет один и тот же файл под двумя именами
    if "sitemap_index.xml" not in "".join(s.get("sitemap_url", "") for s in allsm):
        print("  ! в списке нет sitemap_index.xml — добавить: --add-sitemap https://%s/sitemap_index.xml"
              % "rex.moscow")
    return allsm, added


def cmd_summary(cfg, token, uid, hid, host):
    print("хост: %s (%s)" % (host.get("unicode_host_url", hid), hid))
    ver = Y.api("%s/user/%s/hosts/%s/verification/" % (WM, uid, hid), token)
    print("права: %s, способ %s, uin %s, проверено %s"
          % (ver.get("verification_state"), ver.get("verification_type"),
             ver.get("verification_uin"), (ver.get("latest_verification_time") or "")[:10]))

    try:
        s = Y.api("%s/user/%s/hosts/%s/summary/" % (WM, uid, hid), token)
        sqi = s.get("sqi")
        if isinstance(sqi, dict):
            sqi = sqi.get("value")
        print("ИКС: %s" % (sqi if sqi is not None else "—"))
        for k, v in s.items():
            if k == "sqi":
                continue
            if isinstance(v, (int, float, str)):
                print("%s: %s" % (k, v))
        for k in ("searchable_pages_count", "excluded_pages_count"):
            v = s.get(k)
            if isinstance(v, dict):
                v = v.get("value")
            if v is not None:
                print("%s: %s" % (k, v))
    except SystemExit as e:
        print("summary: %s" % str(e)[:300])

    print()
    sitemaps(uid, hid, token)

    print()
    try:
        hist = Y.api("%s/user/%s/hosts/%s/search-urls/in-search/history/" % (WM, uid, hid),
                     token, {"date_from": days_back(60), "date_to": today()})
        h = hist.get("history") or []
        if h:
            print("страниц в поиске: %d (последнее значение %s на %s)"
                  % (h[-1].get("value", 0), h[-1].get("value"), (h[-1].get("date") or "")[:10]))
            print("  динамика за 60 дней: %s" % ", ".join(str(x.get("value")) for x in h[-10:]))
        else:
            print("страниц в поиске: данных нет (сайт новый для Яндекса)")
    except SystemExit as e:
        print("in-search: %s" % str(e)[:200])

    idx = Y.api("%s/user/%s/hosts/%s/indexing/history/" % (WM, uid, hid), token,
                {"date_from": days_back(14), "date_to": today()})
    ind = idx.get("indicators") or {}
    if ind:
        for name, points in ind.items():
            total = sum(p.get("value") or 0 for p in points)
            print("%s за 14 дней: %s (точек %d)" % (name, total, len(points)))

    print()
    try:
        q = Y.api("%s/user/%s/hosts/%s/recrawl/quota/" % (WM, uid, hid), token)
        print("квота переобхода: %s" % q.get("daily_quota"))
    except SystemExit as e:
        print("квота: %s" % str(e)[:200])


def today():
    return time.strftime("%Y-%m-%d")


def cmd_diag(cfg, token, uid, hid, host):
    data = Y.api("%s/user/%s/hosts/%s/diagnostics/" % (WM, uid, hid), token)
    probs = data.get("problems") or {}
    if isinstance(probs, list):
        probs = {str(x): {} for x in probs}
    order = {"FATAL": 0, "CRITICAL": 1, "POSSIBLE_PROBLEM": 2, "RECOMMENDATION": 3}
    present = [(k, v) for k, v in probs.items() if (v or {}).get("state") != "ABSENT"]
    present.sort(key=lambda kv: order.get((kv[1] or {}).get("severity"), 9))
    print("проверок всего: %d, сработало: %d" % (len(probs), len(present)))
    for k, v in present:
        print("  %-14s %-34s %s" % (v.get("severity"), k,
                                    (v.get("last_state_update") or "")[:10]))


def cmd_queries(cfg, token, uid, hid, host, n):
    data = Y.api("%s/user/%s/hosts/%s/search-queries/popular/" % (WM, uid, hid), token, {
        "order_by": "TOTAL_SHOWS", "query_indicator": "TOTAL_SHOWS",
        "date_from": days_back(30), "date_to": today(),
    })
    qs = data.get("queries") or []
    print("запросов за 30 дней: %d" % data.get("count", len(qs)))
    for q in qs[:n]:
        ind = q.get("indicators") or {}
        print("  %-50s показов %s, кликов %s, позиция %s"
              % (q.get("query_text", "")[:50], ind.get("TOTAL_SHOWS"),
                 ind.get("TOTAL_CLICKS"), ind.get("AVG_SHOW_POSITION")))


def cmd_add_sitemap(cfg, token, uid, hid, host, url):
    res = Y.api("%s/user/%s/hosts/%s/user-added-sitemaps" % (WM, uid, hid), token,
                method="POST", body={"url": url})
    print("добавлен sitemap: %s -> id %s" % (url, res.get("sitemap_id")))


def cmd_del_sitemap(cfg, token, uid, hid, host, sid):
    Y.api("%s/user/%s/hosts/%s/user-added-sitemaps/%s" % (WM, uid, hid, sid), token,
          method="DELETE")
    print("удалён sitemap: %s" % sid)


def cmd_recrawl(cfg, token, uid, hid, host, url):
    res = Y.api("%s/user/%s/hosts/%s/recrawl/queue/" % (WM, uid, hid), token,
                method="POST", body={"url": url})
    print("отправлено на переобход: %s (task %s, остаток квоты %s)"
          % (url, res.get("task_id"), res.get("quota_remainder")))


def cmd_quota(cfg, token, uid, hid, host):
    q = Y.api("%s/user/%s/hosts/%s/recrawl/quota/" % (WM, uid, hid), token)
    print("квота переобхода на сутки: %s" % q.get("daily_quota"))


def main():
    p = argparse.ArgumentParser(description="Яндекс.Вебмастер для rex.moscow")
    p.add_argument("--sitemaps", action="store_true")
    p.add_argument("--add-sitemap", metavar="URL")
    p.add_argument("--del-sitemap", metavar="ID")
    p.add_argument("--diag", action="store_true")
    p.add_argument("--queries", type=int, metavar="N", nargs="?", const=20)
    p.add_argument("--recrawl", metavar="URL")
    p.add_argument("--quota", action="store_true")
    a = p.parse_args()

    cfg = Y.load_env()
    token = Y.get_token(cfg)
    uid, hid, host = ctx(cfg, token)

    if a.sitemaps:
        sitemaps(uid, hid, token)
    elif a.add_sitemap:
        cmd_add_sitemap(cfg, token, uid, hid, host, a.add_sitemap)
    elif a.del_sitemap:
        cmd_del_sitemap(cfg, token, uid, hid, host, a.del_sitemap)
    elif a.diag:
        cmd_diag(cfg, token, uid, hid, host)
    elif a.queries:
        cmd_queries(cfg, token, uid, hid, host, a.queries)
    elif a.recrawl:
        cmd_recrawl(cfg, token, uid, hid, host, a.recrawl)
    elif a.quota:
        cmd_quota(cfg, token, uid, hid, host)
    else:
        cmd_summary(cfg, token, uid, hid, host)


if __name__ == "__main__":
    main()

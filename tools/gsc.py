# -*- coding: utf-8 -*-
"""Google Search Console для rex.moscow через сервисный аккаунт.

Ключ: E:\\Оптимизация\\геосинтетика.москва\\zinc-authority-331923-5b10ba931090.json
Аккаунт: console@zinc-authority-331923.iam.gserviceaccount.com

    & $py313 tools\\gsc.py --status     # свойства и статус sitemap
    & $py313 tools\\gsc.py --verify     # подтвердить свойство по meta-тегу
    & $py313 tools\\gsc.py --submit     # добавить свойство и отправить sitemap
    & $py313 tools\\gsc.py --report     # топ запросов и страниц за 28 дней
"""
import sys
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = r"E:\Оптимизация\геосинтетика.москва\zinc-authority-331923-5b10ba931090.json"
SCOPES = ["https://www.googleapis.com/auth/webmasters",
          "https://www.googleapis.com/auth/siteverification"]
SITE = "https://rex.moscow/"
SITEMAP = "https://rex.moscow/sitemap.xml"


def clients():
    creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)
    return (build("searchconsole", "v1", credentials=creds, cache_discovery=False),
            build("siteVerification", "v1", credentials=creds, cache_discovery=False))


def status(sc):
    print("свойства аккаунта:")
    for e in sc.sites().list().execute().get("siteEntry", []):
        mark = "  <-- наш" if "rex.moscow" in e["siteUrl"] else ""
        print("   %-42s %s%s" % (e["siteUrl"], e["permissionLevel"], mark))
    print("\nsitemap:")
    for it in sc.sitemaps().list(siteUrl=SITE).execute().get("sitemap", []):
        print("   %s\n   скачан: %s | ошибок: %s | предупреждений: %s" % (
            it.get("path"), it.get("lastDownloaded"), it.get("errors"), it.get("warnings")))
        for c in it.get("contents", []):
            print("   URL подано: %s, проиндексировано: %s" % (c.get("submitted"), c.get("indexed")))


def verify(sv, sc):
    try:
        res = sv.webResource().insert(
            verificationMethod="META",
            body={"site": {"type": "SITE", "identifier": SITE}}).execute()
        print("подтверждено:", res.get("id"))
    except Exception as exc:
        print("подтверждение:", type(exc).__name__, str(exc)[:300])
    for _ in range(3):
        got = [e for e in sc.sites().list().execute().get("siteEntry", [])
               if "rex.moscow" in e["siteUrl"]]
        if got:
            print("в Search Console:", got[0]["permissionLevel"])
            return
        time.sleep(10)
    print("в Search Console пока не видно — попробуйте --submit")


def submit(sc):
    try:
        sc.sites().add(siteUrl=SITE).execute()
        print("свойство добавлено в Search Console")
    except Exception as exc:
        print("sites.add:", type(exc).__name__, str(exc)[:200])
    try:
        sc.sitemaps().submit(siteUrl=SITE, feedpath=SITEMAP).execute()
        print("sitemap отправлен:", SITEMAP)
    except Exception as exc:
        print("sitemaps.submit:", type(exc).__name__, str(exc)[:250])


def report(sc):
    body = {"startDate": "2026-10-19", "endDate": "2026-11-16",
            "dimensions": ["query"], "rowLimit": 15}
    try:
        rows = sc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])
    except Exception as exc:
        print("данных пока нет:", type(exc).__name__, str(exc)[:200])
        return
    if not rows:
        print("данных пока нет — сайт ещё не набрал показы")
        return
    print("топ запросов:")
    for r in rows:
        print("   %-44s показы %4d, клики %3d, поз. %.1f" % (
            r["keys"][0][:44], r.get("impressions", 0), r.get("clicks", 0), r.get("position", 0)))
    body["dimensions"] = ["page"]
    rows = sc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])
    print("\nтоп страниц:")
    for r in rows:
        print("   %-52s показы %4d, клики %3d" % (
            r["keys"][0].replace("https://rex.moscow/", "/")[:52],
            r.get("impressions", 0), r.get("clicks", 0)))


def main():
    args = sys.argv[1:]
    sc, sv = clients()
    if "--verify" in args:
        verify(sv, sc)
    elif "--submit" in args:
        submit(sc)
    elif "--report" in args:
        report(sc)
    else:
        status(sc)


if __name__ == "__main__":
    main()

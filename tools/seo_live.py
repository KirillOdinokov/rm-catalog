# -*- coding: utf-8 -*-
r"""Живые SEO-проверки rex.moscow: редиректы, заголовки, скорость, дубли URL.

Запуск: & $py tools\seo_live.py
Пишет data/seo_live.json
"""
import io
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "seo_live.json")
UA = "Mozilla/5.0 (compatible; RexAudit/1.0)"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


def req(url, method="GET", redirect=True, headers=None, timeout=25):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    op = urllib.request.build_opener() if redirect else urllib.request.build_opener(NoRedirect)
    t0 = time.time()
    try:
        r = op.open(urllib.request.Request(url, method=method, headers=h), timeout=timeout)
        body = r.read() if method == "GET" else b""
        return dict(status=r.status, headers=dict(r.headers), body=body,
                    ms=int((time.time() - t0) * 1000), url=r.geturl())
    except urllib.error.HTTPError as e:
        body = e.read() if method == "GET" else b""
        return dict(status=e.code, headers=dict(e.headers), body=body,
                    ms=int((time.time() - t0) * 1000), url=url)
    except Exception as e:
        return dict(status=0, error=str(e), ms=int((time.time() - t0) * 1000), url=url)


def main():
    res = {}

    # --- редиректы и дубли URL
    checks = {
        "http_root": "http://rex.moscow/",
        "http_page": "http://rex.moscow/reks-elast-100",
        "www_https": "https://www.rex.moscow/",
        "www_http": "http://www.rex.moscow/",
        "slash_page": "https://rex.moscow/reks-elast-100/",
        "slash_shop": "https://rex.moscow/shop/",
        "index_html": "https://rex.moscow/index.html",
        "upper": "https://rex.moscow/REKS-ELAST-100",
        "query": "https://rex.moscow/reks-elast-100?utm_source=test&utm_medium=cpc",
        "missing": "https://rex.moscow/net-takoy-stranicy-123",
        "sitemap": "https://rex.moscow/sitemap.xml",
        "robots": "https://rex.moscow/robots.txt",
        "favicon": "https://rex.moscow/assets/favicon.svg",
        "og_image": "https://rex.moscow/assets/og.jpg",
    }
    res["redirects"] = {}
    for k, u in checks.items():
        r = req(u, method="GET", redirect=False)
        loc = r.get("headers", {}).get("Location", "")
        res["redirects"][k] = dict(url=u, status=r["status"], location=loc,
                                   ctype=r.get("headers", {}).get("Content-Type", ""),
                                   bytes=len(r.get("body") or b""))
        print("%-10s %-3s %s -> %s" % (k, r["status"], u, loc))

    # --- заголовки и сжатие
    hdr = {}
    for enc in ("gzip", "br"):
        r = req("https://rex.moscow/", headers={"Accept-Encoding": enc})
        h = r.get("headers", {})
        hdr[enc] = dict(status=r["status"], bytes=len(r.get("body") or b""), ms=r["ms"],
                        encoding=h.get("Content-Encoding", ""), vary=h.get("Vary", ""))
    r = req("https://rex.moscow/", headers={"Accept-Encoding": "identity"})
    base = dict(status=r["status"], bytes=len(r.get("body") or b""), ms=r["ms"])
    h = r.get("headers", {})
    res["headers"] = dict(
        plain=base, gzip=hdr["gzip"], br=hdr["br"],
        server=h.get("Server", ""), hsts=h.get("Strict-Transport-Security", ""),
        ctype=h.get("Content-Type", ""), cache=h.get("Cache-Control", ""),
        xcto=h.get("X-Content-Type-Options", ""), http2=None)
    print("html: plain %d Б, gzip %d Б, br %d Б, TTFB %d мс"
          % (base["bytes"], hdr["gzip"]["bytes"], hdr["br"]["bytes"], base["ms"]))
    print("server:", h.get("Server"), "| HSTS:", bool(h.get("Strict-Transport-Security")))

    # --- HTTP/2 через curl
    for exe in ("curl.exe", "curl"):
        try:
            p = subprocess.run([exe, "-sI", "--http2", "https://rex.moscow/"],
                               capture_output=True, text=True, timeout=25)
            line = (p.stdout or "").splitlines()[0] if p.stdout else ""
            res["headers"]["http2"] = line.strip()
            print("протокол:", line.strip() or "(нет ответа)")
            break
        except Exception:
            continue

    # --- вес главной и карточки (все запросы)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            perf = {}
            for name, url in (("home", "https://rex.moscow/"),
                              ("product", "https://rex.moscow/reks-elast-100"),
                              ("category", "https://rex.moscow/gidroizolyaciya-betona")):
                ctxp = b.new_context(viewport={"width": 1440, "height": 900},
                                     ignore_https_errors=True)
                pg = ctxp.new_page()
                reqs = []
                pg.on("response", lambda r: reqs.append((r.url, r.status,
                                                         (r.headers or {}).get("content-length", ""))))
                pg.goto(url, wait_until="networkidle", timeout=60000)
                m = pg.evaluate("""() => {
                    const n = performance.getEntriesByType('navigation')[0] || {};
                    const fcp = performance.getEntriesByName('first-contentful-paint')[0];
                    const lcp = performance.getEntriesByType('largest-contentful-paint');
                    return {
                      ttfb: Math.round(n.responseStart || 0),
                      dcl: Math.round(n.domContentLoadedEventEnd || 0),
                      load: Math.round(n.loadEventEnd || 0),
                      fcp: fcp ? Math.round(fcp.startTime) : null,
                      lcp: lcp && lcp.length ? Math.round(lcp[lcp.length-1].startTime) : null,
                      dom: document.getElementsByTagName('*').length,
                      transfer: n.transferSize || 0
                    };
                }""")
                m["requests"] = len(reqs)
                perf[name] = m
                ctxp.close()
            b.close()
        res["perf"] = perf
        for k, v in perf.items():
            print("%-8s TTFB %d мс, FCP %s, LCP %s, load %d, DOM %d, запросов %d"
                  % (k, v["ttfb"], v["fcp"], v["lcp"], v["load"], v["dom"], v["requests"]))
    except Exception as e:
        res["perf"] = {"error": str(e)}
        print("playwright:", e)

    # --- robots и sitemap
    r = req("https://rex.moscow/robots.txt")
    res["robots"] = (r.get("body") or b"").decode("utf-8", "replace")
    print("--- robots.txt ---")
    print(res["robots"].strip())
    r = req("https://rex.moscow/sitemap.xml")
    body = (r.get("body") or b"").decode("utf-8", "replace")
    res["sitemap"] = dict(status=r["status"], bytes=len(body), has_lastmod="<lastmod>" in body,
                          has_priority="<priority>" in body,
                          urls=body.count("<loc>"))
    print("sitemap:", res["sitemap"])

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print("отчёт:", OUT)


if __name__ == "__main__":
    main()

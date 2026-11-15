# -*- coding: utf-8 -*-
import functools
import http.server
import os
import socketserver
import sys
import threading
import time

from playwright.sync_api import sync_playwright

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(_BASE, "dist")
OUT = os.path.join(_BASE, "shots")
os.makedirs(OUT, exist_ok=True)


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path.split("?")[0]
        fp = os.path.join(ROOT, p.lstrip("/"))
        if not os.path.exists(fp) and not os.path.isdir(fp):
            for cand in (fp + ".html", os.path.join(fp, "index.html")):
                if os.path.exists(cand):
                    self.path = cand[len(ROOT):].replace("\\", "/")
                    break
        return super().do_GET()


socketserver.TCPServer.allow_reuse_address = True
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(.4)
print("port", PORT, flush=True)

PAGES = [
    ("home", "/", 1440),
    ("shop", "/shop", 1440),
    ("cat", "/gidroizolyaciya-betona", 1440),
    ("cat2", "/gidroshponki", 1440),
    ("prod", "/reks-elast-100", 1440),
    ("prod2", "/gidroshponka-reks-p-4", 1440),
    ("art", "/adgezionnye-sostavy-most-scepleniya-betona", 1440),
    ("blog", "/blog", 1440),
    ("calcs", "/kalkulyatory", 1440),
    ("calc", "/kalkulyator-rashoda-obmazochnoj-gidroizolyacii", 1440),
    ("info", "/dostavka", 1440),
    ("kont", "/kontakty", 1440),
    ("m_home", "/", 390),
    ("m_prod", "/reks-elast-100", 390),
    ("m_cat", "/gidroizolyaciya-betona", 390),
]

only = sys.argv[1:] or None
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for name, path, w in PAGES:
        if only and name not in only:
            continue
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1)
        pg = ctx.new_page()
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        try:
            r = pg.goto("http://127.0.0.1:%d%s" % (PORT, path), wait_until="networkidle", timeout=40000)
            code = r.status if r else None
        except Exception as e:
            code = "ERR %s" % e
        pg.wait_for_timeout(300)
        try:
            pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            pg.wait_for_timeout(400)
            pg.evaluate("() => window.scrollTo(0, 0)")
            pg.wait_for_timeout(150)
        except Exception:
            pass
        pg.screenshot(path=os.path.join(OUT, name + ".png"), full_page=True)
        ow = pg.evaluate("document.documentElement.scrollWidth")
        print("%-8s %s h=%s w=%s errs=%s" % (name, code, pg.evaluate("document.body.scrollHeight"), ow, errs[:2]))
        ctx.close()
    b.close()
httpd.shutdown()

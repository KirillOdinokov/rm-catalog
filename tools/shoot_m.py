# -*- coding: utf-8 -*-
import functools
import http.server
import os
import socketserver
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
            for c in (fp + ".html", os.path.join(fp, "index.html")):
                if os.path.exists(c):
                    self.path = c[len(ROOT):].replace("\\", "/")
                    break
        return super().do_GET()


socketserver.TCPServer.allow_reuse_address = True
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(.3)

CASES = [("m_top", "/", 0), ("m_cards", "/", 1400), ("m_prod", "/reks-elast-100", 0),
         ("m_cat", "/gidroizolyaciya-betona", 0), ("m_menu", "/", -1)]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                        is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    for name, path, scroll in CASES:
        pg.goto("http://127.0.0.1:%d%s" % (PORT, path), wait_until="networkidle")
        if scroll == -1:
            pg.click("#burger")
            pg.wait_for_timeout(350)
        elif scroll:
            pg.evaluate("window.scrollTo(0, %d)" % scroll)
            pg.wait_for_timeout(350)
        pg.screenshot(path=os.path.join(OUT, name + ".png"))
        print(name, pg.evaluate("document.documentElement.scrollWidth"))
    b.close()
httpd.shutdown()

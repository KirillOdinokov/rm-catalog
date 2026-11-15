# -*- coding: utf-8 -*-
"""Локальный сервер для rex.moscow: повторяет правила nginx-конфига.

Запуск:  python serve_local.py [порт]
Отдаёт статику из E:\Design\rex\dist, повторяя:
  /<slug>            -> <slug>.html
  /<slug>/           -> 301 на /<slug>
  /product/<slug>    -> 301 на /<slug>
  /category/<slug>   -> 301 на /<slug>
  /cart-2 и прочие   -> 301
  404                -> 404.html со статусом 404
"""
import os
import posixpath
import sys
import urllib.parse

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")

REDIRECTS = {
    "/cart-2": "/", "/checkout-2": "/", "/wishlist": "/", "/my-account": "/",
    "/calculators": "/kalkulyatory",
    "/shilka-1": "/shop", "/shilka-2b": "/shop",
}

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".webp": "image/webp", ".ico": "image/x-icon",
    ".woff2": "font/woff2", ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "rex-local/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    # ------------------------------------------------------------------
    def send_file(self, rel, status=200):
        fp = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.isfile(fp):
            return self.not_found()
        ext = os.path.splitext(fp)[1].lower()
        with open(fp, "rb") as f:
            data = f.read()
        self.send_response(status)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        if ext in (".css", ".js", ".woff2", ".svg", ".png", ".jpg", ".webp"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        else:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def redirect(self, target):
        self.send_response(301)
        self.send_header("Location", target)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def not_found(self):
        return self.send_file("404.html", 404)

    # ------------------------------------------------------------------
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        raw = urllib.parse.urlparse(self.path).path
        trailing = raw.endswith("/") and raw != "/"
        path = posixpath.normpath(raw or "/")
        if path == ".":
            path = "/"
        if path.startswith("//"):
            path = path[1:]

        if path in REDIRECTS:
            return self.redirect(REDIRECTS[path])
        if path.startswith("/product/"):
            return self.redirect("/" + path[len("/product/"):].strip("/"))
        if path.startswith("/category/"):
            return self.redirect("/" + path[len("/category/"):].strip("/"))
        if path.startswith("/shop/page/"):
            return self.redirect("/shop")
        if path.startswith("/iznosostoykost-po-taberu/"):
            return self.redirect("/shop")

        if trailing:
            return self.redirect(path)

        rel = path.lstrip("/")
        if rel == "":
            return self.send_file("index.html")
        if rel.startswith("assets/"):
            return self.send_file(rel)
        if os.path.isfile(os.path.join(ROOT, rel.replace("/", os.sep))):
            return self.send_file(rel)
        if os.path.isfile(os.path.join(ROOT, rel + ".html")):
            return self.send_file(rel + ".html")
        return self.not_found()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("rex.moscow -> http://127.0.0.1:%d/" % port, flush=True)
    print("root: %s" % ROOT, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

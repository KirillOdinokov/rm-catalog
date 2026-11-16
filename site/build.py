# -*- coding: utf-8 -*-
"""Сборка rex.moscow в статику."""
import json
import os
import re
import shutil
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as C
import pages
import shell
from pages import model


def write(url, text):
    path = url.strip("/")
    fp = os.path.join(C.DIST, "index.html") if not path else os.path.join(C.DIST, path + ".html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(text)
    return fp


def redirect(url, target):
    html = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<title>Переход на новую страницу</title>'
            '<meta http-equiv="refresh" content="0;url=%s">'
            '<link rel="canonical" href="%s%s"><meta name="robots" content="noindex,follow">'
            '</head><body><p>Страница переехала: <a href="%s">%s</a></p></body></html>'
            % (target, C.SITE, target, target, target))
    write(url, html)


def copy_assets():
    dst = os.path.join(C.DIST, "assets")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    shutil.copytree(C.FONTS, os.path.join(dst, "fonts"))
    shutil.copy2(os.path.join(C.FONTS, "fonts.css"), os.path.join(dst, "fonts.css"))
    for fn in ("site.css", "site.js"):
        shutil.copy2(os.path.join(C.ASSETS, fn), os.path.join(dst, fn))
    src_img = os.path.join(C.ASSETS, "img")
    if os.path.isdir(src_img):
        shutil.copytree(src_img, os.path.join(dst, "img"))
    # фавикон
    open(os.path.join(dst, "favicon.svg"), "w", encoding="utf-8").write(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
        '<rect width="40" height="40" fill="#0088cc"/>'
        '<path d="M11 30V11h9a5.5 5.5 0 010 11h-9" fill="none" stroke="#ffffff" stroke-width="3"/>'
        '<path d="M20 22l9 8" stroke="#ffffff" stroke-width="3"/>'
        '<rect x="26" y="6" width="8" height="8" fill="#ffffff"/></svg>')
    # og-картинка и apple-touch
    make_og(os.path.join(dst, "og.jpg"))
    make_touch(os.path.join(dst, "apple-touch.png"))


def copy_root_files():
    """Файлы подтверждения прав (Google/Yandex) кладём в корень сборки как есть."""
    for fn in os.listdir(C.BASE):
        if not fn.endswith(".html"):
            continue
        if not (fn.startswith("google") or fn.startswith("yandex_")):
            continue
        shutil.copy2(os.path.join(C.BASE, fn), os.path.join(C.DIST, fn))


def make_og(path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return
    try:
        COUNT = len(json.load(open(os.path.join(C.DATA, "model.json"), encoding="utf-8"))["products"])
    except Exception:
        COUNT = 0
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (242, 248, 252))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(214, 231, 244))
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(214, 231, 244))
    d.rectangle([0, 0, 14, H], fill=(0, 136, 204))
    try:
        fb = ImageFont.truetype(r"C:\Windows\Fonts\ariblk.ttf", 132)
        fm = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 26)
        fs = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 34)
    except Exception:
        fb = fm = fs = ImageFont.load_default()
    d.text((72, 96), "РЕКС", font=fb, fill=(13, 43, 62))
    d.text((72, 262), "ИНЖЕНЕРНАЯ ХИМИЯ ДЛЯ БЕТОНА", font=fm, fill=(0, 136, 204))
    d.text((72, 330), "Гидроизоляция · Ремонт · Полы", font=fs, fill=(69, 106, 131))
    d.text((72, 380), "Защита · Клеи · Анкеровка", font=fs, fill=(69, 106, 131))
    d.text((72, 520), "%d ПОЗИЦИЙ · ДОКУМЕНТЫ НА ПАРТИЮ · ОТГРУЗКА СО СКЛАДА" % COUNT, font=fm, fill=(90, 122, 145))
    im.save(path, "JPEG", quality=88)


def make_touch(path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return
    im = Image.new("RGB", (180, 180), (0, 136, 204))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\ariblk.ttf", 96)
    except Exception:
        f = ImageFont.load_default()
    d.text((30, 34), "Р", font=f, fill=(255, 255, 255))
    d.rectangle([128, 26, 152, 50], fill=(0, 136, 204))
    im.save(path, "PNG")


def sitemap(urls, dates=None):
    dates = dates or {}
    items = []
    for u in urls:
        node = "<url><loc>%s%s</loc>" % (C.SITE, u)
        if dates.get(u):
            node += "<lastmod>%s</lastmod>" % dates[u]
        node += "<changefreq>weekly</changefreq></url>"
        items.append(node)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(items) + "</urlset>")
    open(os.path.join(C.DIST, "sitemap.xml"), "w", encoding="utf-8").write(xml)
    return len(urls)


def iso_date(s):
    """'10.09.2026' -> '2026-09-10'; уже ISO — как есть."""
    s = (s or "").strip()
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", s)
    if m:
        return "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    return ""


def search_index(m):
    rows = []
    for p in m.products:
        rows.append([p["name"], "/" + p["slug"], "Состав", p["sku"], p["price"] or 0])
    for c in m.cats:
        if m.count(c["slug"]):
            rows.append([c["name"], "/" + c["slug"], "Раздел", "", 0])
    for a in m.posts:
        rows.append([a["title"], "/" + a["slug"], "Статья", "", 0])
    for c in m.calcs:
        rows.append([c["title"], "/" + c["slug"], "Калькулятор", "", 0])
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    open(os.path.join(C.DIST, "search-index.json"), "w", encoding="utf-8").write(data)
    return len(rows)


def main():
    t0 = time.time()
    if os.path.exists(C.DIST):
        shutil.rmtree(C.DIST)
    os.makedirs(C.DIST)
    copy_assets()
    copy_root_files()
    m = model()
    urls = []
    dates = {}
    today = time.strftime("%Y-%m-%d")

    write("/", pages.home())
    urls.append("/")
    dates["/"] = today
    write("/shop", pages.catalog())
    urls.append("/shop")
    dates["/shop"] = today

    for c in m.cats:
        if not m.count(c["slug"]):
            continue
        write("/" + c["slug"], pages.category(c["slug"]))
        urls.append("/" + c["slug"])
        dates["/" + c["slug"]] = today

    for p in m.products:
        write("/" + p["slug"], pages.product(p))
        urls.append("/" + p["slug"])
        dates["/" + p["slug"]] = iso_date(p.get("price_date")) or today

    write("/blog", pages.blog_index())
    urls.append("/blog")
    dates["/blog"] = today
    for a in m.posts:
        write("/" + a["slug"], pages.article(a))
        urls.append("/" + a["slug"])
        d = pages.POST_DATES.get(a["slug"], {})
        dates["/" + a["slug"]] = d.get("modified") or d.get("published") or today

    write("/kalkulyatory", pages.calc_index())
    urls.append("/kalkulyatory")
    dates["/kalkulyatory"] = today
    for c in m.calcs:
        write("/" + c["slug"], pages.calc_page(c))
        urls.append("/" + c["slug"])
        dates["/" + c["slug"]] = today

    for slug in ("dostavka", "oplata", "sertifikaty", "podbor-analogov", "srochnaya-dostavka",
                 "vyezd-menedzhera-na-obekt"):
        write("/" + slug, pages.info(slug))
        urls.append("/" + slug)
        dates["/" + slug] = today
    write("/kontakty", pages.contacts())
    urls.append("/kontakty")
    dates["/kontakty"] = today
    write("/politika-konfidencialnosti", pages.policy())

    # 404
    open(os.path.join(C.DIST, "404.html"), "w", encoding="utf-8").write(pages.notfound())

    # старые адреса
    lines = []
    for p in m.products:
        lines.append("/product/%s /%s 301" % (p["slug"], p["slug"]))
    for c in m.cats:
        lines.append("/category/%s /%s 301" % (c["slug"], c["slug"]))
    lines += ["/cart-2 / 301", "/checkout-2 / 301", "/wishlist / 301", "/my-account / 301",
              "/calculators /kalkulyatory 301", "/calculators/ /kalkulyatory 301",
              # дубль из прайса: та же позиция, что /hacut-ochistitel
              "/hacut-ochistitel-2 /hacut-ochistitel 301"]
    os.makedirs(os.path.join(C.BASE, "dist_nginx"), exist_ok=True)
    open(os.path.join(C.BASE, "dist_nginx", "rex-redirects.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    n = sitemap(urls, dates)
    open(os.path.join(C.DIST, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\nDisallow: /search\nClean-param: utm_source&utm_medium&utm_campaign\n"
        "Sitemap: %s/sitemap.xml\n" % C.SITE)
    idx = search_index(m)

    files = sum(len(fs) for _r, _d, fs in os.walk(C.DIST))
    size = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(C.DIST) for f in fs)
    print("файлов: %d  объём: %.1f МБ" % (files, size / 1048576))
    print("страниц: %d  в sitemap: %d  поиск: %d" % (len(urls), n, idx))
    print("время: %.1f c" % (time.time() - t0))


if __name__ == "__main__":
    main()

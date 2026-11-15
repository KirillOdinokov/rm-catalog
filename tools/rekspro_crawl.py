#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""rekspro_crawl.py — сбор данных с официального сайта завода reks.pro.

Пишет в data\rekspro\:
  raw\<hash>.html      исходные страницы (для повторного разбора без сети)
  pages.jsonl          разобранные страницы: url, type, name, breadcrumbs, blocks, tables, pdf, img
  assets.jsonl         все ссылки на PDF и изображения (для скачивания)

Запуск:
  python tools\rekspro_crawl.py --limit 3          # проба
  python tools\rekspro_crawl.py                    # всё
  python tools\rekspro_crawl.py --only articles    # только статьи
"""
import argparse
import hashlib
import io
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request

socket.setdefaulttimeout(40)

BASE = "https://reks.pro"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "rekspro")
RAW = os.path.join(OUT, "raw")

HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7",
}

from bs4 import BeautifulSoup  # noqa: E402


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    import gzip
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                sys.stderr.write("FAIL %s (%s)\n" % (url, e))
                return ""
            time.sleep(1.2 * (i + 1))
    return ""


def sitemap_urls():
    xml = fetch(BASE + "/sitemap.xml")
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    # индексы sitemap
    subs = [u for u in urls if u.endswith(".xml")]
    if subs:
        out = []
        for s in subs:
            t = fetch(s)
            out += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", t)
        urls = out or urls
    clean = []
    for u in urls:
        if re.search(r"\.(jpg|jpeg|png|gif|svg|webp|pdf|zip|xml)$", u, re.I):
            continue
        clean.append(u.rstrip("/") or BASE)
    seen, res = set(), []
    for u in clean:
        if u not in seen:
            seen.add(u)
            res.append(u)
    return res


def catalog_parents(urls):
    """Все промежуточные пути под /catalog/ — это разделы, остальное — товары."""
    par = set()
    for u in urls:
        p = u[len(BASE):]
        if not p.startswith("/catalog/"):
            continue
        parts = p.strip("/").split("/")
        for i in range(1, len(parts)):
            par.add("/" + "/".join(parts[:i]))
    return par


def kind_of(url, parents=frozenset()):
    p = url[len(BASE):] or "/"
    if p.startswith("/catalog/") and p not in parents:
        return "product"
    if p.startswith("/catalog/"):
        return "category"
    if p.startswith("/articles/"):
        return "article"
    if p.startswith("/news"):
        return "news"
    if p.startswith("/tech-docs"):
        return "techdocs"
    if p.startswith("/services"):
        return "service"
    if p.startswith("/portfolio"):
        return "portfolio"
    if p.startswith("/feedback"):
        return "review"
    return "page"


def norm_text(s):
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_page(html, url, parents=frozenset()):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "svg", "iframe"]):
        t.decompose()

    data = {"url": url, "kind": kind_of(url, parents)}

    # ---- имя и хлебные крошки ----
    h1 = soup.find("h1")
    data["name"] = norm_text(h1.get_text(" ", strip=True)) if h1 else ""
    crumbs = []
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            obj = json.loads(sc.string or "")
        except Exception:
            continue
        stack = [obj]
        while stack:
            o = stack.pop()
            if isinstance(o, list):
                stack.extend(o)
                continue
            if not isinstance(o, dict):
                continue
            if o.get("@type") == "BreadcrumbList":
                for it in o.get("itemListElement", []):
                    try:
                        nm = it.get("item", {}).get("name") or it.get("name")
                        pu = it.get("item", {}).get("@id") or it.get("item", {}).get("id")
                        if nm:
                            crumbs.append([it.get("position"), nm, pu])
                    except Exception:
                        pass
            stack.extend(v for v in o.values() if isinstance(v, (dict, list)))
    crumbs.sort(key=lambda x: (x[0] is None, x[0]))
    data["breadcrumbs"] = [{"name": c[1], "url": c[2]} for c in crumbs]

    # ---- основной контейнер ----
    main = soup.find("main") or soup.find("div", class_=re.compile("content|product|detail")) or soup.body
    for t in (main.find_all(["nav", "footer", "header"]) if main else []):
        t.decompose()

    # ---- таблицы: ключ-значение и списки ----
    tables = []
    for tb in (main.find_all("table") if main else []):
        rows = []
        for tr in tb.find_all("tr"):
            cells = [norm_text(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    data["tables"] = tables

    # ---- текстовые блоки: всё до «Применение на объектах»/подвала, по заголовкам ----
    body = main or soup
    blocks = []
    cur_head, cur_lines = "", []

    def flush():
        if cur_lines:
            txt = norm_text("\n".join(cur_lines))
            if len(txt) > 25:
                blocks.append({"head": cur_head, "text": txt})

    def walk(node):
        nonlocal cur_head, cur_lines
        for el in getattr(node, "children", []):
            nm = getattr(el, "name", None)
            if nm is None:
                continue
            if nm in ("table", "script", "style"):
                continue
            if nm in ("h1", "h2", "h3", "h4", "h5"):
                flush()
                cur_lines = []
                cur_head = norm_text(el.get_text(" ", strip=True))
                continue
            if nm in ("p", "li", "div"):
                txt = norm_text(el.get_text(" ", strip=True))
                if not txt:
                    continue
                if len(txt) > 60 and el.find(["p", "li", "h2", "h3", "table"]):
                    walk(el)
                    continue
                cur_lines.append(("- " if nm == "li" else "") + txt)
                continue
            walk(el)
    walk(body)
    flush()
    # выбрасываем меню и служебное
    junk = re.compile(r"^(Главная|Каталог|Новости|О нас|Статьи|Услуги|Дилеры|Контакты|Сделано в России|"
                      r"Мы используем cookies|Обратный звонок|Поиск)", re.I)
    blocks = [b for b in blocks if not junk.match(b["text"]) and len(b["text"]) > 25]
    data["blocks"] = blocks

    # ---- PDF ----
    pdfs = []
    if main:
        for a in main.find_all("a", href=True):
            h = a["href"]
            if "/attachments/get/" in h or h.lower().endswith(".pdf"):
                full = h if h.startswith("http") else BASE + h
                pdfs.append({"url": full, "label": norm_text(a.get_text(" ", strip=True))})
    data["pdf"] = pdfs

    # ---- изображения товара ----
    imgs = []
    for a in soup.find_all(["img", "a"], href=True):
        h = a["href"]
        if "/userfls/shop/" in h:
            imgs.append(h if h.startswith("http") else BASE + h)
    for im in soup.find_all("img", src=True):
        src = im["src"]
        if "/userfls/shop/" in src or "/userfls/portfolio/" in src or "/userfls/news/" in src:
            imgs.append(src if src.startswith("http") else BASE + src)
    seen, uniq = set(), []
    for i in imgs:
        base = re.sub(r"/userfls/(shop|photo)/\w+/", "/userfls/\\1/*/", i)
        if base in seen:
            continue
        seen.add(base)
        uniq.append(i)
    data["img"] = uniq

    # ---- мета ----
    mt = soup.find("meta", attrs={"name": "description"})
    data["meta_desc"] = mt["content"].strip() if mt and mt.get("content") else ""
    ttl = soup.find("title")
    data["title"] = norm_text(ttl.get_text()) if ttl else ""
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    urls = sitemap_urls()
    parents = catalog_parents(urls)
    print("catalog sections:", len(parents))
    if a.only:
        wanted = set(x.strip() for x in a.only.split(","))
        urls = [u for u in urls if kind_of(u, parents) in wanted]
    print("urls:", len(urls))

    pj = os.path.join(OUT, "pages.jsonl")
    done = set()
    if os.path.exists(pj) and not a.force:
        with open(pj, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["url"])
                except Exception:
                    pass
        print("already:", len(done))

    todo = [u for u in urls if u not in done]
    if a.limit:
        todo = todo[:a.limit]

    fo = open(pj, "a", encoding="utf-8")
    n = 0
    for u in todo:
        html = fetch(u)
        if not html:
            continue
        h = hashlib.md5(u.encode()).hexdigest()[:12]
        with open(os.path.join(RAW, h + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
        try:
            rec = parse_page(html, u, parents)
        except Exception as e:
            sys.stderr.write("PARSE %s %s\n" % (u, e))
            continue
        rec["raw"] = h
        fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fo.flush()
        n += 1
        if n % 10 == 0:
            print("  ", n, "/", len(todo), rec["kind"], rec["name"][:50])
        time.sleep(0.25)
    fo.close()
    print("saved", n, "->", pj)


if __name__ == "__main__":
    main()

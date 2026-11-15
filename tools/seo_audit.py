# -*- coding: utf-8 -*-
r"""SEO-аудит собранного сайта (dist): метаданные, структура, дубли, разметка.

Пишет data/seo_audit.json и сводку в консоль.
Запуск: & $py tools\seo_audit.py
"""
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

from lxml import html as LH

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(BASE, "dist")
OUT = os.path.join(BASE, "data", "seo_audit.json")


def text_of(el):
    if el is None:
        return ""
    return re.sub(r"\s+", " ", el.text_content()).strip()


def norm_url(path):
    p = path.replace(os.sep, "/")
    p = p[len(DIST):].lstrip("/")
    if p in ("index.html", ""):
        return "/"
    if p.endswith("/index.html"):
        return "/" + p[: -len("/index.html")]
    if p.endswith(".html"):
        p = p[:-5]
    return "/" + p


def main():
    model = json.load(io.open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
    PRODS = set("/" + p["slug"] for p in model["products"])
    ARTICLES = set("/" + p["slug"] for p in model["posts"])
    CATS = set("/" + c["slug"] for c in model["cats"])
    CALCS = set("/" + c["slug"] for c in model["calcs"])

    def kind_of(url):
        return ("home" if url == "/" else "shop" if url == "/shop" else
                "blog" if url == "/blog" else "calcs" if url == "/kalkulyatory" else
                "404" if url == "/404" else "article" if url in ARTICLES else
                "calc" if url in CALCS else "cat" if url in CATS else
                "prod" if url in PRODS else "info")

    pages = {}
    titles = defaultdict(list)
    descs = defaultdict(list)
    h1s = defaultdict(list)
    images_noalt = []
    images_no_size = []
    noindex = []
    thin = []
    jsonld = Counter()

    for root, dirs, files in os.walk(DIST):
        for f in files:
            if not f.endswith(".html"):
                continue
            fp = os.path.join(root, f)
            url = norm_url(fp)
            raw = io.open(fp, encoding="utf-8").read()
            try:
                doc = LH.fromstring(raw)
            except Exception as e:
                print("! parse", url, e)
                continue
            head = doc.head
            get = lambda xp: head.xpath(xp)
            title = text_of(get("//title")[0]) if get("//title") else ""
            md = get('//meta[@name="description"]/@content')
            desc = md[0].strip() if md else ""
            can = get('//link[@rel="canonical"]/@href')
            canonical = can[0] if can else ""
            rob = get('//meta[@name="robots"]/@content')
            robots = rob[0] if rob else ""
            og = {k: (get('//meta[@property="og:%s"]/@content' % k) or [""])[0]
                  for k in ("title", "description", "image", "url", "type")}
            h1 = [text_of(x) for x in doc.xpath("//h1")]
            h2n = len(doc.xpath("//h2"))
            body_text = text_of(doc.body)
            words = len(re.findall(r"[А-Яа-яA-Za-z]{2,}", body_text))
            imgs = doc.xpath("//img")
            for im in imgs:
                src = im.get("src") or ""
                if not (im.get("alt") or "").strip():
                    images_noalt.append((url, src))
                if not (im.get("width") and im.get("height")):
                    images_no_size.append((url, src))
            links = doc.xpath("//a[@href]")
            internal = [a.get("href") for a in links
                        if (a.get("href") or "").startswith("/")]
            ext = [a.get("href") for a in links
                   if (a.get("href") or "").startswith("http")]
            lds = doc.xpath('//script[@type="application/ld+json"]')
            for ld in lds:
                try:
                    data = json.loads(ld.text or "{}")
                except Exception:
                    data = {}
                nodes = data.get("@graph") if isinstance(data, dict) else None
                if not nodes:
                    nodes = [data]
                for node in nodes:
                    t = node.get("@type") if isinstance(node, dict) else ""
                    if isinstance(t, list):
                        for x in t:
                            jsonld[x] += 1
                    elif t:
                        jsonld[t] += 1
            pages[url] = dict(
                title=title, title_len=len(title), desc=desc, desc_len=len(desc),
                canonical=canonical, robots=robots, h1=h1, h1n=len(h1), h2=h2n,
                words=words, imgs=len(imgs), links=len(internal), ext_links=len(ext),
                jsonld=len(lds), og=og, og_ok=all(og.values()), kind=kind_of(url))
            titles[title].append(url)
            descs[desc].append(url)
            if h1:
                h1s[h1[0]].append(url)
            if "noindex" in robots:
                noindex.append(url)
            if words < 300:
                thin.append((url, words))

    # ---- источники истины для классификации
    for u, p in pages.items():
        p["kind"] = kind_of(u)

    # ---- дубли и длины
    dup_titles = {t: v for t, v in titles.items() if len(v) > 1 and t}
    dup_descs = {d: v for d, v in descs.items() if len(v) > 1 and d}
    dup_h1 = {h: v for h, v in h1s.items() if len(v) > 1}
    long_titles = [(u, p["title_len"], p["title"]) for u, p in pages.items() if p["title_len"] > 70]
    short_titles = [(u, p["title_len"]) for u, p in pages.items() if p["title_len"] < 30]
    long_descs = [(u, p["desc_len"]) for u, p in pages.items() if p["desc_len"] > 180]
    short_descs = [(u, p["desc_len"]) for u, p in pages.items() if 0 < p["desc_len"] < 70]
    no_desc = [u for u, p in pages.items() if not p["desc"]]
    bad_h1 = [(u, p["h1n"]) for u, p in pages.items() if p["h1n"] != 1]
    bad_canon = [(u, p["canonical"]) for u, p in pages.items()
                 if p["canonical"].rstrip("/") != ("https://rex.moscow" + u).rstrip("/")]
    no_og = [u for u, p in pages.items() if not p["og_ok"]]
    no_ld = [u for u, p in pages.items() if p["jsonld"] == 0]

    # ---- sitemap
    sm = io.open(os.path.join(DIST, "sitemap.xml"), encoding="utf-8").read()
    sm_urls = set(x.replace("https://rex.moscow", "") or "/"
                  for x in re.findall(r"<loc>([^<]+)</loc>", sm))
    sm_missing = sorted(u for u in pages if u not in sm_urls and u != "/404")
    sm_extra = sorted(u for u in sm_urls if u not in pages)

    # ---- похожесть текстов товаров (шаблонные описания)
    def shingles(s, n=6):
        w = re.findall(r"[а-яёa-z]+", s.lower())
        return set(" ".join(w[i:i + n]) for i in range(max(0, len(w) - n)))

    prod_pages = [u for u, p in pages.items() if p["kind"] == "prod"]
    texts = {}
    for u in prod_pages:
        fp = os.path.join(DIST, u.strip("/") + ".html")
        if not os.path.exists(fp):
            continue
        d = LH.fromstring(io.open(fp, encoding="utf-8").read())
        texts[u] = shingles(text_of(d.xpath('//div[contains(@class,"prose")]')[0]
                                    if d.xpath('//div[contains(@class,"prose")]') else d.body))
    import itertools
    sims = []
    lst = sorted(texts)
    for a, b in itertools.combinations(lst, 2):
        sa, sb = texts[a], texts[b]
        if not sa or not sb:
            continue
        j = len(sa & sb) / float(len(sa | sb))
        sims.append(j)
    sims.sort()
    avg_sim = sum(sims) / len(sims) if sims else 0
    high_sim = sum(1 for x in sims if x > 0.5)

    data = dict(
        pages=pages,
        total=len(pages),
        dup_titles={k: v for k, v in list(dup_titles.items())[:20]},
        dup_titles_n=len(dup_titles),
        dup_descs={k: v for k, v in list(dup_descs.items())[:20]},
        dup_descs_n=len(dup_descs),
        dup_h1={k: v for k, v in list(dup_h1.items())[:20]},
        dup_h1_n=len(dup_h1),
        long_titles=sorted(long_titles, key=lambda x: -x[1])[:25],
        long_titles_n=len(long_titles),
        short_titles_n=len(short_titles),
        long_descs_n=len(long_descs),
        short_descs_n=len(short_descs),
        no_desc=no_desc,
        bad_h1=bad_h1,
        bad_canon=bad_canon[:20],
        bad_canon_n=len(bad_canon),
        no_og=no_og,
        no_ld_n=len(no_ld),
        jsonld=dict(jsonld),
        noindex=noindex,
        thin=sorted(thin, key=lambda x: x[1])[:20],
        thin_n=len(thin),
        images_noalt_n=len(images_noalt),
        images_noalt=images_noalt[:15],
        images_no_size_n=len(images_no_size),
        sm_urls_n=len(sm_urls),
        sm_missing=sm_missing,
        sm_extra=sm_extra,
        prod_sim_avg=round(avg_sim, 3),
        prod_sim_high=high_sim,
        prod_sim_pairs=len(sims),
    )
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))

    print("страниц: %d" % len(pages))
    print("дубли title: %d, description: %d, h1: %d" % (len(dup_titles), len(dup_descs), len(dup_h1)))
    print("title >70: %d, <30: %d | desc >180: %d, <70: %d, пустых: %d"
          % (len(long_titles), len(short_titles), len(long_descs), len(short_descs), len(no_desc)))
    print("h1 != 1: %d | canonical неверный: %d | без og: %d | без JSON-LD: %d"
          % (len(bad_h1), len(bad_canon), len(no_og), len(no_ld)))
    print("JSON-LD по типам:", dict(jsonld))
    print("noindex: %d %s" % (len(noindex), noindex[:5]))
    print("тонких страниц (<300 слов): %d" % len(thin))
    print("img без alt: %d | без width/height: %d" % (len(images_noalt), len(images_no_size)))
    print("sitemap: %d URL, нет в карте: %d, лишних: %d" % (len(sm_urls), len(sm_missing), len(sm_extra)))
    print("похожесть текстов товаров: средняя %.2f, пар >0.5: %d из %d"
          % (avg_sim, high_sim, len(sims)))
    print("отчёт:", OUT)


PRODS = ARTICLES = CATS = CALCS = set()
if __name__ == "__main__":
    main()

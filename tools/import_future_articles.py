# -*- coding: utf-8 -*-
"""Импорт пакета статей articles-future в модель сайта.

Пакет: `articles-future/metadata.csv` + `articles-future/content/*.html` (тексты под
другой бренд: инлайн-стили, красный #d60b0b, CTA-блок, заглушки картинок, пустые списки).

Что делает скрипт:
1. Чистит разметку: убирает обёртку `enix-article`, CTA-блок, заглушки-картинки,
   пустые списки и заголовки без содержимого, инлайн-стили и классы.
2. Блок «Короткий ответ» превращает в `<div class="note">`.
3. Строит оглавление (`<div class="toc">`) и проставляет заголовкам читаемые id.
4. Перебрендирует `meta_title` / `meta_description` (убирает «ЕНИКС»).
5. Кладёт тело статьи в `content/articles/<slug>.html`, обложку — в `assets/img/a/`.
6. Распределяет даты публикации: `--start` + `--per-day`, кластеры вперемешку,
   внутри — по `rex_score`.

Запуск:
    & $py13 tools\\import_future_articles.py --dry                  # отчёт без записи
    & $py13 tools\\import_future_articles.py --start 2026-11-16 --per-day 2
    & $py13 tools\\import_future_articles.py --limit 3 --start 2026-11-15 --today
"""
import csv
import json
import os
import re
import sys
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUT = os.path.join(BASE, "articles-future")
CONTENT_DIR = os.path.join(BASE, "content", "articles")
IMG_DIR = os.path.join(BASE, "assets", "img", "a")
MODEL = os.path.join(BASE, "data", "model.json")
IMAGES = os.path.join(BASE, "data", "images.json")
DATES = os.path.join(BASE, "data", "post_dates.json")

CATEGORY = {
    "hydro": "gidroizolyaciya",
    "repair": "remont-betona",
    "floors": "promyshlennye-poly",
    "protection": "zashhita-betona",
    "anchor": "kleevye-ankernye-sistemy",
    "adhesive": "kleevye-ankernye-sistemy",
}
CAT_RU = {
    "gidroizolyaciya": "Гидроизоляция",
    "remont-betona": "Ремонт бетона",
    "promyshlennye-poly": "Промышленные полы",
    "zashhita-betona": "Защита бетона",
    "kleevye-ankernye-sistemy": "Крепёж и клеевые системы",
}
TRANS = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "j", "k", "l", "m", "n", "o", "p",
     "r", "s", "t", "u", "f", "h", "c", "ch", "sh", "shh", "", "y", "", "e", "yu", "ya"]))
PREPS = ("на", "по", "для", "и", "в", "с", "от", "до", "из", "о", "об", "при", "как",
         "что", "или", "а", "за", "под", "над", "про", "через", "ли", "не", "же")


# --------------------------------------------------------------------- разметка
def block_end(html, start, tag):
    depth = 0
    for m in re.finditer(r"<(/?)%s\b[^>]*>" % tag, html[start:]):
        if m.group(1) == "":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return start + m.end()
    return -1


def drop_blocks(html, tag, marker):
    pos = 0
    while True:
        i = html.find("<" + tag, pos)
        if i < 0:
            return html
        end = block_end(html, i, tag)
        if end < 0:
            return html
        if marker in html[i:end]:
            html = html[:i] + html[end:]
            pos = i
        else:
            pos = end


def unwrap(html):
    m = re.search(r'<div class="enix-article">', html)
    if not m:
        return html
    end = block_end(html, m.start(), "div")
    if end < 0:
        return html
    return html[:m.start()] + html[m.end():end - len("</div>")] + html[end:]


def callout_to_note(html):
    i = html.find("<div")
    while i >= 0:
        end = block_end(html, i, "div")
        if end < 0:
            return html
        if "Короткий ответ" in html[i:end]:
            inner = html[html.find(">", i) + 1:end - len("</div>")]
            return html[:i] + '<div class="note">' + inner + "</div>" + html[end:]
        i = html.find("<div", end)
    return html


def make_id(text, used):
    s = "".join(TRANS.get(ch, ch) for ch in text.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > 46:  # не обрываем слово посередине
        s = s[:46]
        s = s[:s.rfind("-")] if "-" in s else s
    s = s.strip("-") or "razdel"
    base, n = s, 2
    while s in used:
        s = "%s-%d" % (base, n)
        n += 1
    used.add(s)
    return s


def add_toc(html):
    used, items = set(), []

    def repl(m):
        attrs, body = m.group(1), m.group(2)
        if "id=" in attrs:
            return m.group(0)
        text = re.sub(r"<[^>]+>", "", body).strip()
        hid = make_id(text, used)
        items.append((hid, text))
        return '<h2 id="%s"%s>%s</h2>' % (hid, attrs, body)

    html = re.sub(r"<h2([^>]*)>(.*?)</h2>", repl, html, flags=re.S)
    if len(items) < 3:
        return html
    toc = ('<div class="toc"><h2 id="soderzhanie">Содержание</h2><ol>%s</ol></div>'
           % "".join('<li><a href="#%s">%s</a></li>' % (h, t) for h, t in items))
    i = html.find("<h2")
    return html[:i] + toc + html[i:]


def dedupe_sections(html):
    """В части статей пакета один и тот же план продублирован (два варианта текста).

    Оставляем самый подробный блок по каждому заголовку, остальные выкидываем —
    иначе в оглавлении два одинаковых пункта, а в тексте два похожих раздела.
    """
    parts = re.split(r"(?=<h2)", html)
    head = "" if parts and parts[0].lstrip().startswith("<h2") else parts[0]
    segs = [p for p in parts if p.lstrip().startswith("<h2")]
    if len(segs) < 3:
        return html
    by_title = {}
    for i, seg in enumerate(segs):
        m = re.match(r"<h2[^>]*>(.*?)</h2>", seg, re.S)
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip().lower()
        by_title.setdefault(title, []).append(i)
    keep = set(range(len(segs)))
    for idxs in by_title.values():
        if len(idxs) > 1:
            best = max(idxs, key=lambda i: len(plain(segs[i])))
            for i in idxs:
                if i != best:
                    keep.discard(i)
    return head + "".join(segs[i] for i in sorted(keep))


def clean(html):
    html = unwrap(html)
    html = drop_blocks(html, "div", "Нужна консультация?")
    html = drop_blocks(html, "figure", "[ изображение")
    # в исходнике встречается style="font-family:"Roboto Condensed",…" — кавычка рвёт атрибут,
    # поэтому режем от style=" до конца тега, а не до кавычки
    html = re.sub(r'\s+style="[^>]*>', ">", html)
    html = re.sub(r"\s+style='[^>]*>", ">", html)
    html = re.sub(r'\s+class="[^"]*"', "", html)
    html = callout_to_note(html)
    # заголовки с пустым списком и просто пустые списки
    html = re.sub(r"<h2[^>]*>[^<]*</h2>\s*<(?:ol|ul)>\s*</(?:ol|ul)>", "", html)
    html = re.sub(r"<(ol|ul)>\s*</\1>", "", html)
    html = re.sub(r"<p>\s*</p>", "", html)
    html = html.replace('href="/kalkulyatory/"', 'href="/kalkulyatory"')
    html = re.sub(r'href="(/[^"#?]*?)/"', r'href="\1"', html)
    html = dedupe_sections(html)
    html = add_toc(html)
    html = re.sub(r"[ \t]+\n", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html).strip()
    return html


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


# --------------------------------------------------------------------- метаданные
def rebrand(s):
    s = (s or "").replace("— ЕНИКС", "").replace("ЕНИКС", "").replace("еникс", "")
    s = re.sub(r"\s+", " ", s).strip(" .,;:—-")
    # после удаления бренда остаются обрубки вида «… под ваш объект. Разбор от»
    s = re.sub(r"(?:^|[.!?]\s*)(?:Разбор|Ответ|Материал|Статья|Обзор)\s+от\s*$", "", s).strip()
    s = re.sub(r"\s+(?:от|для|по|на)$", "", s).strip(" .,;:—-")
    if s and s[-1] not in ".!?":
        s += "."
    return s


def short_title(title, limit=60):
    """Короткий title: режем по естественной границе (двоеточие, тире, скобка)."""
    t = re.sub(r"\s+", " ", (title or "").strip())
    if len(t) <= limit:
        return t + " | РЕКС"
    for sep in (":", " — ", " – ", " ("):
        i = t.find(sep)
        if 24 <= i <= limit:
            return t[:i].rstrip(" ,;:—–-") + " | РЕКС"
    cut = t[:limit].rsplit(" ", 1)[0]
    words = cut.split()
    while words and words[-1].lower() in PREPS:
        words.pop()
    return " ".join(words).rstrip(" ,;:—-") + "… | РЕКС"


# --------------------------------------------------------------------- обложки
def render_covers(rows, generated):
    """Обложки WebP 760×428 в стиле сайта (нужны Pillow и fontTools, python 3.13)."""
    from fontTools.merge import Merger
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from PIL import Image, ImageDraw, ImageFont

    cache = r"E:\temp\rex-fonts"
    os.makedirs(cache, exist_ok=True)

    def prep(name, wght=None):
        out = os.path.join(cache, os.path.basename(name).replace(".woff2", ".ttf"))
        if not os.path.exists(out):
            f = TTFont(os.path.join(BASE, "assets", "fonts", name))
            f.flavor = None
            if wght and "fvar" in f:
                f = instantiateVariableFont(f, {"wght": wght}, updateFontNames=True)
            f.save(out)
        return out

    def merged(cyr, lat, out_name, wght=None):
        out = os.path.join(cache, out_name)
        if not os.path.exists(out):
            Merger().merge([prep(cyr, wght), prep(lat, wght)]).save(out)
        return out

    geo = merged("geologica-600-cyrillic.woff2", "geologica-600-latin.woff2", "geo600.ttf", 600)
    plex = merged("plex-500-cyrillic.woff2", "plex-500-latin.woff2", "plex500.ttf")

    W, H = 760, 428
    PAPER, GRID, LINE, ACC, INK, MUTED = "#f2f8fc", "#e9f4fb", "#a9c9e0", "#0088cc", "#0d2b3e", "#5a7a91"
    f_mono = ImageFont.truetype(plex, 13)
    f_title = ImageFont.truetype(geo, 33)
    f_cat = ImageFont.truetype(plex, 14)
    os.makedirs(IMG_DIR, exist_ok=True)

    for r in rows:
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        for x in range(0, W, 38):
            d.line([(x, 0), (x, H)], fill=GRID)
        for y in range(0, H, 38):
            d.line([(0, y), (W, y)], fill=GRID)
        d.rectangle([0, 0, W - 1, H - 1], outline=LINE)
        d.rectangle([0, 0, 7, H], fill=ACC)
        d.text((52, 28), "ПОМОЩЬ ПРОЕКТИРОВЩИКУ И СТРОИТЕЛЮ", font=f_mono, fill=MUTED)

        words, lines, cur = r["title"].split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f_title) <= W - 112:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        y = 108 if len(lines) < 3 else 84
        for ln in lines[:4]:
            d.text((52, y), ln, font=f_title, fill=INK)
            y += 41

        d.line([(52, H - 74), (W - 52, H - 74)], fill=LINE)
        d.text((52, H - 56), CAT_RU[CATEGORY[r["rex_category"]]].upper(), font=f_cat, fill="#456a83")
        right = "РЕКС · 2026"
        d.text((W - 52 - d.textlength(right, font=f_mono), H - 55), right, font=f_mono, fill=MUTED)

        path = os.path.join(IMG_DIR, r["slug"] + ".webp")
        img.save(path, "WEBP", quality=72, method=6)
        generated[r["slug"]] = {"file": "a/%s.webp" % r["slug"], "bytes": os.path.getsize(path)}


# --------------------------------------------------------------------- планировщик
def schedule(rows, start, per_day):
    """Даты публикации: кластеры вперемешку, внутри кластера — по убыванию rex_score."""
    groups = {}
    for r in rows:
        groups.setdefault(r["rex_category"], []).append(r)
    for v in groups.values():
        v.sort(key=lambda r: -float(r["rex_score"]))
    order, keys = [], sorted(groups, key=lambda k: -max(float(r["rex_score"]) for r in groups[k]))
    while any(groups[k] for k in keys):
        for k in keys:
            if groups[k]:
                order.append(groups[k].pop(0))
    for i, r in enumerate(order):
        r["publish_at"] = (start + timedelta(days=i // per_day)).isoformat()
    return order


# --------------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    covers = "--covers" in args  # по умолчанию обложки не генерируем: карточки рисуют «пластину»

    def opt(name, default):
        if name in args:
            return args[args.index(name) + 1]
        return default

    start = date.fromisoformat(opt("--start", (date.today() + timedelta(days=1)).isoformat()))
    per_day = int(opt("--per-day", "2"))
    limit = int(opt("--limit", "0"))
    today = "--today" in args

    rows = list(csv.DictReader(open(os.path.join(FUT, "metadata.csv"), encoding="utf-8-sig")))
    rows = schedule(rows, start, per_day)
    if limit:
        rows = rows[:limit]
    if today:
        for r in rows:
            r["publish_at"] = date.today().isoformat()

    model = json.load(open(MODEL, encoding="utf-8"))
    known = {p["slug"] for p in model["posts"]}
    rows = [r for r in rows if r["slug"] not in known]

    images = json.load(open(IMAGES, encoding="utf-8"))
    dates = json.load(open(DATES, encoding="utf-8"))
    gen = {}
    if covers:
        try:
            render_covers(rows, gen)
        except ImportError:
            print("! нет Pillow/fontTools — обложки не делаю (запускать python 3.13)")

    for r in rows:
        html = clean(open(os.path.join(FUT, r["file"]), encoding="utf-8").read())
        r["html"] = html
        r["len"] = len(plain(html))

    print("статей к импорту: %d" % len(rows))
    if limit or dry:
        for r in rows[:5]:
            print("  %s  %s  %d симв.  %s" % (r["publish_at"], r["slug"][:40], r["len"], r["title"][:60]))
    days = sorted({r["publish_at"] for r in rows})
    if days:
        print("дат: %d, первая %s, последняя %s, в день %.1f" % (
            len(days), days[0], days[-1], len(rows) / float(len(days))))
    if dry:
        print("--dry: ничего не записано")
        return

    os.makedirs(CONTENT_DIR, exist_ok=True)
    added = 0
    for r in rows:
        with open(os.path.join(CONTENT_DIR, r["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(r["html"])
        model["posts"].append({
            "title": r["title"],
            "slug": r["slug"],
            "category": CATEGORY[r["rex_category"]],
            "meta_title": short_title(r["title"]),
            "meta_desc": rebrand(r["meta_description"]),
            "content_len": r["len"],
            "publish_at": r["publish_at"],
            "file": "articles/%s.html" % r["slug"],
        })
        dates[r["slug"]] = {"published": r["publish_at"]}
        added += 1

    images["articles"].update(gen)
    json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(images, open(IMAGES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(dates, open(DATES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("импортировано: %d, обложек: %d" % (added, len(gen)))


if __name__ == "__main__":
    main()

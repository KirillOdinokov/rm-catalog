# -*- coding: utf-8 -*-
r"""Неопубликованные статьи из дампа БД rex.moscow -> папка unpublished/.

Берём записи post_type = post/page со статусом draft, pending, future, private
(trash, auto-draft, inherit пропускаем). Пишем:
    unpublished\index.csv      — таблица для планирования публикаций
    unpublished\README.md      — отчёт по дампу + порядок работы
    unpublished\<NN>-<slug>.md — текст материала с front matter
"""
import csv
import io
import json
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL = os.path.join(BASE, "data", "_db", "rex.sql")
OUT = os.path.join(BASE, "unpublished")
KEEP = ("draft", "pending", "future", "private")

sql = io.open(SQL, encoding="utf-8", errors="replace").read()


def table_rows(name):
    """Все строки таблицы rex_<name> (учитываем несколько INSERT-ов)."""
    rows = []
    for m in re.finditer(r"INSERT INTO `rex_%s` VALUES (.*?);\n" % re.escape(name), sql, re.S):
        body = m.group(1)
        row, i, n = [], 0, len(body)
        while i < n:
            c = body[i]
            if c == "(":
                row = []
                i += 1
                while i < n:
                    while body[i] in " ,":
                        i += 1
                    if body[i] == ")":
                        rows.append(row)
                        i += 1
                        break
                    if body[i] == "'":
                        i += 1
                        buf = []
                        while i < n:
                            ch = body[i]
                            if ch == "\\":
                                nxt = body[i + 1]
                                buf.append({"n": "\n", "r": "\r", "t": "\t", "0": "\0"}.get(nxt, nxt))
                                i += 2
                            elif ch == "'":
                                if i + 1 < n and body[i + 1] == "'":
                                    buf.append("'")
                                    i += 2
                                else:
                                    i += 1
                                    break
                            else:
                                buf.append(ch)
                                i += 1
                        row.append("".join(buf))
                    else:
                        start = i
                        while i < n and body[i] not in ",)":
                            i += 1
                        tok = body[start:i].strip()
                        row.append(None if tok.upper() == "NULL" else tok)
            else:
                i += 1
    return rows


def strip_blocks(html):
    """Убрать блоки Gutenberg, style/script, лишние обёртки."""
    html = re.sub(r"<!--\s*/?wp:.*?-->", "", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    html = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    html = re.sub(r"\[/?vc_[^\]]*\]", "", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def to_md(html):
    """Очень простой HTML -> Markdown: заголовки, списки, жирный, ссылки, таблицы."""
    s = strip_blocks(html)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>",
               lambda m: "\n\n%s %s\n" % ("#" * int(m.group(1)), _inline(m.group(2))), s, flags=re.S | re.I)
    s = re.sub(r"<li[^>]*>(.*?)</li>", lambda m: "\n- " + _inline(m.group(1)), s, flags=re.S | re.I)
    s = re.sub(r"</?(ul|ol)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"</?blockquote[^>]*>", "\n\n> ", s, flags=re.I)
    s = re.sub(r"<p[^>]*>(.*?)</p>", lambda m: "\n\n" + _inline(m.group(1)), s, flags=re.S | re.I)
    s = re.sub(r"<table[^>]*>", "\n\n", s, flags=re.I)
    s = re.sub(r"<tr[^>]*>", "\n| ", s, flags=re.I)
    s = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", s, flags=re.I)
    s = re.sub(r"</tr>", " |", s, flags=re.I)
    s = re.sub(r"</?(thead|tbody|tfoot|colgroup|caption)[^>]*>", "", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = _entities(s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _inline(x):
    x = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", x, flags=re.S | re.I)
    x = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", x, flags=re.S | re.I)
    x = re.sub(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", x, flags=re.S | re.I)
    x = re.sub(r"<code>(.*?)</code>", r"`\1`", x, flags=re.S | re.I)
    x = re.sub(r"<[^>]+>", "", x)
    return _entities(x).strip()


def _entities(s):
    for a, b in (("&nbsp;", " "), ("&#8212;", "—"), ("&#8211;", "–"), ("&laquo;", "«"),
                 ("&raquo;", "»"), ("&quot;", '"'), ("&#039;", "'"), ("&amp;", "&"),
                 ("&lt;", "<"), ("&gt;", ">"), ("&#8217;", "’"), ("&mdash;", "—"),
                 ("&ndash;", "–"), ("&hellip;", "…")):
        s = s.replace(a, b)
    return s


def main():
    posts = table_rows("posts")
    meta = table_rows("postmeta")
    by_post = defaultdict(dict)
    for r in meta:
        if len(r) >= 4:
            by_post[int(r[1])][r[2]] = r[3]
    att = {}
    for r in posts:
        if len(r) >= 21 and r[20] == "attachment":
            att[int(r[0])] = r[18] or ""

    picked = []
    stats = defaultdict(int)
    articles = []
    for r in posts:
        if len(r) < 21:
            continue
        ptype, status = r[20], r[7]
        stats[(ptype, status)] += 1
        if ptype == "post":
            articles.append((r[11], status, r[5] or ""))
        if ptype not in ("post", "page") or status not in KEEP:
            continue
        pid = int(r[0])
        m = by_post.get(pid, {})
        thumb = m.get("_thumbnail_id") or ""
        cover = att.get(int(thumb)) if thumb.isdigit() else ""
        picked.append(dict(
            id=pid, type=ptype, status=status, date=r[2] or "", date_gmt=r[3] or "",
            title=(r[5] or "").strip() or "(без заголовка)", slug=r[11] or ("post-%d" % pid),
            content=r[4] or "", excerpt=r[6] or "", modified=r[14] or "",
            author=r[1], cover=cover,
            meta_title=m.get("_yoast_wpseo_title") or "",
            meta_desc=m.get("_yoast_wpseo_metadesc") or "",
            focus_kw=m.get("_yoast_wpseo_focuskw") or ""))

    picked.sort(key=lambda p: (p["date"], p["id"]))
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".md") or f.endswith(".csv"):
            os.remove(os.path.join(OUT, f))

    rows = []
    for i, p in enumerate(picked, 1):
        body = to_md(p["content"])
        fname = "%02d-%s.md" % (i, re.sub(r"[^a-z0-9\-]+", "-", p["slug"].lower())[:60] or ("post-%d" % p["id"]))
        head = [
            "---",
            'id: %d' % p["id"],
            'title: "%s"' % p["title"].replace('"', "'"),
            'slug: "%s"' % p["slug"],
            'status: "%s"' % p["status"],
            'type: "%s"' % p["type"],
            'date: "%s"' % p["date"],
            'date_gmt: "%s"' % p["date_gmt"],
            'modified: "%s"' % p["modified"],
            'chars: %d' % len(body),
        ]
        if p["meta_title"]:
            head.append('meta_title: "%s"' % p["meta_title"].replace('"', "'"))
        if p["meta_desc"]:
            head.append('meta_desc: "%s"' % p["meta_desc"].replace('"', "'"))
        if p["focus_kw"]:
            head.append('focus_keyword: "%s"' % p["focus_kw"].replace('"', "'"))
        if p["cover"]:
            head.append('cover: "%s"' % p["cover"])
        head += ["---", "", "# %s" % p["title"], ""]
        io.open(os.path.join(OUT, fname), "w", encoding="utf-8").write("\n".join(head) + body + "\n")
        rows.append([i, p["id"], p["status"], p["date"], p["date_gmt"], p["title"], p["slug"],
                     len(body), fname])

    with io.open(os.path.join(OUT, "index.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["#", "id", "status", "date", "date_gmt", "title", "slug", "chars", "file"])
        w.writerows(rows)

    label = {"draft": "черновик", "pending": "на проверке", "future": "запланирована",
             "private": "приватная"}
    # сколько статей из дампа уже стоит на сайте
    model_path = os.path.join(BASE, "data", "model.json")
    on_site, missing = set(), []
    if os.path.exists(model_path):
        model = json.load(io.open(model_path, encoding="utf-8"))
        on_site = set(p["slug"] for p in model.get("posts", []))
        missing = [a for a in articles if a[0] not in on_site]
    pub = sum(1 for a in articles if a[1] == "publish")
    lines = ["# Неопубликованные материалы сайта rex.moscow", "",
             "Выгружено из дампа БД `D:\\Old Sites\\rex.moscow\\MySQL\\odinoknx_rex.sql.gz`",
             "(таблица `rex_posts`). Попадают только записи, которые не были опубликованы:",
             "`draft`, `pending`, `future`, `private`. Служебные `trash`, `auto-draft`, `inherit`",
             "и вложения пропущены.", "",
             "## Результат проверки дампа", "",
             "| что проверяли | результат |", "|---|---|",
             "| всего записей в `rex_posts` | %d |" % len(posts),
             "| статей (`post`) | %d, из них опубликовано %d |" % (len(articles), pub),
             "| статей **не** опубликовано | %d |" % sum(1 for a in articles if a[1] != "publish"),
             "| статей из дампа нет на сайте | %d |" % len(missing),
             "| неопубликованных страниц/записей в выгрузке | %d |" % len(picked), ""]
    if articles and not missing and pub == len(articles):
        lines += ["> В этом бэкапе неопубликованных статей нет: все %d статей в статусе "
                  "`publish`, и все они уже перенесены в `data/model.json` → `posts[]` "
                  "(сверка по слагам)." % len(articles), ""]
    if not picked:
        lines += ["Папка пустая по существу: переносить нечего.", ""]
    lines += ["Всего в выгрузке: **%d** материалов (%s)." % (
        len(picked),
        ", ".join("%s — %d" % (label[s], sum(1 for p in picked if p["status"] == s))
                  for s in ("draft", "pending", "future", "private")
                  if any(p["status"] == s for p in picked)) or "нет"),
        "",
        "| # | статус | дата | знаков | заголовок | файл |",
        "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %d | %s | %s | %d | %s | `%s` |" % (
            r[0], label.get(r[2], r[2]), (r[3] or "")[:10], r[7],
            r[5].replace("|", "\\|"), r[8]))
    lines += ["", "## Что это за статусы", "",
              "- **запланирована (`future`)** — материал уже написан, но дата публикации ещё",
              "  не наступила. Именно такие записи проще всего вернуть в отложенную публикацию.",
              "- **черновик (`draft`)** — текст не дописан или не проверен.",
              "- **на проверке (`pending`)** — ждёт подтверждения.",
              "- **приватная (`private`)** — видна только администратору.", "",
              "## Как вернуть в публикацию", "",
              "1. Проверить текст в `.md` и дату в поле `date`.",
              "2. Поставить `status: future` и дату в будущем — генератор (`site/build.py`)",
              "   такие файлы пока не собирает.",
              "3. Когда дата наступила — перенести материал в `data/model.json` → `posts[]`",
              "   (поля `title`, `slug`, `content`, `content_len`) и пересобрать сайт.", "",
              "## Предложение по отложенной публикации", "",
              "Схема, которую можно включить без ручной работы:", "",
              "1. Материалы лежат в `unpublished/` и имеют `date` и `status: future`.",
              "2. `site/build.py` при сборке читает эту папку и включает в блог те файлы,",
              "   у которых `date` уже наступила (остальные пропускает).",
              "3. На сервере `cron` раз в сутки запускает `git pull` + `build.py` + атомарную",
              "   подмену каталога — новый материал появляется сам в назначенный день.",
              "",
              "Альтернатива без cron: сборка запускается вручную в день публикации;",
              "даты при этом уже расставлены в front matter, ошибиться негде.", "",
              "## Файлы", "",
              "- `index.csv` — таблица с разделителем `;` (открывается в Excel).",
              "- `NN-<slug>.md` — текст материала с front matter.", ""]
    io.open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write("\n".join(lines))

    print("всего записей в БД: %d" % len(posts))
    print("неопубликованных: %d" % len(picked))
    for k, v in sorted(stats.items(), key=lambda x: -x[1])[:12]:
        print("  %-12s %-12s %d" % (k[0], k[1], v))
    print("папка:", OUT)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Убирает «.html» из внутренних ссылок статей: /reks-sil.html -> /reks-sil.

Зачем: генератор (`_fix_article`) оставляет только ссылки на известные URL, а известны
они без расширения. Ссылки вида `/reks-sil.html` он считал внешними и заменял на `/shop` —
из-за этого в блоке «Материалы РЕКС по теме» пропадали ссылки на карточки.

    & $py tools\\fix_article_links.py --dry
    & $py tools\\fix_article_links.py
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(BASE, "data", "model.json")
POSTS = os.path.join(BASE, "content", "articles")


def main():
    dry = "--dry" in sys.argv
    model = json.load(open(MODEL, encoding="utf-8"))
    known = set()
    for kind in ("products", "cats", "posts", "calcs"):
        for x in model[kind]:
            known.add(x["slug"])
    known |= {"blog", "shop", "kalkulyatory", "kontakty", "politika-konfidencialnosti"}

    rx = re.compile(r'href="/([A-Za-z0-9_-]+)\.html"')
    fixed = []

    def fix(html):
        def repl(m):
            slug = m.group(1)
            if slug in known:
                fixed.append(slug)
                return 'href="/%s"' % slug
            return m.group(0)
        return rx.sub(repl, html)

    changed_files = 0
    for name in sorted(os.listdir(POSTS)):
        if not name.endswith(".html"):
            continue
        path = os.path.join(POSTS, name)
        html = open(path, encoding="utf-8").read()
        new = fix(html)
        if new != html:
            changed_files += 1
            if not dry:
                open(path, "w", encoding="utf-8").write(new)

    changed_posts = 0
    for post in model["posts"]:
        if not post.get("content"):
            continue
        new = fix(post["content"])
        if new != post["content"]:
            changed_posts += 1
            if not dry:
                post["content"] = new

    print("файлов статей поправлено: %d | статей в модели: %d | ссылок: %d"
          % (changed_files, changed_posts, len(fixed)))
    if dry:
        print("--dry: не записано")
        return
    json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("записано")


if __name__ == "__main__":
    main()

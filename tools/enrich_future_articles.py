# -*- coding: utf-8 -*-
"""Добавляет в импортированные статьи блок «Материалы РЕКС по теме».

Берёт факты из базы знаний завода (data/rekspro/kb.json + match.json), форматирует
таблицу так же, как в 75 «старых» статьях (см. tools/articles_enrich.py), и вставляет
её перед разделом «Литература/Источники». Оглавление статьи обновляется.

    & $py tools\\enrich_future_articles.py --dry
    & $py tools\\enrich_future_articles.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import articles_enrich as ae  # noqa: E402  (готовые функции нормализации и разметки)

BASE = ae.ROOT
MODEL = os.path.join(BASE, "data", "model.json")
SRC = os.path.join(BASE, "data", "rekspro")

# тема статьи -> подпись + позиции каталога (slug'и сайта)
POOLS = [
    (r"пропитк|обеспыл|упрочн|гидрофоб|водоотталк",
     "укрепления и гидрофобизации поверхности",
     ["reks-gidrofob", "reks-super", "reks-akva-densit", "reks-anti-kapillyar"]),
    (r"протечк|гидропломб|течь|заделк.{0,20}шов",
     "ликвидации протечек",
     ["reks-plag-plag-30", "reks-sil", "hacut-kat"]),
    (r"инъекц|инъектир|пакер|смол|гел|тампонаж",
     "инъекционных работ",
     ["hacut-kat", "hasoil-gelakril", "reks-epo-inzh", "paker-inekcionnyj-stalnoj-13h115-mm-s-ploskoj-golovkoj"]),
    (r"анкер|шпильк|гильз|дюбел|крепёж|закладн|нагель",
     "химической анкеровки",
     ["reks-fiks-akrep", "reks-fiks-epo-tiks", "reks-fiks-epo-t-vn", "ankernaja-shpilka-ska-10-100"]),
    (r"шпонк|деформац|рабоч|герметик|лент|примыкан|шов",
     "герметизации швов",
     ["reks-gidrolenta", "gidroshponka-reks-p-4", "gidroshponka-thg-2p", "reks-bento-svello-25h20-mm"]),
    (r"мембран",
     "гидроизоляции мембранами",
     ["gidroizolyacionnaya-membrana-mvr", "reks-bento-svello-25h20-mm"]),
    (r"стяжк|ровнител|наливн|пол|гараж|склад|паркинг|производствен",
     "устройства полов",
     ["reks-53s", "reks-np-3000", "reks-epo-top", "reks-epo-prajmer"]),
    (r"плиточн|керамогранит|плитк",
     "плиточных работ",
     ["reks-klej-2000", "reks-klej-pljus", "reks-klejplit", "reks-klej-b55"]),
    (r"кладк|газобетон|пеноблок|кирпич|блок",
     "кладочных работ",
     ["reks-klej-penoblok", "reks-klej-teplokontakt", "reks-klej-b55"]),
    (r"краск|эмал|огнезащит|декор|антикор|корроз|защитн.{0,12}слой",
     "защиты и отделки конструкций",
     ["reks-prajmer-antikor", "reks-protekt", "reks-epo-dekos", "reks-barer"]),
    (r"бетон.?контакт|бетоноконтакт|грунтовк|праймер|адгези",
     "подготовки основания и адгезии",
     ["reks-prajmer", "reks-epo-prajmer", "reks-akril"]),
    (r"добавк|модификатор|пластификатор|противомороз",
     "модификации бетонных смесей",
     ["reks-msc-upm-protivomoroznyj-modifikator", "reks-msc-penakon", "reks-msc-antiglina"]),
    (r"торкрет|ремонт|восстановлен|смес|трещин|подлив|фундамент|колонн|балк|бетонирован",
     "ремонта бетонных конструкций",
     ["reks-r3", "reks-r4", "reks-ar", "reks-torkret"]),
    (r".", "гидроизоляции бетона",
     ["reks-sil", "reks-elast-100", "reks-super", "reks-akva-densit"]),
]

SOURCES = re.compile(r'<h2 id="((?:literatura|ispolzovannye|ssylki|istochniki)[^"]*)">')


def pretty(name):
    """«Рекс® r3» -> «РЕКС® Р3»: бренд капсом, латинские коды модели — тоже."""
    s = name.replace("Рекс", "РЕКС").replace("рекс", "РЕКС")
    s = re.sub(r"\b([a-z]{1,4})(\d+[a-z0-9]*)\b", lambda m: m.group(1).upper() + m.group(2), s)
    s = re.sub(r"\br3\b", "Р3", s, flags=re.I)
    s = re.sub(r"\br4\b", "Р4", s, flags=re.I)
    return s


def main():
    dry = "--dry" in sys.argv
    model = json.load(open(MODEL, encoding="utf-8"))
    kb = {k: v for k, v in json.load(open(os.path.join(SRC, "kb.json"), encoding="utf-8")).items()
          if not k.startswith("_")}
    match = json.load(open(os.path.join(SRC, "match.json"), encoding="utf-8"))
    site2kb = {s: r["kb"] for s, r in match.items() if r.get("kb")}
    kb2site = {}
    for s, k in site2kb.items():
        kb2site.setdefault(k, s)
    have = {p["slug"] for p in model["products"]}
    missing = sorted({s for _rx, _l, slugs in POOLS for s in slugs} - have)
    if missing:
        print("нет в каталоге (пропущены):", ", ".join(missing))

    done, skipped, no_pool = 0, 0, 0
    for post in model["posts"]:
        name = post.get("file")
        if not name:
            continue
        path = os.path.join(BASE, "content", name)
        html = open(path, encoding="utf-8").read()
        if 'id="materialy-reks"' in html:
            skipped += 1
            continue

        hay = (post["slug"] + " " + post["title"]).lower()
        label, pool = None, []
        for rx, lab, slugs in POOLS:
            if re.search(rx, hay):
                label, pool = lab, slugs
                break
        keys = [site2kb[s] for s in pool if s in have and s in site2kb]
        block = ae.materials_block(label, keys, kb, kb2site, {}, post["title"])
        if not block:
            no_pool += 1
            continue
        block = block.replace("Материалы завода по теме", "Материалы РЕКС по теме")
        block = re.sub(r'(<a href="/[^"]+">)([^<]+)(</a>)',
                       lambda m: m.group(1) + pretty(m.group(2)) + m.group(3), block)

        m = SOURCES.search(html)
        if m:
            html = html[:m.start()] + block.strip() + "\n\n" + html[m.start():]
            anchor = m.group(1)
        else:
            html = html.rstrip() + "\n\n" + block.strip() + "\n"
            anchor = None

        li = '<li><a href="#materialy-reks">Материалы РЕКС по теме</a></li>'
        if li not in html:
            if anchor and ('<a href="#%s">' % anchor) in html:
                html = html.replace('<li><a href="#%s">' % anchor, li + '\n<li><a href="#%s">' % anchor, 1)
            else:
                html = re.sub(r'(</ol></div>)', li + r'\1', html, count=1)

        post["content_len"] = len(re.sub(r"<[^>]+>", " ", html))
        if not dry:
            open(path, "w", encoding="utf-8").write(html)
        done += 1

    print("обогащено: %d | уже было: %d | без подходящих позиций: %d" % (done, skipped, no_pool))
    if dry:
        print("--dry: файлы не изменены")
        return
    json.dump(model, open(MODEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("модель обновлена (content_len)")


if __name__ == "__main__":
    main()

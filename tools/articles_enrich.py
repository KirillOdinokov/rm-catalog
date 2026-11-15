#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""articles_enrich.py — вычитка статей и внедрение фактов завода (база знаний reks.pro).

Что делает:
  1. типографика: пробел перед знаком, двойные пробелы, дефис вместо тире;
  2. правит формулировки, недопустимые для дилера («наш завод», «мы производим»);
  3. вставляет блок «Материалы завода по теме» — 3–4 реальные позиции с характеристиками
     из технических описаний завода и ссылками на карточки сайта;
  4. добавляет пункт в содержание статьи;
  5. пишет обратно data\model.json (копия до правки — data\model.before_articles.json).

Запуск: python tools\articles_enrich.py [--check]
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "rekspro")

# тема статьи -> (подпись, позиции завода)
TOPICS = [
    (r"oborudovanie|paker|nasos|igla", "оборудования для инъекционных работ",
     ["inektsionnyy-porshnevoy-nasos-gs-1k",
      "paker-inektsionnyy-stalnoy-13kh115-mm-s-ploskoy-go", "shilka-1"]),
    (r"gidroshponk|deformacionn|rabochih-shvov|p-obrazn|prizhimn|nabuhayushh", "герметизации швов",
     ["reks-tkhr-10p", "reks-tkhz-6p-zolushka", "reks-gidrolenta", "reks-bento-svello"]),
    (r"inekcionn|protech|usilenie-gruntov|kirpichnoj|tamponazh|kontrol-kachestva-inekcionnyh",
     "инъекционных работ",
     ["hacut-kat", "hasoil-gelakril", "reks-epo-inzh", "hasoil-rokstab"]),
    (r"aktivnyh-protechek", "ликвидации протечек",
     ["reks-plag-plag-30", "hacut-kat", "reks-sil"]),
    (r"himicheskie-ankera|ankern|podlivochn|germetizaciya-deformacionnyh",
     "анкеровки и подливки",
     ["reks-fiks-akrep", "reks-fiks-epo-tiks", "reks-fiks-epo-tvn", "reks-graut-gp"]),
    (r"pol|styazhk|rovnitel|nalivn|pokrytiya-promyshlennyh|avtoservis|sklad|pishhev|farmacevt|antistat",
     "устройства полов",
     ["reks-epo-top", "reks-epo-praymer", "reks-53s", "reks-top-k"]),
    (r"kle|kladk|plitk|penoblok|gazobeton|fasad|shtukaturno-kleevye", "клеевых и штукатурных работ",
     ["reks-kley-2000", "reks-kley-elast", "reks-kley-teplokontakt", "reks-epo-uni"]),
    (r"korroz|zashhit|prajmer|ognezashhit|importozameshhenie|sp-28|sp-72",
     "защиты бетона и металла",
     ["reks-praymer-antikor", "reks-protekt", "reks-dekor", "reks-gidrofob"]),
    (r"torrkret|torkret|tiksotrop|bystrotverdeyushh|mineralnye-smesi|remont-beton|remont-zhelezobeton|"
     r"remont-mostovyh|remont-betonnyh|vosstanovlenie-zashhitnogo|defekty|diagnostika|gost-32016|"
     r"polimernye-remontnye|sp-63",
     "ремонта бетонных конструкций",
     ["reks-r3", "reks-r4", "reks-ar", "reks-torkret-45"]),
    (r"geomeembran|geomembran", "гидроизоляции мембранами",
     ["gidroizolyatsionnaya-membrana-mvr", "reks-bento-svello"]),
    (r"gidrofob|pronikayushch", "защиты от капиллярной влаги",
     ["reks-gidrofob", "reks-super", "reks-akva-densit"]),
    (r".", "гидроизоляции",
     ["reks-sil", "reks-elast-100", "reks-super", "reks-akva-densit"]),
]

SPEC_PRIO = [r"водонепрониц", r"морозост", r"прочность на сжатие", r"сцеплени|адгези",
             r"толщин", r"расход", r"прочность на растяжение"]
BAD_CLAIMS = [
    (r"\bнаш(?:его|ем|им)?\s+завод\w*", "завода-производителя"),
    (r"\bмы\s+производим\b", "мы поставляем"),
    (r"\bмы\s+изготавливаем\b", "мы поставляем"),
    (r"\bсобственное\s+производство\b", "прямые поставки с завода"),
]


def decaps(s):
    s = (s or "").strip(" .")
    if not s:
        return ""
    if s != s.upper():
        return s
    keep = {"Р", "ВН", "НВ", "ЭПО", "ПУ", "PU", "ЖБ", "МСП", "МСЦ", "ТХГ", "ТХД", "НП", "БС",
            "АР", "ФМ", "ЕШ", "ШД", "СНВ", "AR", "МВР", "GS", "SKA", "МПа", "ПЗ", "УПМ"}
    out = []
    for w in s.split(" "):
        out.append(w if w.strip(".,;:()«»\"").upper() in keep else w.lower())
    r = " ".join(out)
    return r[:1].upper() + r[1:] if r else r


def cut(s, n):
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"


SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹", "01234567890123456789")


def clean_intro(s):
    """«РЕКС ® Сил - ГИДРОИЗОЛЯЦИОННАЯ СМЕСЬ» -> «Гидроизоляционная смесь»."""
    s = (s or "").strip().translate(SUB)
    s = re.sub(r"\s*®\s*", "®", s)
    m = re.match(r"^.{0,90}?\s[-—–]\s(.+)$", s)
    if m:
        s = m.group(1)
    s = re.sub(r"^(это|представляет собой)\s+", "", s, flags=re.I)
    return decaps(s)


KEYMAP = {"морозостойкости": "морозостойкость", "водонепроницаемости": "водонепроницаемость",
          "прочности на сжатие": "прочность на сжатие", "адгезии": "адгезия",
          "прочности сцепления": "прочность сцепления"}


def _digits(s):
    def f(m):
        o = ord(m.group(0))
        if 0x2080 <= o <= 0x2089:
            return str(o - 0x2080)
        if 0x2070 <= o <= 0x2079:
            return str(o - 0x2070)
        return m.group(0)
    return re.sub(r"[\u2070-\u2079\u2080-\u2089]", f, s)


def spec_of(kb):
    kv = kb.get("kv") or {}
    got = []
    for rx in SPEC_PRIO:
        for k, v in kv.items():
            if not re.search(rx, k, re.I) or not v or len(got) >= 2:
                continue
            name = re.sub(r"\(.*?\)", "", k)
            name = re.sub(r"\s*,\s*.*$", "", name)
            name = re.sub(r"^Марка по\s+", "", name, flags=re.I).strip().lower()
            name = KEYMAP.get(name, name)
            val = _digits(v).strip().rstrip(".")
            if re.search(r"в зависимости|зависит от", val, re.I):
                continue
            if len(val) > 70:
                val = val.split(".")[0][:70].rstrip(" ,;:")
            got.append("%s — %s" % (name, val))
            break
    return "; ".join(dict.fromkeys(got))


def materials_block(topic_label, keys, kb, inv, site_names, title=""):
    rows = []
    for k in keys:
        v = kb.get(k)
        if not v:
            continue
        site = inv.get(k)
        name = decaps(v["name"]).translate(SUB)
        purpose = cut(clean_intro(v.get("intro") or ""), 110)
        spec = spec_of(v)
        link = ('<a href="/%s.html">%s</a>' % (site, name)) if site else name
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (link, purpose or "—", spec or "—"))
    if not rows:
        return ""
    theme = cut(re.sub(r"\s*[|—].*$", "", title or topic_label), 70)
    return ('\n<h2 id="materialy-reks">Материалы завода по теме</h2>\n'
            '<p>К теме «%s» в каталоге завода относятся позиции ниже. Характеристики — '
            'из технических описаний производителя, поставка — со склада дилера.</p>\n'
            '<table><thead><tr><th>Материал</th><th>Назначение</th><th>Ключевые показатели</th>'
            '</tr></thead><tbody>%s</tbody></table>\n' % (theme, "".join(rows)))


def fix_typo(html):
    html = re.sub(r"[ \t]+([.,;:!?])", r"\1", html)
    # пробел/перенос перед знаком после тега: «…</a> .» -> «…</a>.»
    html = re.sub(r"\s+([.,;:!?])(?=\s|<|$)", r"\1", html)
    html = re.sub(r"(?<=[а-яёa-z0-9]) {2,}(?=[а-яёa-z0-9])", " ", html)
    html = re.sub(r"(?<=\s)-(?=\s)", "—", html)
    # случайный повтор слова в таблице (найден вычиткой)
    html = re.sub(r"\b(Полиуретановые)\s+\1\b", r"\1", html)
    return html


def main():
    check = "--check" in sys.argv
    model_p = os.path.join(ROOT, "data", "model.json")
    model = json.load(open(model_p, encoding="utf-8"))
    kb = {k: v for k, v in json.load(open(os.path.join(SRC, "kb.json"), encoding="utf-8")).items()
          if not k.startswith("_")}
    match = json.load(open(os.path.join(SRC, "match.json"), encoding="utf-8"))
    inv = {}
    for site, rec in match.items():
        if rec.get("kb"):
            inv.setdefault(rec["kb"], site)
    site_names = {p["slug"]: p["name"] for p in model["products"]}

    if not check:
        shutil.copyfile(model_p, os.path.join(ROOT, "data", "model.before_articles.json"))

    added, skipped, fixed = 0, 0, 0
    for post in model["posts"]:
        html = post.get("content") or ""
        orig = html
        for rx, rep in BAD_CLAIMS:
            html = re.sub(rx, rep, html, flags=re.I)
        html = fix_typo(html)
        topic_label, keys = "гидроизоляции", []
        hay = (post["slug"] + " " + post["title"]).lower()
        for rx, label, ks in TOPICS:
            if re.search(rx, hay):
                topic_label, keys = label, ks
                break
        block = materials_block(topic_label, keys, kb, inv, site_names, post["title"])
        if 'id="materialy-reks"' in html:
            if block:
                html = re.sub(r'\n?<h2 id="materialy-reks">.*?(?=\n<h2 |\Z)',
                              "\n" + block + "\n", html, flags=re.S)
                added += 1
            else:
                skipped += 1
        elif block:
            if '<h2 id="literatura">' in html:
                html = html.replace('<h2 id="literatura">', block + '\n<h2 id="literatura">', 1)
            else:
                html = html + block
            if 'href="#materialy-reks"' not in html and 'class="article-toc"' in html:
                html = re.sub(r'(<li><a href="#literatura">)',
                              r'<li><a href="#materialy-reks">Материалы завода по теме</a></li>\n\1',
                              html, count=1)
            added += 1
        if html != orig:
            post["content"] = html
            post["content_len"] = len(re.sub(r"<[^>]+>", " ", html))
            fixed += 1

    print("статей: %d, добавлен блок материалов: %d, уже был: %d, изменено: %d"
          % (len(model["posts"]), added, skipped, fixed))
    if not check:
        with open(model_p, "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False)
        print("записано:", model_p)


if __name__ == "__main__":
    main()

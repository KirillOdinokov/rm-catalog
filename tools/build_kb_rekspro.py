#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""build_kb_rekspro.py — база знаний по заводу РЕКС (reks.pro).

Вход:  data\rekspro\pages.jsonl, data\rekspro\docs.jsonl
Выход: E:\Оптимизация\Knowledge\reks.pro\
         README.md            — что это и как собрано
         products.csv         — сводная таблица позиций
         products.md          — полные карточки по разделам
         sections.md          — структура каталога завода
         docs.csv             — документы (паспорта, ТУ, сертификаты)
         docs\*.md            — распознанный текст PDF
         company.md           — факты о заводе
         articles.md          — статьи завода
       E:\Сайты\rex.moscow\data\rekspro\kb.json  — факты для генератора сайта
"""
import csv
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "rekspro")
KB = r"E:\Оптимизация\Knowledge\reks.pro"

JUNK_SUB = ("получить консультацию", "скачать pdf", "поделиться:", "применение на объектах",
            "оставить заявку", "заказать звонок", "вернуться в каталог")
JUNK_EXACT = ("описание", "достоинства", "характеристики", "применение", "фото", "видео",
              "отзывы", "документы", "похожие товары", "смеси", "все характеристики")
CYR = re.compile(r"[А-Яа-яЁё]")


def clean(s):
    s = s.replace("\xa0", " ").replace("®", "® ")
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .;•")


def load(name):
    p = os.path.join(SRC, name)
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def section_name(pg):
    """Раздел = путь из URL под /catalog/, кроме последнего сегмента."""
    p = pg["url"].replace("https://reks.pro", "").strip("/")
    parts = [x for x in p.split("/") if x]
    if parts and parts[0] == "catalog":
        return parts[1:-1]
    return []


def parse_product(pg):
    lines = []
    for b in pg.get("blocks", []):
        h = clean(b.get("head") or "")
        if h and h.lower() not in JUNK_EXACT and h.lower() != pg["name"].lower():
            lines.append(h)
        for ln in (b.get("text") or "").split("\n"):
            ln = ln.strip()
            if ln:
                lines.append(ln)

    intro, app, adv, extra = [], [], [], []
    mode = "intro"
    for ln in lines:
        low = ln.lower()
        if any(j in low for j in JUNK_SUB):
            continue
        if "см. в подробном описании" in low:
            continue
        if low.startswith("- "):
            t = clean(ln[2:])
            tl = t.lower()
            if tl.startswith("описание"):
                mode = "intro"
                continue
            if tl.startswith("достоинств"):
                mode = "adv"
                continue
            if tl.startswith("характеристик"):
                # в разметке сайта подписи вкладок идут подряд (Описание / Достоинства /
                # Характеристики), а списки преимуществ — уже после них; сами
                # характеристики берём из таблиц
                mode = "adv"
                continue
            if not t or len(t) < 4 or "см. в подробном описании" in tl:
                continue
            if mode in ("app", "spec"):
                app.append(t)
            elif mode == "adv":
                adv.append(t)
            else:
                intro.append(t)
            continue
        if low in JUNK_EXACT:
            if low in ("достоинства", ):
                mode = "adv"
            elif low in ("характеристики", "все характеристики"):
                mode = "spec"
            continue
        # заголовок блока капсом
        if CYR.search(ln) and ln == ln.upper() and len(ln) > 4:
            if "ОБЛАСТ" in ln:
                mode = "app"
                continue
            if "ДОСТОИНСТВ" in ln:
                mode = "adv"
                continue
            if "ОПИСАН" in ln:
                mode = "intro"
                continue
            if mode == "intro" and (" - " in ln or " — " in ln or " – " in ln):
                intro.append(clean(ln))
                continue
            extra.append(clean(ln))
            continue
        if mode == "adv":
            adv.append(clean(ln))
        elif mode == "app":
            app.append(clean(ln))
        else:
            intro.append(clean(ln))

    # таблицы: первая — цвет/расход/упаковка, дальше — характеристики
    kv, kv_first = {}, {}
    for ti, tb in enumerate(pg.get("tables", [])):
        for row in tb:
            if len(row) < 2:
                continue
            k = clean(row[0])
            v = clean(" ".join(row[1:]))
            if not k or not v:
                continue
            if ti == 0 and re.match(r"(цвет|расход|упаковка|вес|объ[её]м|фасовка|гарант)", k, re.I):
                kv_first[k] = v
            else:
                kv[k] = v
    for k, v in kv_first.items():
        kv.setdefault(k, v)

    def pick(rx):
        for k, v in list(kv_first.items()) + list(kv.items()):
            if re.search(rx, k, re.I):
                return v
        return ""

    return {
        "url": pg["url"],
        "name": pg["name"],
        "section": section_name(pg),
        "intro": intro,
        "app": app,
        "adv": adv,
        "kv": kv,
        "color": pick(r"цвет"),
        "pack": pick(r"упаков|фасов"),
        "cons": pick(r"расход"),
        "meta": pg.get("meta_desc", ""),
        "pdf": [d["url"] for d in pg.get("pdf", [])],
        "img": pg.get("img", []),
    }


def strip_sup(s):
    return (s.replace("₂", "2").replace("₀", "0").replace("⁰", "0")
             .replace("⁵", "5").replace("⁴", "4").replace("³", "3"))


def kpath(sec, names=None):
    names = names or {}
    return " → ".join(names.get(x, x.replace("-", " ")) for x in sec)


def write_products(prods, cats, names=None):
    names = names or {}
    lines = ["# Каталог завода РЕКС® — полные карточки", "",
             "Источник: https://reks.pro (официальный сайт производителя). Собрано %s." % date.today(),
             "Формулировки областей применения и преимуществ — дословно с сайта завода.", ""]
    cur = None
    for p in sorted(prods, key=lambda x: (x["section"], x["name"])):
        sec = " / ".join(names.get(x, x.replace("-", " ")) for x in p["section"]) if p["section"] else "Каталог"
        if sec != cur:
            cur = sec
            lines += ["", "## " + sec, ""]
        lines.append("### %s" % p["name"])
        lines.append("")
        lines.append("<%s>" % p["url"])
        lines.append("")
        if p["intro"]:
            lines.append("**Что это.** " + " ".join(p["intro"]))
            lines.append("")
        if p["app"]:
            lines.append("**Область применения**")
            lines.append("")
            lines += ["- " + x for x in p["app"]]
            lines.append("")
        if p["adv"]:
            lines.append("**Преимущества**")
            lines.append("")
            lines += ["- " + x for x in p["adv"]]
            lines.append("")
        if p["kv"]:
            lines.append("**Технические характеристики**")
            lines.append("")
            lines.append("| Показатель | Значение |")
            lines.append("|---|---|")
            for k, v in p["kv"].items():
                lines.append("| %s | %s |" % (strip_sup(k).replace("|", "/"),
                                              strip_sup(v).replace("|", "/")))
            lines.append("")
        if p["pdf"]:
            lines.append("Документы: " + ", ".join(p["pdf"]))
            lines.append("")
        if p.get("prep") or p.get("apply"):
            lines.append("**Технология по паспорту завода**")
            lines.append("")
            if p.get("prep"):
                lines.append("*Подготовка:* " + p["prep"])
                lines.append("")
            if p.get("mix"):
                lines.append("*Приготовление:* " + p["mix"])
                lines.append("")
            if p.get("apply"):
                lines.append("*Нанесение:* " + p["apply"])
                lines.append("")
    return "\n".join(lines)


def clean_doc(t):
    """Текст паспорта: убираем переносы, маркеры шрифта и служебный подвал."""
    t = t.replace("\r", "")
    t = re.sub(r"\[\[стр\.\s*\d+\]\]", "\n", t)          # маркеры страниц
    t = re.sub(r"(?<=\w)-\n(?=[а-яё])", "", t)          # перенос по слогам
    t = t.replace("џ", "\n• ")
    t = re.sub(r"^\s*®\s*$", "", t, flags=re.M)
    t = re.sub(r"\S+@\S+", "", t)                       # почта
    t = re.sub(r"\+?7\s*\(?\d{3}\)?[\s-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}", "", t)
    t = re.sub(r"(Официальный представитель|123308|Телефон:|E-mail:|Сайт: www\.reks\.pro|"
               r"Техническая спецификация|ТЕХНИЧЕСКОЕ ОПИСАНИЕ|ООО «ТД РЕКС»|"
               r"проспект Маршала Жукова|офис 508)", "", t)
    t = re.sub(r"\b(Январь|Февраль|Март|Апрель|Май|Июнь|Июль|Август|Сентябрь|Октябрь|Ноябрь|"
               r"Декабрь)\s+20\d\d\b", "", t)
    # строки-адреса и служебные обрывки не нужны в технологическом тексте
    ADDR = re.compile(r"Россия,\s*Москва|дом\s*\d+,\s*корпус|строение\s*\d|"
                      r"^\s*[,;:.\s\d-]{0,12}$", re.I)
    t = "\n".join(ln for ln in t.split("\n") if not ADDR.search(ln))
    t = re.sub(r"(?:\s*[,;:]\s*){2,}", ". ", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


STOP_HEAD = re.compile(r"^\s*(\d+(\.\d+)*\.?\s+[А-ЯЁ]|Официальн|Технические характеристики|"
                       r"Хранение|Меры безопасности|Упаковка|Гарант|Состав|"
                       r"Сертификац)", re.M)


def doc_part(t, keys):
    """Абзац паспорта от заголовка с одним из keys до следующего заголовка."""
    low = t.lower()
    for k in keys:
        i = low.find(k.lower())
        if i < 0:
            continue
        # сама строка заголовка в текст не идёт
        j = t.find("\n", i)
        tail = t[j + 1:] if 0 < j - i < 90 else t[i:]
        m = STOP_HEAD.search(tail, 3)
        part = tail[:m.start()] if m else tail[:1200]
        part = part.replace("\n", " ").replace("•", " ")
        part = re.sub(r"\s+", " ", part).strip()
        if len(part) > 60:
            return part
    return ""


def tech_parts(text):
    if not text:
        return "", "", ""
    t = clean_doc(text)
    prep = doc_part(t, ("Подготовка поверхности", "Подготовка основания", "8.1"))
    mix = doc_part(t, ("Смешивание", "Приготовление", "8.2"))
    app = doc_part(t, ("Нанесение", "Способ применения", "8.3"))
    return prep[:900], mix[:700], app[:1200]


def main():
    pages = load("pages.jsonl")
    docs = load("docs.jsonl")
    if not pages:
        print("нет data\\rekspro\\pages.jsonl")
        return
    os.makedirs(KB, exist_ok=True)
    os.makedirs(os.path.join(KB, "docs"), exist_ok=True)

    cats = [p for p in pages if p["kind"] == "category" and not any(
        b in p["url"] for b in ("/cart", "/wishlist", "/compare", "/show", "/search"))]
    names = {}
    for c in cats:
        seg = c["url"].rstrip("/").rsplit("/", 1)[-1]
        if c["name"]:
            names[seg] = c["name"]
    BAD = ("/catalog/show", "/catalog/wishlist", "/catalog/compare", "/catalog/search")
    prods = []
    for p in pages:
        if p["kind"] != "product" or any(b in p["url"] for b in BAD):
            continue
        pp = parse_product(p)
        if not pp["name"] or not (pp["kv"] or pp["pdf"] or pp["app"]):
            continue
        prods.append(pp)

    docs_by_url = {d.get("url"): d for d in docs}
    for p in prods:
        txt = ""
        for u in p["pdf"]:
            if u in docs_by_url:
                txt = docs_by_url[u].get("text", "")
                break
        p["prep"], p["mix"], p["apply"] = tech_parts(txt)
    arts = [p for p in pages if p["kind"] == "article"]
    servs = [p for p in pages if p["kind"] == "service"]
    others = [p for p in pages if p["kind"] in ("page", "techdocs")]
    print("products:", len(prods), "sections:", len(cats), "articles:", len(arts),
          "services:", len(servs), "docs:", len(docs))

    # ---------- products.csv ----------
    with open(os.path.join(KB, "products.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Раздел", "Наименование", "URL", "Что это", "Область применения",
                    "Преимущества", "Цвет", "Упаковка", "Расход", "Характеристик", "PDF", "Фото"])
        for p in sorted(prods, key=lambda x: (x["section"], x["name"])):
            w.writerow([kpath(p["section"], names), p["name"], p["url"], " ".join(p["intro"]),
                        " • ".join(p["app"]), " • ".join(p["adv"]), p["color"], p["pack"],
                        p["cons"], len(p["kv"]), "; ".join(p["pdf"]), "; ".join(p["img"])])

    # ---------- products.md ----------
    with open(os.path.join(KB, "products.md"), "w", encoding="utf-8") as f:
        f.write(write_products(prods, cats, names))

    # ---------- sections.md ----------
    MODAL = re.compile(r"(консультац|прикрепить|нажимая|отправить|обратный звонок|"
                       r"нужна|ваше имя|телефон|e-mail)", re.I)
    name_by_url = {c["url"]: c["name"] for c in cats}
    lines = ["# Разделы каталога завода РЕКС®", "",
             "Структура и формулировки с https://reks.pro/catalog.", ""]
    for c in sorted(cats, key=lambda x: len(section_name(x))):
        cnt = len([p for p in prods if p["section"] and p["url"].startswith(c["url"] + "/")])
        lines.append("## %s — %d поз." % (c["name"] or c["url"], cnt))
        lines.append("")
        lines.append("<%s>" % c["url"])
        lines.append("")
        added = 0
        for b in c.get("blocks", [])[:8]:
            raw = (b.get("text") or "")
            keep = [x.strip() for x in raw.split("\n")
                    if x.strip() and not x.strip().startswith("- ") and not MODAL.search(x)]
            t = clean(" ".join(keep))
            t = re.sub(r"(Наш менеджер|Нужна консультация|Оставьте|Закажите).*$", "", t).strip()
            nm = (c["name"] or "").upper()
            if nm and len(nm) > 5 and nm in t.upper()[1:]:
                t = t[:t.upper().find(nm, 1)].strip(" ,;:—-")
            t = re.split(r"\s+РЕКС\s*®?\s*", t)[0].strip(" ,;:—-")
            if len(t) > 320:
                t = t[:320].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
            if 40 < len(t):
                lines.append(t)
                lines.append("")
                added += 1
        if not added and c.get("meta_desc"):
            md = re.sub(r"\s*ТД РЕКС.*$", "", c["meta_desc"]).strip()
            if len(md) > 30:
                lines.append(md)
                lines.append("")
        lines.append("")
    with open(os.path.join(KB, "sections.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---------- docs ----------
    with open(os.path.join(KB, "docs.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Файл", "Заголовок", "Страница-источник", "Товар/раздел", "Страниц",
                    "Символов", "Скан-страниц", "URL"])
        for d in docs:
            w.writerow([d.get("file", ""), d.get("label", ""), d.get("page", ""), d.get("name", ""),
                        d.get("pages", ""), d.get("chars", ""), d.get("scanned", ""), d.get("url", "")])
    for d in docs:
        txt = d.get("text", "")
        head = "# %s\n\nИсточник: %s\nТовар: %s\nСтраниц: %s\n\n---\n\n" % (
            d.get("name") or d.get("file"), d.get("url", ""), d.get("name", ""), d.get("pages", ""))
        with open(os.path.join(KB, "docs", d["file"].replace(".pdf", ".md")), "w",
                  encoding="utf-8") as f:
            f.write(head + txt)

    # ---------- company / articles / services ----------
    def dump(kind, title, fname, note):
        out = ["# " + title, "", note, ""]
        for p in sorted([x for x in pages if x["kind"] == kind], key=lambda x: x["url"]):
            out.append("## " + (p["name"] or p["url"]))
            out.append("")
            out.append("<%s>" % p["url"])
            out.append("")
            for b in p.get("blocks", []):
                t = clean(b.get("text", ""))
                if len(t) > 60:
                    if b.get("head") and b["head"] != p["name"]:
                        out.append("**%s**" % clean(b["head"]))
                        out.append("")
                    out.append(t)
                    out.append("")
            out.append("")
        with open(os.path.join(KB, fname), "w", encoding="utf-8") as f:
            f.write("\n".join(out))

    dump("page", "Завод РЕКС — о компании, производство, дилеры, контакты", "company.md",
         "Дословные тексты со страниц reks.pro/about, /nashe-proizvodstvo, /dealers, /contacts.")
    dump("article", "Статьи завода РЕКС®", "articles.md",
         "Технические статьи reks.pro — источник фактов и формулировок для статей дилера.")
    dump("service", "Услуги завода РЕКС®", "services.md",
         "Инженерное сопровождение, обучение, выезд на объект, документация.")
    if others:
        dump("techdocs", "Техническая документация завода", "techdocs.md",
             "Раздел /tech-docs: перечень паспортов, ТУ и сертификатов.")

    # ---------- kb.json для генератора сайта ----------
    kbp = {}
    for p in prods:
        slug = p["url"].rstrip("/").rsplit("/", 1)[-1]
        kbp[slug] = {
            "name": p["name"],
            "url": p["url"],
            "section": p["section"],
            "intro": " ".join(p["intro"]),
            "app": p["app"],
            "adv": p["adv"],
            "kv": {strip_sup(k): strip_sup(v) for k, v in p["kv"].items()},
            "color": p["color"],
            "pack": p["pack"],
            "cons": p["cons"],
            "pdf": p["pdf"],
            "img": p["img"],
            "prep": p["prep"],
            "mix": p["mix"],
            "apply": p["apply"],
        }
    kbp["_sections"] = {seg: nm for seg, nm in names.items()}
    kbp["_docs"] = {d.get("file", ""): {"label": d.get("label", ""), "page": d.get("page", ""),
                                       "chars": d.get("chars", 0)}
                    for d in docs}
    with open(os.path.join(SRC, "kb.json"), "w", encoding="utf-8") as f:
        json.dump(kbp, f, ensure_ascii=False, indent=1)
    # ---------- README ----------
    readme = """# База знаний: завод РЕКС® (reks.pro)

Единая база знаний по продукции завода **РЕКС®** — для описаний товаров, статей и любых
материалов по этому направлению (не только для rex.moscow).

Собрано автоматически с официального сайта производителя **https://reks.pro** ({today}).

## Что внутри

| Файл | Содержание |
|---|---|
| `products.csv` | все позиции каталога: раздел, название, «что это», область применения, преимущества, цвет, упаковка, расход, число характеристик, ссылки на PDF и фото |
| `products.md` | полные карточки по разделам: описание, область применения, преимущества, таблица характеристик |
| `sections.md` | структура каталога завода (направления и подразделы) с описаниями |
| `docs.csv` | перечень технических документов (паспорта, ТУ, сертификаты) |
| `docs\\*.md` | распознанный текст каждого PDF (постранично), с чисткой переносов |
| `pdf\\*.pdf` | сами документы завода (паспорта и технические описания) |
| `company.md` | о компании, производство, дилеры, контакты, объекты |
| `articles.md` | технические статьи завода |
| `services.md` | услуги: обследование объекта, техрешения, обучение, шеф-монтаж |
| `techdocs.md` | раздел технической документации |

## Покрытие

- позиций каталога: **{n_prod}**
- разделов: **{n_cat}**
- документов PDF: **{n_docs}** (распознано символов: **{n_chars}**)
- статей завода: **{n_art}**, услуг: **{n_srv}**

Часть карточек на сайте завода — заглушки «Страница в стадии разработки» (гидрошпонки,
часть оснастки). По ним фактов в этой базе нет: данные берём из прайса и архива старого сайта.

## Как использовать

1. **Описание товара.** Основа — «что это» (строка из техописания завода), область применения,
   преимущества, 7–10 ключевых характеристик, упаковка и расход, а также разделы паспорта
   «Подготовка основания», «Приготовление», «Нанесение». Формулировки завода технические,
   переписывать их в маркетинговый текст не нужно.
2. **Статья.** Факты (марки, классы, прочность, морозостойкость, водонепроницаемость, толщины,
   расход) сверяем по `products.md` и `docs\\`; ссылки на нормативы — по текстам паспортов.
3. **Подбор материала.** Раздел и назначение берём из `sections.md`, совместимость систем —
   из области применения соседних позиций.
4. **Проверка формулировок.** Если в тексте появляется цифра или марка, её источник — эта база.
   Нет в базе — значит, цифру писать нельзя.

## Как собрано

`tools\\rekspro_crawl.py` (страницы каталога, статей, услуг) → `tools\\rekspro_assets.py`
(фото и PDF, распознавание через PyMuPDF с учётом двухколоночной вёрстки) →
`tools\\build_kb_rekspro.py` (эта база + `data\\rekspro\\kb.json` для генератора сайта).
Сопоставление карточек дилера с карточками завода — `tools\\rekspro_match.py`
(ручные пары в `data\\rekspro\\manual_match.json`).

## Правовые рамки для дилера

Материалы завода используем как источник фактов. На сайте дилера нельзя писать «наш завод»,
«мы производим»: только «официальный дилер», «прямые поставки с завода».

**«ТД РЕКС» / «Торговый дом РЕКС» / ООО «ТД РЕКС» — это торговая компания завода** (так она
названа на reks.pro), а не заказчик. В материалах дилера это название не используем:
правообладатель — домен, реквизиты — по запросу. В файлах `company.md`, `docs\\` и `pdf\\`
оно встречается как данные завода — при цитировании убираем.
""".format(today=date.today().isoformat(), n_prod=len(prods), n_cat=len(cats),
           n_docs=len(docs), n_chars=sum(d.get("chars", 0) for d in docs),
           n_art=len(arts), n_srv=len(servs))
    with open(os.path.join(KB, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)
    print("KB ->", KB)


if __name__ == "__main__":
    main()

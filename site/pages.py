# -*- coding: utf-8 -*-
"""Рендер страниц rex.moscow."""
import json
import os
import re

import art
import config as C
import content
import images
import schema
import shell
from shell import esc, money

# даты статей из бэкапа БД: нужны для Article и sitemap
try:
    POST_DATES = json.load(open(os.path.join(C.DATA, "post_dates.json"), encoding="utf-8"))
except Exception:
    POST_DATES = {}


class Model(object):
    def __init__(self):
        m = json.load(open(os.path.join(C.DATA, "model.json"), encoding="utf-8"))
        self.products = m["products"]
        self.cats = m["cats"]
        self.pages = {p["slug"]: p for p in m["pages"]}
        self.posts = m["posts"]
        self.calcs = m["calcs"]
        self.by_slug = {p["slug"]: p for p in self.products}
        self.cat_by = {c["slug"]: c for c in self.cats}
        self.children = {}
        for c in self.cats:
            self.children.setdefault(c["parent"], []).append(c)
        self.root_cats = [c for c in self.cats if not c["parent"]]
        self.prod_cats = {}
        for p in self.products:
            for s in p["cats"]:
                self.prod_cats.setdefault(s, []).append(p)
        self.post_by = {p["slug"]: p for p in self.posts}
        # первый владелец description: нужен, чтобы не выводить одинаковые описания
        self._desc_owner = {}
        for p in self.products:
            d = (p.get("meta_desc") or "").strip()
            if d and d not in self._desc_owner:
                self._desc_owner[d] = p["slug"]

    def desc_owner(self, d):
        return self._desc_owner.get((d or "").strip())

    def url(self, p):
        return "/" + p["slug"]

    def subtree(self, slug):
        out = [slug]
        for ch in self.children.get(self.cat_by[slug]["id"], []):
            out.extend(self.subtree(ch["slug"]))
        return out

    def products_in(self, slug):
        seen, res = set(), []
        for s in self.subtree(slug):
            for p in self.prod_cats.get(s, []):
                if p["slug"] not in seen:
                    seen.add(p["slug"])
                    res.append(p)
        return res

    def parents(self, cat):
        chain, cur = [], cat
        while cur and cur["parent"]:
            cur = next((c for c in self.cats if c["id"] == cur["parent"]), None)
            if cur:
                chain.append(cur)
        return list(reversed(chain))

    def count(self, slug):
        return len(self.products_in(slug))


M = None


def model():
    global M
    if M is None:
        M = Model()
    return M


def price_html(p, big=False):
    if p["price"]:
        return shell.price_block(p)
    return '<div class="prod__price">Цена по запросу</div>'


# ------------------------------------------------------------------ метаданные
WP_TAIL = re.compile(r"\s*[-–—]\s*(?:характеристики|описание|цена|купить|фото|отзывы|"
                     r"инструкция|применение|состав и свойства|доставка)[^-|]{0,90}$", re.I)


def trim_desc(s, limit=175):
    """Обрезка description по границе предложения (а не на полуслове)."""
    s = re.sub(r"\s+", " ", (s or "")).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    for sep in (". ", "! ", "? ", "; "):
        i = cut.rfind(sep)
        if i > 90:
            return cut[:i + 1].strip()
    i = cut.rfind(" ")
    return cut[:i].rstrip(" ,;:—-") + "."


def product_title(p):
    """Title не длиннее ~70 знаков: чистим WP-хвост, иначе собираем свой."""
    t = (p.get("meta_title") or "").strip()
    if t and len(t) <= 70:
        return t
    if t:
        short = WP_TAIL.sub("", t).strip()
        if len(short) <= 62:
            return short + " | РЕКС"
    name = p["name"]
    suf = (" — купить, цена %s ₽ | РЕКС" % "{:,}".format(p["price"]).replace(",", " ")
           if p.get("price") else " — купить, цена по запросу | РЕКС")
    room = 70 - len(suf)
    if len(name) <= room:
        return name + suf
    cut = name[:room]
    cut = cut[:cut.rfind(" ")] if " " in cut else cut
    return cut.rstrip(" ,;—-") + suf


def product_desc(p, m, ct):
    """Description: уникальный (без повторов), не длиннее 175 знаков."""
    if ct.get("meta"):
        return trim_desc(ct["meta"])
    d = (p.get("meta_desc") or "").strip()
    if d and m.desc_owner(d) == p["slug"]:
        return trim_desc(d)
    return trim_desc(ct["lead"])


def cat_title(c):
    t = (c.get("meta_title") or "").strip()
    if t and len(t) <= 70:
        return t
    if t:
        short = WP_TAIL.sub("", t).strip()
        if len(short) <= 62:
            return short + " | РЕКС"
    name = c["name"]
    suf = " — купить в Москве | РЕКС"
    room = 70 - len(suf)
    if len(name) <= room:
        return name + suf
    cut = name[:room]
    cut = cut[:cut.rfind(" ")] if " " in cut else cut
    return cut.rstrip(" ,;—-") + suf


def card(p):
    m = model()
    ct = content.cluster_of(p)[1]["kind"]
    price = ("%s <small>₽</small>" % "{:,}".format(p["price"]).replace(",", " ")) if p["price"] \
        else '<span class="pcard__ask">по запросу</span>'
    ph = images.product(p)
    media = ('<div class="pcard__plate pcard__plate--photo">%s</div>'
             % images.tag(ph, esc(p["name"]), w=560, h=420)) if ph else \
            ('<div class="pcard__plate">%s</div>' % art.plate(p))
    return """
<article class="pcard">
  %s
  <div class="pcard__kind">%s</div>
  <h3 class="pcard__name"><a href="%s">%s</a></h3>
  <div class="pcard__foot"><span class="pcard__price">%s</span><span class="pcard__ask">%s</span></div>
</article>""" % (media, esc(ct), m.url(p), esc(p["name"]), price,
                 "Арт. %s" % esc(p["sku"]))


def faq_block(faq):
    items = "".join(
        '<div class="spec__row" style="grid-template-columns:minmax(0,1fr)"><dt style="padding:0 0 5px">%s</dt>'
        '<dd style="color:#456a83">%s</dd></div>' % (esc(q), esc(a)) for q, a in faq)
    return '<div class="spec" style="margin-top:8px">%s</div>' % items


# ------------------------------------------------------------------ иконки и CTA
GROUP_ICON = {
    "gidroizolyaciya-betona": "drop",
    "smesi-dlya-remonta-betona": "trowel",
    "polimernye-poly": "layers",
    "smesi-dlya-zashhity-betona-i-zhbi": "shield",
    "adgezionnye-i-kleyashie-sostavy": "glue",
    "ankerovochnye-sostavy": "bolt",
}
TASK_ICON = {"fundament": "drop", "remont": "trowel", "protechka": "shield",
             "pol": "layers", "shov": "ruler", "anker": "bolt"}
STRIP_ITEMS = [
    ("warehouse", "Отгрузка со склада", "в течение 24 часов"),
    ("seal", "Документы на партию", "паспорт качества и сертификат"),
    ("helmet", "Инженер на объекте", "Москва и Подмосковье — бесплатно"),
    ("factory", "Статус поставщика", "официальный дилер завода РЕКС"),
]


def strip():
    items = "".join('<div class="strip__i">%s<div><b>%s</b><span>%s</span></div></div>'
                    % (art.icon(i), esc(b), esc(s)) for i, b, s in STRIP_ITEMS)
    return '<div class="strip">%s</div>' % items


def _visit_ok(slugs):
    """Есть ли на странице кнопка выезда специалиста (кроме гидрошпонок)."""
    for s in slugs or []:
        if s in C.VISIT_EXCEPT:
            return False
    return True


def visit_block(slugs=None, label=None):
    return shell.visit_cta(label) if _visit_ok(slugs) else ""


# ------------------------------------------------------------------ главная
def plural(n, forms):
    """plural(3, ("позиция", "позиции", "позиций")) -> "позиции"."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def home():
    m = model()
    groups = []
    for slug, title, desc, num in C.GROUPS:
        n = m.count(slug)
        groups.append("""
<a class="group" href="/%s">
  <div class="group__icon">%s</div>
  <div class="group__i">%s · %d %s</div>
  <h3>%s</h3>
  <p>%s</p>
  <span class="group__link">Смотреть раздел %s</span>
</a>""" % (slug, art.icon(GROUP_ICON.get(slug, "grid")), num, n,
           plural(n, ("позиция", "позиции", "позиций")),
           esc(title), esc(desc), art.icon("arrow")))

    popular = [p for p in m.products if p["price"]][:8]
    popular_html = "".join(card(p) for p in popular)

    tasks = "".join("""
<a class="group" href="%s">
  <div class="group__icon">%s</div>
  <div class="group__i">задача</div>
  <h3>%s</h3><p>%s</p>
  <span class="group__link">Решение %s</span>
</a>""" % (url, art.icon(TASK_ICON.get(k, "grid")), esc(t), esc(d), art.icon("arrow"))
                   for t, d, url, k in C.TASKS)

    arts = "".join("""
<a class="group" href="/%s" style="padding:22px 24px">
  <div class="group__i">статья · %d симв.</div>
  <h3 style="font-size:18px;margin:9px 0 6px">%s</h3>
  <span class="group__link">Читать %s</span>
</a>""" % (a["slug"], a["content_len"], esc(a["title"]), art.icon("arrow")) for a in m.posts[:4])

    standards = "".join('<div class="spec__row"><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v))
                        for k, v in C.STANDARDS)

    facts_list = [(str(len(m.products)), "позиций в каталоге")] + list(C.FACTS[1:])
    facts = "".join('<div class="hero__fact"><b>%s</b><span>%s</span></div>' % (esc(v), esc(t))
                    for v, t in facts_list)

    kpi = "".join('<div><b>%s</b><span>%s</span></div>' % (esc(v), esc(t)) for v, t in facts_list)

    body = """
<section class="hero"><div class="wrap hero__in">
  <div>
    <div class="hero__eyebrow mono"><i></i> %s · с 2014 года</div>
    <h1>Инженерная химия<br>для <em>бетона</em></h1>
    <p class="hero__lead">Гидроизоляция, ремонт, защита и промышленные полы РЕКС. Подбираем систему
    под узел и условия эксплуатации, считаем расход, выезжаем на объект и отгружаем со склада
    в течение суток.</p>
    <div class="hero__act">
      <a class="btn btn--acc btn--lg" href="#zapros">Подобрать материал</a>
      <a class="btn btn--ghost btn--lg" href="%s">%s Вызвать специалиста</a>
    </div>
    <div class="hero__facts">%s</div>
  </div>
  <div class="passport">
    <div class="passport__code">ТЕХПАСПОРТ</div>
    <div class="passport__top"><span>Узел гидроизоляции</span><span></span></div>
    <div class="passport__plate">%s</div>
    <dl style="margin:0">
      <div class="passport__row"><dt>Система</dt><dd>Инъекция + мембрана</dd></div>
      <div class="passport__row"><dt>Раскрытие шва</dt><dd>до 5 мм</dd></div>
      <div class="passport__row"><dt>Класс среды</dt><dd>XА2 · W12</dd></div>
      <div class="passport__row"><dt>Расчёт</dt><dd>по заданию</dd></div>
    </dl>
  </div>
</div></section>
%s

<section class="sec"><div class="wrap">
  %s
  <div class="groups">%s</div>
</div></section>

<section class="sec" style="background:#e9f4fb"><div class="wrap">
  <div class="sec__head"><div><div class="eyebrow"><b>02</b> — каталог</div>
    <h2>Что чаще всего заказывают</h2></div>
    <div class="sec__lead">Цены указаны за единицу с НДС по прайсу от 10 сентября 2026 г.
    Минимальная сумма заказа —
    %s ₽. Для объёмных поставок готовим спецификацию и коммерческое предложение.</div></div>
  <div class="cards">%s</div>
  <div style="margin-top:26px"><a class="btn btn--ghost" href="/shop">Весь каталог %s</a></div>
</div></section>

<section class="sec"><div class="wrap">
  <div class="sec__head"><div><div class="eyebrow"><b>03</b> — задачи</div>
    <h2>С чем приходят на объект</h2></div>
    <div class="sec__lead">Шесть типовых задач, под которые у нас собраны готовые системы
    материалов с технологией и расчётом расхода.</div></div>
  <div class="groups">%s</div>
  %s
</div></section>

<section class="sec sec--dark"><div class="wrap">
  <div class="sec__head"><div><div class="eyebrow"><b>04</b> — нормативы</div>
    <h2>Работаем по действующим нормам</h2></div>
    <div class="sec__lead">Материалы и системы подбираем с учётом требований СП и ГОСТ,
    готовим документы для проектной и исполнительной документации.</div></div>
  <div class="kpi">%s</div>
  <div class="split" style="margin-top:36px">
    <div class="spec" style="border-top:1px solid rgba(255,255,255,.14)">%s</div>
    <div class="side-card side-card--dark" style="margin:0">
      <h3>Документы на партию</h3>
      <p>Паспорт качества, сертификат соответствия, инструкция по применению и техническое
      описание. Для проектных организаций — альбомы узлов и расчёт расхода.</p>
      <a class="btn btn--acc" href="mailto:%s?subject=Запрос документов" style="margin-top:16px">Запросить документы</a>
    </div>
  </div>
</div></section>

<section class="sec"><div class="wrap">
  <div class="sec__head"><div><div class="eyebrow"><b>05</b> — инженерия</div>
    <h2>Разбираем узлы в блоге</h2></div>
    <div class="sec__lead">75 технических статей: технологии, ошибки, нормативы и разбор
    конкретных узлов гидроизоляции и ремонта.</div></div>
  <div class="groups">%s</div>
  <div style="margin-top:26px;display:flex;gap:10px;flex-wrap:wrap">
    <a class="btn btn--ghost" href="/blog">Все статьи</a>
    <a class="btn btn--ghost" href="/kalkulyatory">Калькуляторы расхода</a>
  </div>
</div></section>
""" % (esc(C.DEALER), C.VISIT_URL, art.icon("helmet"), facts, art.hero_art(), strip(),
       shell.section_head("01", "Шесть направлений",
           "Каждое направление — законченная система материалов: основание, основной слой, "
           "финиш и герметизация примыканий."),
       "".join(groups), "{:,}".format(C.MIN_ORDER).replace(",", " "), popular_html,
       art.icon("arrow"), tasks, "<div style=\"margin-top:26px\">%s</div>" % shell.visit_cta(),
       kpi, standards, C.EMAIL, arts)

    body += shell.cta_band()
    body += shell.lead_form()
    desc = ("Официальный дилер завода РЕКС: гидроизоляция бетона, ремонтные смеси, промышленные "
            "полы, защита и анкеровка. %d позиций, подбор под узел, расчёт расхода, выезд инженера "
            "на объект, отгрузка со склада." % len(m.products))
    return shell.page("/", "РЕКС — инженерная химия для бетона: гидроизоляция, ремонт | Москва",
                      trim_desc(desc), body, ld=schema.dumps(*schema.org()))


# ------------------------------------------------------------------ каталог
def catalog():
    m = model()
    rows = []
    for root in m.root_cats:
        subs = m.children.get(root["id"], [])
        sub_html = ", ".join(
            '<a href="/%s">%s</a>' % (s["slug"], esc(s["name"])) for s in subs if m.count(s["slug"]))
        rows.append("""
<div class="catrow">
  <div class="catrow__n">%d</div>
  <div class="catrow__t"><a href="/%s">%s</a><small>%s</small></div>
  <div class="catrow__c">%d поз.</div>
  %s
</div>""" % (len(rows) + 1, root["slug"], esc(root["name"]), sub_html or esc(root["meta_desc"] or ""),
             m.count(root["slug"]), art.icon("arrow")))
    body = """
%s
<div class="wrap">
  <div class="pagehead">
    <div class="eyebrow"><b>каталог</b> — продукция РЕКС</div>
    <h1>%s позиций для гидроизоляции, ремонта и защиты бетона</h1>
    <p>Полный ассортимент: обмазочные и проникающие системы, инъекционные составы, гидрошпонки,
    ремонтные смеси, промышленные полы, клеи и анкеры. Цены за единицу с НДС, минимальный
    заказ — %s ₽.</p>
    <div class="pagehead__meta"><span>направлений: <b>6</b></span><span>позиций: <b>%s</b></span>
    <span>документы: <b>на каждую партию</b></span></div>
  </div>
  <div class="catrows" style="margin-top:8px">%s</div>
</div>
%s
<div class="wrap"><div class="prose" style="padding:10px 0 30px">%s</div></div>
""" % (shell.crumbs([("/shop", "Каталог")]), len(m.products),
       "{:,}".format(C.MIN_ORDER).replace(",", " "), len(m.products), "".join(rows),
       '<div class="wrap">%s</div>' % shell.visit_cta(), content.SHOP_BODY)
    body += shell.cta_band()
    ld = schema.dumps(
        schema.breadcrumbs([("/shop", "Каталог")]),
        schema.collection("/shop", "Каталог продукции РЕКС",
                          "Полный ассортимент инженерной химии РЕКС: %d позиций." % len(m.products),
                          [("/" + g[0], g[1]) for g in C.GROUPS]))
    return shell.page("/shop", "Каталог продукции РЕКС — %d позиций для бетона" % len(m.products),
                      trim_desc("Каталог инженерной химии РЕКС: гидроизоляция бетона, ремонтные "
                                "составы, промышленные полы, защита, клеи и анкеры. Официальный "
                                "дилер: цены, технические описания, документы, выезд инженера."),
                      body, ld=ld)


def category(slug):
    m = model()
    c = m.cat_by[slug]
    prods = m.products_in(slug)
    ct = content.category_text(c)
    subs = [s for s in m.children.get(c["id"], []) if m.count(s["slug"])]
    chips = ""
    if subs:
        chips = '<div class="chips">' + "".join(
            '<a class="chip" href="/%s">%s <b>%d</b></a>' % (s["slug"], esc(s["name"]), m.count(s["slug"]))
            for s in subs) + "</div>"
    grp = next((g for g in C.GROUPS if g[0] == slug), None)
    if not grp:
        parent = m.parents(c)[0] if m.parents(c) else None
        grp = next((g for g in C.GROUPS if parent and g[0] == parent["slug"]), ("", c["name"], "", ""))
    cards = "".join(card(p) for p in prods)
    crumbs = [(u, n) for u, n in []]
    chain = [("/" + g[0], g[1]) for g in C.GROUPS if g[0] in [x["slug"] for x in m.parents(c)] + [slug]]
    body = """
%s
<div class="wrap">
  <div class="pagehead">
    <div class="eyebrow"><b>раздел</b> — %s</div>
    <h1>%s</h1>
    <p>%s</p>
    <div class="pagehead__meta"><span>позиций: <b>%d</b></span><span>артикулы: <b>в наличии</b></span>
    <span>документы: <b>сертификаты и паспорта</b></span></div>
  </div>
  <div style="padding:26px 0 6px">%s<div class="toolbar"><span class="toolbar__count">%d позиций</span>
  <span class="toolbar__sp"></span><span class="toolbar__count" style="text-transform:none">Цены с НДС · прайс 10.09.2026</span></div></div>
  <div class="cards">%s</div>
</div>
%s
<section class="sec sec--tight"><div class="wrap split">
  <div class="prose">%s</div>
  <div><div class="side-card"><h3>Подбор под узел</h3>
    <p class="muted" style="font-size:14px">Опишите конструкцию и условия — инженер предложит
    систему и посчитает расход с ценой.</p>
    <a class="btn btn--acc btn--full" href="#zapros" style="margin-top:14px">Запросить подбор</a></div>
    <div class="side-card" style="margin-top:16px"><h3>Другие разделы</h3><ul>%s</ul></div>
  </div>
</div></section>
""" % (shell.crumbs([("/shop", "Каталог")] + chain), esc(grp[1]), esc(c["name"]), esc(ct["lead"]),
       len(prods), chips, len(prods), cards,
       visit_block([slug] + [x["slug"] for x in m.parents(c)]), ct["body"],
       "".join('<li><a href="/%s">%s <span class="muted">· %d</span></a></li>'
               % (g[0], esc(g[1]), m.count(g[0])) for g in C.GROUPS if g[0] != slug))
    body += shell.cta_band("Подобрать материал из раздела «%s»" % c["name"],
                           "Пришлите задание или чертёж узла — вернёмся с системой материалов, "
                           "расходом и ценой в течение рабочего дня.")
    body += shell.lead_form()
    title = cat_title(c)
    desc = trim_desc(c["meta_desc"] or ct["lead"])
    ld = schema.dumps(
        schema.breadcrumbs([("/shop", "Каталог")] + chain),
        schema.collection("/" + slug, c["name"], trim_desc(ct["lead"]),
                          [("/" + p["slug"], p["name"]) for p in prods]))
    return shell.page("/" + slug, title, desc, body, ld=ld,
                      no_visit=not _visit_ok([slug] + [x["slug"] for x in m.parents(c)]))


# ------------------------------------------------------------------ товар
def nice_pack(s):
    """«комплект 35кг.(меш. 25 +канистра 10 кг)» -> «Комплект 35 кг. (меш. 25 + канистра 10 кг)»."""
    s = (s or "").strip()
    if not s:
        return s
    s = re.sub(r"(\d)(мл|мм|кг|л)\b", r"\1 \2", s)
    s = s.replace(".(", ". (").replace("+", "+ ")
    s = re.sub(r"\+\s+(?=\d)", "+", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s[0].upper() + s[1:]
    s = re.sub(r"^Меш\.\s*", "Мешок ", s)
    s = re.sub(r"^Мет\.\s*ведро\s*", "Мет. ведро ", s)
    s = re.sub(r"^Пласт\.\s*ведро\s*", "Пласт. ведро ", s)
    s = re.sub(r"^Кан\.\s*", "Канистра ", s)
    return s


def product(p):
    m = model()
    ct = content.product_text(p)
    cats = [m.cat_by[s] for s in p["cats"] if s in m.cat_by]
    path = []
    if cats:
        best = max(cats, key=lambda c: len(m.parents(c)))
        path = m.parents(best) + [best]
    main = path[0] if path else None
    chain = [("/" + c["slug"], c["name"]) for c in path]
    similar = [x for x in m.products_in(main["slug"]) if x["slug"] != p["slug"]][:4] if main else []
    specs = [("grid", "Тип", ct["kind"]), ("doc", "Артикул", p["sku"] or "—"),
             ("layers", "Раздел", main["name"] if main else "—")]
    specs.append(("package", "Фасовка", nice_pack(p.get("pack")) or
                  art.PACK_BY_KIND.get(art.kind_of(p), "по запросу").split("·")[-1].strip()))
    specs.append(("warehouse", "Наличие", "со склада в Москве"))
    specs.append(("seal", "Документы", "паспорт качества, сертификат"))
    spec_html = "".join('<div class="spec__row"><dt>%s %s</dt><dd>%s</dd></div>'
                        % (art.icon(i), esc(k), esc(v)) for i, k, v in specs)
    side_spec = "".join('<div class="spec__row"><dt>%s %s</dt><dd>%s</dd></div>'
                        % (art.icon(i), esc(k), esc(v)) for i, k, v in specs[3:])
    ph = images.product(p)
    if ph:
        media = ('<div class="prod__duo"><div class="prod__photo">%s</div>'
                 '<div class="prod__scheme">%s</div></div>'
                 % (images.tag(ph, esc(p["name"]), w=900, h=900, eager=True), art.plate(p)))
        cap = "Фото упаковки · схема тары"
    else:
        media = art.plate(p)
        cap = "Техпаспорт · %s" % esc(art.kind_of(p).upper())
    body = """
%s
<div class="wrap">
  <div class="prod">
    <div>
      <figure class="prod__media" style="margin:0">
        %s
        <figcaption><span>%s</span><span>арт. %s</span></figcaption>
      </figure>
    </div>
    <div>
      <div class="eyebrow"><b>%s</b></div>
      <h1>%s</h1>
      <p class="prod__lead">%s</p>
      <div class="prod__pricebox">
        %s
        <div class="prod__note">Цена за единицу с НДС · прайс от 10.09.2026 · минимальный заказ %s ₽</div>
      </div>
      <div class="prod__act">
        <a class="btn btn--acc" href="#zapros">Запросить счёт</a>
        <a class="btn btn--ghost" href="mailto:%s?subject=%s">Задать вопрос</a>
      </div>
      <dl class="spec">%s</dl>
    </div>
  </div>
</div>
%s
<section class="sec sec--tight"><div class="wrap split">
  <div class="prose">%s</div>
  <div>
    <div class="side-card"><h3>Наличие и отгрузка</h3>
      <dl style="margin:0">%s</dl></div>
    <div class="side-card" style="margin-top:16px"><h3>Частые вопросы</h3>%s</div>
  </div>
</div></section>
""" % (shell.crumbs([("/shop", "Каталог")] + chain + [("", p["name"])]),
       media, cap, esc(p["sku"]), esc(ct["kind"]), esc(p["name"]),
       esc(ct["lead"]), price_html(p), "{:,}".format(C.MIN_ORDER).replace(",", " "),
       C.EMAIL, esc(p["name"]), spec_html,
       '<div class="wrap">%s</div>' % visit_block(p["cats"]),
       ct["body"], side_spec, faq_block(ct["faq"]))

    if similar:
        body += """
<section class="sec sec--tight" style="background:#e9f4fb"><div class="wrap">
  <div class="sec__head sec__head--one"><div><div class="eyebrow"><b>+</b> — рядом</div>
  <h2>Похожие составы</h2></div></div>
  <div class="cards">%s</div>
</div></section>""" % "".join(card(x) for x in similar)

    body += shell.cta_band("Нужен расчёт по этому составу?",
                           "Подскажем расход на вашу площадь, посчитаем стоимость партии и сроки поставки.")
    body += shell.lead_form()
    title = product_title(p)
    desc = product_desc(p, m, ct)
    pack = nice_pack(p.get("pack")) or ""
    ld = schema.dumps(
        schema.product(p, m.url(p), desc, main["name"] if main else "", pack, ph),
        schema.breadcrumbs([("/shop", "Каталог")] + chain + [("", p["name"])]),
        schema.faq(ct["faq"]))
    og = (C.SITE + "/assets/img/" + ph) if ph else None
    return shell.page(m.url(p), title, desc, body, no_visit=not _visit_ok(p["cats"]),
                      ld=ld, og_image=og)


# ------------------------------------------------------------------ блог
def blog_index():
    m = model()

    def art_card(a):
        cov = images.article(a)
        cover = ('<div class="group__cover">%s</div>'
                 % images.tag(cov, esc(a["title"]), w=760, h=428)) if cov else '<div class="group__cover group__cover--empty"></div>'
        return """
<a class="group group--art" href="/%s">
  %s
  <div class="group__body">
    <div class="group__i">статья · %d симв.</div>
    <h3 style="font-size:17px;margin:8px 0 8px">%s</h3>
    <span class="group__link">Читать %s</span>
  </div>
</a>""" % (a["slug"], cover, a["content_len"], esc(a["title"]), art.icon("arrow"))

    cards = "".join(art_card(a) for a in m.posts)
    body = """
%s
<div class="wrap">
  <div class="pagehead">
    <div class="eyebrow"><b>блог</b> — инженерные разборы</div>
    <h1>Технологии, нормативы и разбор узлов</h1>
    <p>75 статей о гидроизоляции, ремонте и защите бетона: как работают материалы, какие
    ошибки встречаются на объектах и что требуют нормативы.</p>
    <div class="pagehead__meta"><span>статей: <b>%d</b></span><span>разделов: <b>7</b></span></div>
  </div>
  <div class="groups" style="margin:28px 0 10px">%s</div>
</div>
<div class="wrap">%s</div>
""" % (shell.crumbs([("/blog", "Блог")]), len(m.posts), cards, shell.visit_cta())
    body += shell.cta_band()
    ld = schema.dumps(
        schema.breadcrumbs([("/blog", "Блог")]),
        schema.collection("/blog", "Блог РЕКС", "75 технических статей о гидроизоляции, "
                          "ремонте и защите бетона.", [("/" + a["slug"], a["title"]) for a in m.posts]))
    return shell.page("/blog", "Блог РЕКС — гидроизоляция, ремонт и защита бетона",
                      "Технические статьи о гидроизоляции бетона, ремонтных составах, промышленных "
                      "полах и нормативах: технологии, ошибки, разбор узлов.", body, ld=ld)


def _fix_article(html, known):
    html = html.replace('class="article-toc"', 'class="toc"')
    html = re.sub(r"(<h[23][^>]*>)\s*[>›»]\s*", r"\1", html)
    html = html.replace('class="article-note"', 'class="note"')
    html = html.replace('class="article-conclusion"', 'class="note"')
    html = html.replace('class="article-references"', 'class="note"')
    html = re.sub(r'\sstyle="[^"]*"', "", html)

    def fix_link(m):
        href = m.group(1)
        if href.startswith("#") or href.startswith("http") or href.startswith("mailto"):
            return m.group(0)
        clean = href.rstrip("/")
        if clean in known:
            return 'href="%s"' % clean
        return 'href="/shop"'

    html = re.sub(r'href="([^"]+)"', fix_link, html)
    # заголовки без id получают id по номеру
    n = [0]

    def add_id(m):
        n[0] += 1
        return '<%s id="s%d">' % (m.group(1), n[0])

    html = re.sub(r'<h2(?![^>]*id=)', lambda m: '<h2 id="s%d">' % (hash(m.string or "") % 1000), html)
    return html


_REL_STOP = set("""
для при как что это или так его она они был без под над про через между
бетон бетона бетонных конструкций конструкция статья материал материалы
""".split())


def _rel_tokens(s):
    return {w for w in re.findall(r"[а-яёa-z0-9]{4,}", (s or "").lower())
            if w not in _REL_STOP}


def _related_posts(m, a, n=6):
    """Похожие статьи по теме: пересечение ключевых слов + общая рубрика."""
    cur = _rel_tokens(a["slug"].replace("-", " ") + " " + a["title"])
    scored = []
    for x in m.posts:
        if x["slug"] == a["slug"]:
            continue
        t = _rel_tokens(x["slug"].replace("-", " ") + " " + x["title"])
        inter = len(cur & t)
        score = inter / (1.0 + (len(cur | t)) ** 0.5)
        if x.get("category") and x.get("category") == a.get("category"):
            score += 0.08
        if inter == 0:
            score = -1
        scored.append((score, -len(x["title"]), x["slug"], x))
    scored.sort(key=lambda p: (-p[0], p[1], p[2]))
    top = [p[3] for p in scored if p[0] > 0][:n]
    if len(top) < n:  # добираем остальные, чтобы блок не пустел
        rest = [x for x in m.posts if x["slug"] != a["slug"] and x not in top]
        top += rest[:n - len(top)]
    return top


def article(a):
    m = model()
    known = set(["/"] + ["/" + p["slug"] for p in m.products] +
                ["/" + c["slug"] for c in m.cats] +
                ["/" + p["slug"] for p in m.posts] +
                ["/" + c["slug"] for c in m.calcs] +
                ["/blog", "/shop", "/kalkulyatory", "/kontakty", "/politika-konfidencialnosti"] +
                [u for u, _n in C.INFO_PAGES])
    body_html = _fix_article(a["content"], known)
    cov = images.article(a)
    cover_html = ('<img class="art__cover" src="/assets/img/%s" alt="%s" width="760" height="428" '
                  'loading="eager" decoding="async">' % (cov, esc(a["title"]))) if cov else ""
    if '<div class="toc"' not in body_html:
        pass
    related = _related_posts(m, a)
    dt = POST_DATES.get(a["slug"], {})
    pub = dt.get("published", "")
    pub_ru = ("%s.%s.%s" % (pub[8:10], pub[5:7], pub[0:4])) if len(pub) == 10 else ""
    body = """
%s
<div class="wrap">
  <div class="art">
    <div class="art__body">
      <div class="art__head">
        <div class="art__meta"><span>%s</span><a href="/blog">Блог</a>%s<span>%d симв.</span></div>
        <h1>%s</h1>
        %s
      </div>
      <div class="prose">%s</div>
    </div>
    <aside class="art__side">
      <div class="side-card side-card--dark">
        <h3>Подбор материала</h3>
        <p>Опишите узел и условия эксплуатации — инженер предложит систему и посчитает расход.</p>
        <a class="btn btn--acc btn--full" href="#zapros" style="margin-top:14px">Запросить расчёт</a>
      </div>
      <div class="side-card"><h3>Выезд на объект</h3>
        <p style="font-size:13.5px;color:#456a83">Москва и Подмосковье — бесплатно: осмотр узла,
        замер и подбор системы на месте.</p>
        <a class="btn btn--ghost btn--full" href="%s" style="margin-top:14px">%s %s</a>
      </div>
      <div class="side-card"><h3>Ещё по теме</h3><ul>%s</ul></div>
      <div class="side-card"><h3>Разделы каталога</h3><ul>%s</ul></div>
    </aside>
  </div>
</div>
""" % (shell.crumbs([("/blog", "Блог"), ("", a["title"])]), "статья",
       ('<time datetime="%s">%s</time>' % (pub, pub_ru)) if pub else "",
       a["content_len"],
       esc(a["title"]), cover_html, body_html, C.VISIT_URL, art.icon("helmet"),
       esc(C.VISIT_SHORT),
       "".join('<li><a href="/%s">%s</a></li>' % (x["slug"], esc(x["title"])) for x in related),
       "".join('<li><a href="/%s">%s</a></li>' % (g[0], esc(g[1])) for g in C.GROUPS))
    body += '<div class="wrap">%s</div>' % shell.visit_cta()
    body += shell.cta_band()
    title = a.get("meta_title") or (a["title"] + " | РЕКС")
    if len(title) > 70:
        title = (a["title"][:52].rstrip(" ,;—-") + " | РЕКС") if len(a["title"]) > 52 \
            else (a["title"] + " | РЕКС")
    desc = trim_desc(a.get("meta_desc") or re.sub(r"<[^>]+>", " ", body_html)[:170])
    ld = schema.dumps(
        schema.article(a, "/" + a["slug"], cov, pub, dt.get("modified", "")),
        schema.breadcrumbs([("/blog", "Блог"), ("", a["title"])]))
    og = (C.SITE + "/assets/img/" + cov) if cov else None
    return shell.page("/" + a["slug"], title, desc, body, ld=ld, og_image=og)


# ------------------------------------------------------------------ калькуляторы
def calc_icon(slug, title):
    t = (slug + " " + title).lower()
    if "stoimost" in t:
        return "tag"
    if ("shov" in t or "germetik" in t or "shponk" in t or "treshchin" in t
            or "profilya" in t or "tolshchin" in t):
        return "ruler"
    if "anker" in t or "nesushch" in t:
        return "bolt"
    if ("poliuretan" in t or "epoksidn" in t or "nalivn" in t or "polim" in t
            or "rovnitel" in t):
        return "layers"
    if "kley" in t or "adgez" in t or "shtukaturn" in t:
        return "glue"
    if "ognezashchit" in t or "antikor" in t or "zashchit" in t or "zashhit" in t:
        return "shield"
    if ("gidroizolyac" in t or "pronik" in t or "otsech" in t or "geomembran" in t
            or "plomb" in t or "grunt" in t or "usilen" in t):
        return "drop"
    if "remont" in t or "torkret" in t or "podliv" in t:
        return "trowel"
    return "calc"


def calc_index():
    m = model()
    cards = []
    for i, c in enumerate(m.calcs):
        d = CALCS.get(c["slug"]) or {}
        lead = (d.get("intro") or "Онлайн-расчёт по нормативным зависимостям").split(". ")[0]
        cards.append("""
<a class="calccard" href="/%s">
  <div class="calccard__icon">%s</div>
  <div class="calccard__i">%02d / расчёт</div>
  <h3>%s</h3>
  <p>%s.</p>
  <span class="calccard__go">Открыть калькулятор %s</span>
</a>""" % (c["slug"], art.icon(calc_icon(c["slug"], c["title"])), i + 1,
           esc(d.get("title") or c["title"]), esc(lead), art.icon("arrow")))
    body = """
%s
<div class="wrap">
  <div class="pagehead">
    <div class="eyebrow"><b>инструменты</b> — расчёты</div>
    <h1>Калькуляторы расхода материалов РЕКС</h1>
    <p>Расход обмазочной и проникающей гидроизоляции, объём ремонтного состава, толщина
    защитного слоя, расход клея и ровнителя — по нормативным зависимостям. Считают на лету
    и сразу показывают, сколько упаковок нужно купить.</p>
    <div class="pagehead__meta"><span>калькуляторов: <b>%d</b></span><span>формат: <b>онлайн</b></span>
    <span>результат: <b>материал и стоимость</b></span></div>
  </div>
  <div class="calcgrid" style="margin:26px 0 10px">%s</div>
</div>
<div class="wrap">%s</div>
""" % (shell.crumbs([("/kalkulyatory", "Калькуляторы")]), len(m.calcs), "".join(cards),
       shell.visit_cta())
    body += shell.cta_band("Нужен расчёт под проект?",
                           "Посчитаем расход и стоимость материалов по вашему заданию — с учётом запаса на потери.")
    ld = schema.dumps(
        schema.breadcrumbs([("/kalkulyatory", "Калькуляторы")]),
        schema.collection("/kalkulyatory", "Калькуляторы расхода материалов РЕКС",
                          "Онлайн-калькуляторы расхода гидроизоляции, ремонтных составов, клея "
                          "и защитных покрытий.", [("/" + c["slug"], c["title"]) for c in m.calcs]))
    return shell.page("/kalkulyatory", "Калькуляторы расхода материалов РЕКС — %d расчётов" % len(m.calcs),
                      "Онлайн-калькуляторы расхода гидроизоляции, ремонтных составов, клея, "
                      "ровнителя и защитных покрытий по нормативным зависимостям: результат "
                      "в килограммах, упаковках и рублях.", body, ld=ld)


CALCS = {
    "kalkulyator-rashoda-obmazochnoj-gidroizolyacii": dict(
        title="Расчёт расхода обмазочной гидроизоляции",
        intro="Обмазочную мембрану считают по площади и числу слоёв с коэффициентом потерь. "
              "Для ровного основания потери — 5–7 %, для шероховатого и сложного — до 15 %.",
        fields=[("Площадь поверхности, м²", "area", 50), ("Слоёв", "layers", 2),
                ("Расход на слой, кг/м²", "rate", 1.6), ("Коэффициент потерь", "loss", 1.1)],
        formula="kg = area × layers × rate × loss",
        unit="кг", sub="сухой смеси на всю площадь", product="reks-elast-110"),
    "kalkulyator-rashoda-pronikayushchej-gidroizolyacii": dict(
        title="Расчёт расхода проникающей гидроизоляции",
        intro="Проникающий состав наносят в 2 слоя; норма зависит от пористости бетона — "
              "для плотного бетона от 0,8 кг/м², для пористой поверхности — до 2,0 кг/м².",
        fields=[("Площадь, м²", "area", 80), ("Слоёв", "layers", 2),
                ("Расход на слой, кг/м²", "rate", 1.0), ("Коэффициент потерь", "loss", 1.1)],
        formula="kg = area × layers × rate × loss",
        unit="кг", sub="сухой смеси", product="reks-super"),
    "kalkulyator-obyoma-remontnogo-sostava": dict(
        title="Калькулятор объёма ремонтного состава",
        intro="Объём ремонта считают по площади и средней глубине дефекта: объём = площадь × "
              "толщина. Расход сухой смеси на 1 м³ готового раствора — около 1,7–1,9 т.",
        fields=[("Площадь ремонта, м²", "area", 20), ("Средняя толщина, мм", "thick", 30),
                ("Расход смеси, кг/м² на 1 мм", "rate", 1.8)],
        formula="kg = area × thick × rate",
        unit="кг", sub="сухой смеси", product="reks-strukto-100"),
    "kalkulyator-rashoda-rovnitelya-dlya-pola": dict(
        title="Расчёт расхода ровнителя для пола",
        intro="Расход ровнителя пропорционален толщине слоя. Для самовыравнивающихся составов "
              "расход на 1 мм слоя обычно 1,5–1,8 кг/м².",
        fields=[("Площадь пола, м²", "area", 120), ("Толщина слоя, мм", "thick", 5),
                ("Расход на 1 мм, кг/м²", "rate", 1.6)],
        formula="kg = area × thick × rate",
        unit="кг", sub="сухой смеси", product="reks-53s"),
    "kalkulyator-rashoda-plitochnogo-kleya": dict(
        title="Расчёт расхода плиточного клея",
        intro="Расход клея зависит от размера плитки и типа гребёнки: для плитки 300×300 — "
              "около 3 кг/м², для крупноформатного керамогранита — 6–8 кг/м².",
        fields=[("Площадь облицовки, м²", "area", 40), ("Расход клея, кг/м²", "rate", 4.0),
                ("Запас, %", "loss", 10)],
        formula="kg = area × rate × (1 + loss/100)",
        unit="кг", sub="сухой смеси", product="reks-klej-pljus"),
    "kalkulyator-rashoda-gidroplomby": dict(
        title="Расчёт расхода гидропломбы",
        intro="Расход гидропломбы считают по объёму выработки: на 1 дм³ полости требуется "
              "около 1,6–1,8 кг сухой смеси.",
        fields=[("Объём выработки, дм³", "vol", 5), ("Расход, кг/дм³", "rate", 1.7)],
        formula="kg = vol × rate",
        unit="кг", sub="сухой смеси", product="reks-plag-30"),
    "kalkulyator-dliny-gidroshponki": dict(
        title="Расчёт длины гидрошпонки",
        intro="Длину профиля считают по периметру шва с запасом на нахлёст и разделку "
              "примыканий.",
        fields=[("Длина шва, м", "len", 60), ("Запас на нахлёст, %", "loss", 8)],
        formula="m = len × (1 + loss/100)",
        unit="м", sub="профиля по длине шва"),
    "kalkulyator-rashoda-inekcionnogo-sostava-dlya-treshchin": dict(
        title="Расчёт инъекционного состава для трещин",
        intro="Объём инъекции считают по раскрытию и глубине трещины: V = ширина × глубина × длина "
              "с коэффициентом заполнения.",
        fields=[("Длина трещины, м", "len", 10), ("Раскрытие, мм", "width", 0.5),
                ("Глубина, мм", "depth", 100), ("Коэффициент заполнения", "k", 1.3)],
        formula="l = len × width × depth / 1000 × k",
        unit="л", sub="инъекционного состава", product="hacut-kat"),
    "kalkulyator-rashoda-zashhitnogo-pokrytiya-dlya-betona": dict(
        title="Расчёт расхода защитного покрытия",
        intro="Защитный состав наносят в два слоя; расход зависит от пористости основания "
              "и типа покрытия.",
        fields=[("Площадь, м²", "area", 200), ("Слоёв", "layers", 2),
                ("Расход на слой, кг/м²", "rate", 0.35)],
        formula="kg = area × layers × rate",
        unit="кг", sub="материала", product="reks-protekt"),
    "kalkulyator-nesushchej-sposobnosti-himicheskogo-ankera": dict(
        title="Расчёт несущей способности химического анкера",
        intro="Ориентировочная несущая способность анкера зависит от диаметра, глубины "
              "анкеровки и прочности бетона.",
        fields=[("Диаметр шпильки, мм", "d", 12), ("Глубина анкеровки, мм", "h", 110),
                ("Класс бетона B", "b", 25)],
        formula="N = 0.0022 × d × h × (b/25)^0.5",
        unit="кН", sub="ориентировочная нагрузка на анкер", product="reks-fiks-epo-tiks"),
    "kalkulyator-rasstoyaniya-mezhdu-deformacionnymi-shvami": dict(
        title="Расстояние между деформационными швами",
        intro="Швы нарезают через 24–36 толщин плиты: чем тоньше плита, тем чаще шов. "
              "Для плит на грунте обычно принимают коэффициент 30.",
        fields=[("Толщина плиты, мм", "h", 200), ("Коэффициент, × толщин", "k", 30)],
        formula="m = h × k / 1000",
        unit="м", sub="шаг шва"),
    "kalkulyator-tolshchiny-zashchitnogo-sloya-betona": dict(
        title="Толщина защитного слоя бетона по СП 63",
        intro="Минимальный защитный слой берут по таблицам СП 63.13330 в зависимости от условий "
              "эксплуатации и диаметра арматуры, затем прибавляют технологическую поправку.",
        fields=[("Слой по таблице СП 63, мм", "base", 25), ("Поправка на условия, мм", "add", 5)],
        formula="mm = base + add",
        unit="мм", sub="защитного слоя до арматуры"),
    "kalkulyator-rashoda-sostava-dlya-usileniya-gruntov": dict(
        title="Расход состава для усиления грунтов",
        intro="Расход считают по объёму укрепляемого массива, пористости грунта и плотности "
              "инъекционного раствора.",
        fields=[("Объём массива, м³", "v", 100), ("Пористость (доля пор)", "pore", 0.3),
                ("Плотность состава, кг/м³", "dens", 1100)],
        formula="kg = v × pore × dens",
        unit="кг", sub="инъекционного состава", product="hasoil-gelakril"),
    "kalkulyator-rashoda-epoksidnoj-shpatlyovki": dict(
        title="Расход эпоксидной шпатлёвки",
        intro="Шпатлёвка выравнивает основание тонким слоем: расход зависит от толщины слоя "
              "и шероховатости поверхности.",
        fields=[("Площадь выравнивания, м²", "area", 20), ("Толщина слоя, мм", "thick", 2),
                ("Расход на 1 мм, кг/м²", "rate", 1.5)],
        formula="kg = area × thick × rate",
        unit="кг", sub="готовой шпатлёвки"),
    "kalkulyator-rashoda-nabuhayushchego-profilya": dict(
        title="Расход набухающего профиля",
        intro="Профиль укладывают по всей длине шва с запасом на нахлёст и заводку в бетон.",
        fields=[("Длина шва, м", "len", 60), ("Запас на нахлёст, %", "loss", 10)],
        formula="m = len × (1 + loss/100)",
        unit="м", sub="профиля", product="reks-svello-20h4-mm", pack_qty=10),
    "kalkulyator-stoimosti-ustrojstva-polimernogo-pola": dict(
        title="Стоимость устройства полимерного пола",
        intro="Стоимость считают по площади и цене квадратного метра системы «под ключ»: "
              "подготовка основания, праймер, основной слой, финиш.",
        fields=[("Площадь пола, м²", "area", 200), ("Цена системы, ₽/м²", "price", 1100)],
        formula="rub = area × price",
        unit="₽", sub="стоимость устройства пола"),
    "kalkulyator-stoimosti-remonta-betonnogo-pola": dict(
        title="Стоимость ремонта бетонного пола",
        intro="Ремонт считают по площади дефектных участков и цене работ с материалом.",
        fields=[("Площадь ремонта, м²", "area", 100), ("Цена ремонта, ₽/м²", "price", 650)],
        formula="rub = area × price",
        unit="₽", sub="стоимость ремонта"),
    "kalkulyator-stoimosti-gidroizolyacii-fundamenta": dict(
        title="Стоимость гидроизоляции фундамента",
        intro="Стоимость зависит от площади обработки и типа системы: обмазочная, проникающая "
              "или оклеечная.",
        fields=[("Площадь обработки, м²", "area", 150), ("Цена системы, ₽/м²", "price", 700)],
        formula="rub = area × price",
        unit="₽", sub="стоимость гидроизоляции"),
    "kalkulyator-rashoda-ognezashchitnogo-sostava": dict(
        title="Расход огнезащитного состава",
        intro="Расход зависит от требуемого предела огнестойкости и толщины слоя: для R90 "
              "обычно принимают 1,2–1,6 кг/м² на слой.",
        fields=[("Площадь конструкции, м²", "area", 100), ("Расход на слой, кг/м²", "rate", 1.4),
                ("Слоёв", "layers", 2)],
        formula="kg = area × rate × layers",
        unit="кг", sub="огнезащитного состава"),
    "kalkulyator-rashoda-shtukaturno-kleevoj-smesi": dict(
        title="Расход штукатурно-клеевой смеси для СФТК",
        intro="Смесь наносят на армирующую сетку и на утеплитель: суммарный расход по системе "
              "обычно 5–6 кг/м².",
        fields=[("Площадь фасада, м²", "area", 80), ("Расход смеси, кг/м²", "rate", 5.0)],
        formula="kg = area × rate",
        unit="кг", sub="сухой смеси", product="reks-klej-pljus"),
    "kalkulyator-rashoda-torkret-smesi": dict(
        title="Расход торкрет-смеси",
        intro="Торкретирование идёт слоями по 30–70 мм: расход считают по толщине слоя "
              "и площади конструкции.",
        fields=[("Площадь конструкции, м²", "area", 60), ("Толщина слоя, мм", "thick", 50),
                ("Расход на 1 мм, кг/м²", "rate", 2.0)],
        formula="kg = area × thick × rate",
        unit="кг", sub="сухой смеси", product="reks-torkret"),
    "kalkulyator-rashoda-otsechnoj-gidroizolyacii": dict(
        title="Расход отсечной гидроизоляции",
        intro="Отсечку делают через систему отверстий по толщине стены: количество отверстий "
              "зависит от шага и толщины кладки.",
        fields=[("Длина стены, м", "len", 12), ("Толщина стены, м", "thick", 0.4),
                ("Шаг отверстий, м", "step", 0.3), ("Расход на отверстие, л", "dose", 1.5)],
        formula="l = len × thick / step × dose",
        unit="л", sub="инъекционной жидкости", product="reks-anti-kapillyar", pack_qty=20),
    "kalkulyator-rashoda-germetika-dlya-shvov": dict(
        title="Расход герметика для деформационных швов",
        intro="Объём герметика равен объёму полости шва: ширина × глубина × длина, с поправкой "
              "на плотность материала.",
        fields=[("Длина шва, м", "len", 60), ("Ширина шва, мм", "width", 20),
                ("Глубина заливки, мм", "depth", 15), ("Плотность, г/см³", "dens", 1.4)],
        formula="kg = len × width × depth × dens / 1000",
        unit="кг", sub="герметика", product="hacut-fleks-snv"),
    "kalkulyator-rashoda-geomembrany": dict(
        title="Расход геомембраны с учётом нахлёстов",
        intro="К площади поверхности прибавляют запас на нахлёсты и подвороты: обычно 8–12 %.",
        fields=[("Площадь поверхности, м²", "area", 500), ("Нахлёсты и подвороты, %", "overlap", 10)],
        formula="m2 = area × (1 + overlap/100)",
        unit="м²", sub="полотна с запасом"),
    "kalkulyator-rashoda-antikorrozionnogo-prajmera": dict(
        title="Расход антикоррозионного праймера",
        intro="Праймер наносят на арматуру и закладные в два слоя: расход зависит от профиля "
              "поверхности металла.",
        fields=[("Площадь обработки, м²", "area", 200), ("Расход на слой, кг/м²", "rate", 0.2),
                ("Слоёв", "layers", 2)],
        formula="kg = area × rate × layers",
        unit="кг", sub="праймера", product="reks-prajmer-antikor"),
    "kalkulyator-rashoda-poliuretanovogo-pokrytiya": dict(
        title="Расход полиуретанового покрытия",
        intro="Полиуретановое покрытие наносят в два слоя: расход зависит от пористости "
              "основания и требуемой толщины.",
        fields=[("Площадь, м²", "area", 300), ("Расход на слой, кг/м²", "rate", 0.6),
                ("Слоёв", "layers", 2)],
        formula="kg = area × rate × layers",
        unit="кг", sub="покрытия", product="severus-tikso"),
    "kalkulyator-rashoda-epoksidnogo-nalivnogo-pola": dict(
        title="Расход эпоксидного наливного пола",
        intro="Наливной пол считают по толщине слоя: для эпоксидных систем расход на 1 мм "
              "составляет 1,4–1,6 кг/м².",
        fields=[("Площадь пола, м²", "area", 200), ("Толщина покрытия, мм", "thick", 3),
                ("Расход на 1 мм, кг/м²", "rate", 1.5)],
        formula="kg = area × thick × rate",
        unit="кг", sub="эпоксидной системы", product="reks-epo-top"),
    "kalkulyator-rashoda-montazhnogo-kleya-dlya-blokov": dict(
        title="Расход монтажного клея для кладки блоков",
        intro="Тонкошовная кладка: расход клея зависит от толщины шва и геометрии блока.",
        fields=[("Площадь кладки, м²", "area", 50), ("Толщина шва, мм", "thick", 3),
                ("Расход на 1 мм, кг/м²", "rate", 1.6)],
        formula="kg = area × thick × rate",
        unit="кг", sub="клеевой смеси", product="reks-klej-pljus"),
    "kalkulyator-rashoda-podlivochnogo-sostava": dict(
        title="Расход подливочного состава",
        intro="Подливку считают по площади опирания и толщине слоя: расход на 1 мм слоя — "
              "около 1,9 кг/м².",
        fields=[("Площадь подливки, м²", "area", 10), ("Толщина слоя, мм", "thick", 30),
                ("Расход на 1 мм, кг/м²", "rate", 1.9)],
        formula="kg = area × thick × rate",
        unit="кг", sub="сухой смеси", product="reks-litoj"),
    "kalkulyator-rashoda-adgezionnogo-sostava": dict(
        title="Расход адгезионного состава",
        intro="Мост сцепления наносят тонким слоем на основание: расход зависит от пористости "
              "бетона и способа нанесения.",
        fields=[("Площадь обработки, м²", "area", 50), ("Расход, кг/м²", "rate", 0.5)],
        formula="kg = area × rate",
        unit="кг", sub="адгезионного состава", product="reks-epo-uni-shot-long"),
}


def _pack_qty(prod, unit):
    """Сколько единиц в упаковке по тексту фасовки («меш. 25 кг» -> 25)."""
    pack = (prod.get("pack") or "").lower().replace(",", ".")
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*(кг|л|п\.?\s?м)", pack)
    if not m2:
        return None
    return float(m2.group(1))


def _num(v):
    v = float(v)
    return ("%d" % v) if v.is_integer() else ("%.1f" % v).replace(".", ",")


def calc_page(c):
    m = model()
    d = CALCS.get(c["slug"])
    if not d:
        d = dict(title=c["title"],
                 intro="Калькулятор считает расход материала по площади и нормативной норме.",
                 fields=[("Площадь, м²", "area", 50), ("Норма расхода, кг/м²", "rate", 1.5),
                         ("Коэффициент потерь", "loss", 1.1)],
                 formula="kg = area × rate × loss", unit="кг", sub="материала")
    prod = m.by_slug.get(d.get("product") or "")
    pack_qty = d.get("pack_qty")
    if pack_qty is None and prod:
        pack_qty = _pack_qty(prod, d["unit"])
    price = (prod or {}).get("price")
    fields = "".join("""
      <div class="field"><label for="f-%s">%s</label>
        <input id="f-%s" data-calc="%s" type="number" step="0.1" inputmode="decimal" value="%s"></div>""" % (
        k, esc(lbl), k, k, v) for lbl, k, v in d["fields"])
    rows = []
    if pack_qty:
        rows.append('<li><span>упаковок по %s %s</span><b id="calcPacks">—</b></li>'
                    % (_num(pack_qty), esc(d["unit"])))
    if price:
        rows.append('<li><span>стоимость партии</span><b id="calcCost">—</b></li>')
    if prod:
        rows.append('<li><span>материал</span><b><a href="/%s">%s</a></b></li>'
                    % (prod["slug"], esc(prod["name"])))
    elif d["unit"] == "₽":
        rows.append('<li><span>в расчёте</span><b>материалы и работы</b></li>')
    else:
        rows.append('<li><span>единица результата</span><b>%s</b></li>' % esc(d["unit"]))
    need = ""
    rel = []
    if prod:
        key = content.cluster_of(prod)[0]
        if key != "generic":
            same = [x for x in m.products if x["slug"] != prod["slug"] and x["price"]
                    and content.cluster_of(x)[0] == key]
        else:
            same = [x for x in m.products_in(prod["cats"][-1])
                    if x["slug"] != prod["slug"] and x["price"]]
        rel = ([prod] + same)[:3]
        if len(rel) < 2:
            rel = []
    if rel:
        rows_need = "".join("""
<a class="needrow" href="/%s">
  <span class="needrow__kind">%s</span>
  <span class="needrow__t"><b>%s</b><small>%s</small></span>
  <span class="needrow__p">%s</span>
  <span class="needrow__go">%s</span>
</a>""" % (x["slug"], esc(content.cluster_of(x)[1]["kind"]), esc(x["name"]),
           esc(nice_pack(x.get("pack")) or "фасовка по запросу"),
           money(x["price"]) if x["price"] else "по запросу", art.icon("arrow")) for x in rel)
        need = """
<section class="sec sec--tight"><div class="wrap">
  <div class="sec__head"><div><div class="eyebrow"><b>+</b> — материал</div>
    <h2>Что потребуется по этому расчёту</h2></div>
    <div class="sec__lead">Цены за упаковку с НДС по прайсу от 10 сентября 2026 г.
    Точную фасовку и расход уточняйте в техническом описании.</div></div>
  <div class="needlist">%s</div>
</div></section>""" % rows_need
    others = "".join('<a class="callink" href="/%s">%s %s</a>' % (
        x["slug"], esc(re.sub(r"^(Калькулятор|Расчёт)\s+", "", x["title"]).lower()),
        art.icon("arrow")) for x in m.calcs if x["slug"] != c["slug"])
    body = """
%s
<div class="wrap">
  <div class="pagehead">
    <div class="eyebrow"><b>калькулятор</b> — расчёт</div>
    <h1>%s</h1>
    <p>%s</p>
    <div class="pagehead__meta"><span>результат: <b>%s</b></span>
    <span>расчёт: <b>мгновенный</b></span><span>формула: <b>%s</b></span></div>
  </div>
  <div class="calcwrap">
    <div class="calc" id="calc" data-formula="%s" data-unit="%s" data-pack="%s" data-price="%s">
      <div class="calc__head"><span>Исходные данные</span><b>считается автоматически</b></div>
      <div class="calc__body">
        <div class="calc__grid">%s</div>
        <div class="calc__hint">Меняйте значения — результат и стоимость пересчитываются сразу.</div>
        <div class="calc__action">
          <button class="btn btn--acc" id="calcBtn">Пересчитать</button>
          <span class="note-inline">данные не отправляются на сервер</span>
        </div>
      </div>
    </div>
    <div class="calc__out">
      <div class="calc__label">%s результат</div>
      <div class="calc__big"><span id="calcOut">—</span><i>%s</i></div>
      <div class="calc__sub">%s</div>
      <ul class="calc__rows" id="calcRows">%s</ul>
      <div class="calc__formula"><b>как считаем</b><span id="calcFormula">%s</span></div>
    </div>
  </div>
  <p class="muted" style="font-size:12.5px;margin:14px 0 0">Расчёт ориентировочный: точную норму
  уточняйте в техническом описании материала или у инженера.</p>
  %s
</div>
%s
<section class="sec sec--tight"><div class="wrap">
  <div class="sec__head sec__head--one"><div><div class="eyebrow"><b>%d</b> — ещё расчёты</div>
  <h2>Другие калькуляторы</h2></div></div>
  <div class="callist">%s</div>
</div></section>
""" % (shell.crumbs([("/kalkulyatory", "Калькуляторы"), ("", c["title"])]), esc(d["title"]),
       esc(d["intro"]), esc(d["unit"]), esc(d["formula"]), esc(d["formula"]), esc(d["unit"]),
       _num(pack_qty or 0), price or "", fields, art.icon("calc"), esc(d["unit"]), esc(d["sub"]),
       "".join(rows), esc(d["formula"]), shell.visit_cta(), need, len(m.calcs) - 1, others)
    body += shell.cta_band()
    ld = schema.dumps(schema.breadcrumbs([("/kalkulyatory", "Калькуляторы"), ("", c["title"])]))
    seo_title = d["title"] + " | РЕКС"
    if len(seo_title) < 40:
        seo_title = d["title"] + " — онлайн-калькулятор | РЕКС"
    return shell.page("/" + c["slug"], seo_title, trim_desc(d["intro"]), body, ld=ld)


# ------------------------------------------------------------------ служебные
INFO_TITLE = {
    "dostavka": "Доставка стройхимии РЕКС по Москве и России — сроки и цены",
    "oplata": "Оплата материалов РЕКС — счёт, безнал, работа с НДС",
    "sertifikaty": "Сертификаты и паспорта качества на материалы РЕКС",
    "podbor-analogov": "Подбор аналогов импортной строительной химии — РЕКС",
    "srochnaya-dostavka": "Срочная доставка стройхимии РЕКС со склада — день в день",
    "vyezd-menedzhera-na-obekt": "Выезд специалиста на объект — бесплатно по Москве и МО",
}

PAGE_PICKUP = """
<h2>Самовывоз со складов</h2>
<p>Отгрузка и самовывоз — с двух складов; адреса указаны в действующем прайс-листе:</p>
<ul>
  <li>Московская обл., Наро-Фоминский р-н, д. Софьино, уч. 136;</li>
  <li>Калужская обл., Боровский р-н, д. Добрино, 2-й Восточный проезд, вл. 8.</li>
</ul>
<p>Цены в прайс-листе указаны в рублях с учётом НДС и действуют с 10 сентября 2026 г.
 Для объёмов от 3 и от 10 тонн предусмотрены отдельные уровни цен — их рассчитает менеджер
 по вашей спецификации.</p>
"""


PAGE_VISIT = """<h2>Выезд инженера: что входит</h2>
<p>Специалист приезжает на объект, чтобы не гадать по фотографиям и описанию. В выезд входит:</p>
<ul>
  <li>осмотр конструкции и узла, где работает материал, оценка состояния основания;</li>
  <li>замер площадей, длин швов и объёмов — по факту, а не по проекту;</li>
  <li>подбор системы материалов под условия эксплуатации и технологию работ;</li>
  <li>расчёт расхода и предварительная смета на материалы;</li>
  <li>рекомендации по подготовке основания и последовательности операций.</li>
</ul>
<h2>Куда выезжаем</h2>
<p>По Москве и Московской области выезд <b>бесплатный</b> — в том числе на объекты
в Наро-Фоминске, Подольске, Домодедово, Химках, Мытищах и других городах области.
В другие регионы — по согласованию, стоимость и формат обсуждает менеджер.</p>
<h2>Как заказать</h2>
<p>Позвоните по телефону <a href="%s">%s</a> или оставьте заявку в форме ниже: укажите адрес
объекта, стадию работ и удобное время. Обычно выезд назначают на ближайшие 1–2 рабочих дня.</p>
""" % (C.PHONE_HREF, esc(C.PHONE))


def info(slug):
    title, lead = content.PAGE_TEXTS.get(slug, (slug, ""))
    pg = model().pages.get(slug)
    inner = ""
    if pg and pg.get("content"):
        txt = re.sub(r"\[/?vc_[^\]]*\]", "", pg["content"])
        txt = re.sub(r"<[^>]+>", "\n", txt)
        txt = re.sub(r"&#8212;|&#8211;", "—", txt)
        txt = re.sub(r"\n{2,}", "\n", txt).strip()
        paras = [p.strip() for p in txt.split("\n") if len(p.strip()) > 3]
        inner = "".join("<p>%s</p>" % esc(p) for p in paras[:12])
    if slug == "dostavka":
        inner += PAGE_PICKUP
    if slug == "vyezd-menedzhera-na-obekt":
        inner = PAGE_VISIT
    inner += content.PAGE_BODIES.get(slug, "")
    body = """
%s
<div class="wrap">
  <div class="pagehead"><div class="eyebrow"><b>информация</b></div><h1>%s</h1><p>%s</p></div>
  <div class="split" style="padding:38px 0 20px">
    <div class="prose">%s</div>
    <div>
      <div class="side-card"><h3>Контакты</h3>
        <dl style="margin:0">
          <div class="spec__row"><dt>Телефон</dt><dd><a href="%s">%s</a></dd></div>
          <div class="spec__row"><dt>Почта</dt><dd><a href="mailto:%s">%s</a></dd></div>
          <div class="spec__row"><dt>Склад</dt><dd>%s</dd></div>
          <div class="spec__row"><dt>Адрес (%s)</dt><dd>%s</dd></div>
          <div class="spec__row"><dt>Часы</dt><dd>%s</dd></div>
        </dl>
      </div>
      <div class="side-card side-card--dark" style="margin-top:16px"><h3>Запрос</h3>
        <p>Пришлём прайс, технические описания и расчёт под ваш объём.</p>
        <a class="btn btn--acc btn--full" href="#zapros" style="margin-top:12px">Оставить заявку</a></div>
    </div>
  </div>
</div>
""" % (shell.crumbs([("", title)]), esc(title), esc(lead), inner or "<p>%s</p>" % esc(lead),
       C.PHONE_HREF, esc(C.PHONE), C.EMAIL, C.EMAIL, esc(C.ADDR), esc(C.ADDR_2_LABEL),
       esc(C.ADDR_2), esc(C.HOURS))
    body += ('<div class="wrap">%s</div>' % shell.visit_cta()
             if slug != "vyezd-menedzhera-na-obekt" else "")
    if slug == "vyezd-menedzhera-na-obekt":
        body += shell.lead_form("Вызвать специалиста на объект",
                                "Укажите адрес объекта и стадию работ — согласуем дату выезда "
                                "в течение рабочего дня.")
    else:
        body += shell.lead_form()
    ld = schema.dumps(schema.breadcrumbs([("", title)]))
    seo_title = INFO_TITLE.get(slug) or ("%s — РЕКС" % title)
    return shell.page("/" + slug, seo_title, trim_desc(lead), body, ld=ld)


def contacts():
    body = """
%s
<div class="wrap">
  <div class="pagehead"><div class="eyebrow"><b>контакты</b> · %s</div>
  <h1>Связаться с РЕКС</h1>
  <p>Офис и склад в Наро-Фоминском районе Подмосковья, второй адрес — в Феодосии.
  Отгрузка по России и в страны ЕАЭС. Инженер ответит на технические вопросы, поможет собрать
  систему материалов под объект и выедет на площадку в Москве или Подмосковье.</p></div>
  <div class="split" style="padding:34px 0 10px">
    <div>
      <dl class="spec">
        <div class="spec__row"><dt>%s Телефон</dt><dd><a href="%s"><b>%s</b></a></dd></div>
        <div class="spec__row"><dt>%s E-mail</dt><dd><a href="mailto:%s">%s</a></dd></div>
        <div class="spec__row"><dt>%s Адрес</dt><dd>%s</dd></div>
        <div class="spec__row"><dt>%s Адрес (%s)</dt><dd>%s</dd></div>
        <div class="spec__row"><dt>%s Часы</dt><dd>%s</dd></div>
        <div class="spec__row"><dt>%s Статус</dt><dd>%s</dd></div>
      </dl>
      <div class="note" style="margin-top:22px"><b>Документы</b>
      Паспорта качества и сертификаты — на каждую партию. Для проектных организаций готовим
      технические описания и альбомы узлов.</div>
      <div class="prose" style="margin-top:26px">%s</div>
    </div>
    <div class="card">
      <h3 style="margin-bottom:14px">Заявка на расчёт</h3>
      <form class="form" id="leadForm" novalidate>
        <div class="field"><label for="c-name">Имя</label><input id="c-name" name="name" required></div>
        <div class="field"><label for="c-phone">Телефон</label><input id="c-phone" name="phone" type="tel" required></div>
        <div class="field"><label for="c-msg">Задача</label><textarea id="c-msg" name="msg"></textarea></div>
        <button class="btn btn--acc" type="submit">Отправить</button>
        <div class="form__ok" id="leadOk">Заявка сформирована — откроется почтовый клиент.</div>
      </form>
    </div>
  </div>
</div>
<div class="wrap">%s</div>
""" % (shell.crumbs([("", "Контакты")]), esc(C.DEALER), art.icon("phone"), C.PHONE_HREF,
       esc(C.PHONE), art.icon("mail"), C.EMAIL, C.EMAIL, art.icon("pin"), esc(C.ADDR),
       art.icon("pin"), esc(C.ADDR_2_LABEL), esc(C.ADDR_2),
       art.icon("clock"), esc(C.HOURS), art.icon("seal"), esc(C.DEALER),
       content.KONTAKTY_BODY, shell.visit_cta())
    ld = schema.dumps(schema.breadcrumbs([("", "Контакты")]),
                      schema.collection("/kontakty", "Контакты РЕКС",
                                        "Телефон, почта и адреса официального дилера завода РЕКС."))
    return shell.page("/kontakty", "Контакты РЕКС — адреса в Подмосковье и Феодосии, телефон",
                      "Контакты официального дилера завода РЕКС: телефон +7 (495) 155-01-31, "
                      "почта, адреса в Наро-Фоминске и Феодосии, выезд инженера на объект "
                      "по Москве и Подмосковью.", body, ld=ld)


def policy():
    body = """
%s
<div class="wrap"><div class="pagehead"><div class="eyebrow"><b>документы</b></div>
<h1>Политика обработки персональных данных</h1></div>
<div class="prose" style="padding:34px 0 60px">
<p>Настоящая политика описывает порядок обработки персональных данных, которые пользователь
передаёт через формы на сайте rex.moscow.</p>
<h2>Какие данные собираем</h2>
<p>Имя, телефон, адрес электронной почты и текст задачи — в объёме, который пользователь
указывает добровольно при отправке заявки.</p>
<h2>Зачем</h2>
<p>Чтобы подготовить расчёт, коммерческое предложение, спецификацию и ответить на технический
вопрос. Данные не передаются третьим лицам, кроме случаев, предусмотренных законом.</p>
<h2>Как храним</h2>
<p>Данные хранятся не дольше, чем требуется для обработки обращения. Пользователь может
отозвать согласие, написав на <a href="mailto:%s">%s</a>.</p>
<h2>Cookies</h2>
<p>Сайт использует технические cookies и системы веб-аналитики для оценки удобства интерфейса.</p>
</div></div>
""" % (shell.crumbs([("", "Политика конфиденциальности")]), C.EMAIL, C.EMAIL)
    return shell.page("/politika-konfidencialnosti", "Политика обработки персональных данных | РЕКС",
                      "Политика обработки персональных данных сайта rex.moscow.", body, noindex=True)


def notfound():
    body = """
<div class="wrap"><div class="pagehead" style="padding:90px 0 70px">
  <div class="eyebrow"><b>404</b> — страница не найдена</div>
  <h1>Такой страницы нет</h1>
  <p>Возможно, адрес изменился или страница была перемещена. Начните с каталога —
  в нём %d позиций с описаниями и ценами.</p>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:26px">
    <a class="btn btn--acc" href="/shop">Каталог</a>
    <a class="btn btn--ghost" href="/">На главную</a>
    <a class="btn btn--ghost" href="/kalkulyatory">Калькуляторы</a>
  </div>
</div></div>
""" % len(model().products)
    return shell.head("Страница не найдена | РЕКС", "Страница не найдена", "/404.html", True,
                      canonical=False) + \
        shell.topbar() + shell.header("/") + body + shell.footer()

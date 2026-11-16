# -*- coding: utf-8 -*-
"""Каркас страниц rex.moscow."""
import html
import re

import art
import config as C


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def _nav_active(path, url):
    if url == "/":
        return path == "/"
    return path == url or path.startswith(url + "/")


def head(title, desc, path, noindex=False, extra="", ld="", og_image=None, canonical=True):
    cur = C.SITE + path
    robots = '<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow">'
    can_tag = ('<link rel="canonical" href="%s">' % cur) if canonical else ""
    img = og_image or (C.SITE + "/assets/og.jpg")
    social = """<meta property="og:image" content="%s">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%s">
<meta name="twitter:description" content="%s">
<meta name="twitter:image" content="%s">""" % (esc(img), esc(title), esc(desc), esc(img))
    verify = ""
    if C.VERIFY_YANDEX:
        verify += '<meta name="yandex-verification" content="%s">\n' % esc(C.VERIFY_YANDEX)
    if C.VERIFY_GOOGLE:
        verify += '<meta name="google-site-verification" content="%s">\n' % esc(C.VERIFY_GOOGLE)
    return """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
%s
%s
<meta property="og:type" content="website">
<meta property="og:site_name" content="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
%s
<meta name="theme-color" content="#0088cc">
%s<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch.png">
<link rel="preload" href="/assets/fonts/geologica-700-cyrillic.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/fonts.css">
<link rel="stylesheet" href="/assets/site.css?v=9">
<script defer src="/assets/site.js?v=5"></script>
%s
%s
</head>
<body>""" % (esc(title), esc(desc), robots, can_tag, esc(C.FULL), esc(title), esc(desc),
               cur, social, verify, extra, ld)


def topbar(no_visit=False):
    visit = "" if no_visit else (
        '<a class="topline__visit" href="%s">%s Выезд специалиста — бесплатно</a>'
        '<span class="topline__dot">·</span>' % (C.VISIT_URL, art.icon("helmet")))
    return """
<div class="topline"><div class="wrap">
  <div class="topline__left">%s <span class="topline__dot">·</span> отгрузка со склада по России</div>
  <div class="topline__right">
    %s
    <a href="mailto:%s">%s</a> <span class="topline__dot">·</span> <a href="%s">%s</a>
  </div>
</div></div>""" % (esc(C.DEALER), visit, C.EMAIL, C.EMAIL, C.PHONE_HREF, C.PHONE)


def header(path, no_visit=False):
    links = []
    for url, label in C.NAV:
        cur = ' aria-current="page"' if _nav_active(path, url) else ''
        links.append('<a class="nav__link" href="%s"%s>%s</a>' % (url, cur, label))
    help_items = "".join('<a class="navdrop__link" href="%s">%s</a>' % (url, label)
                         for url, label in C.NAV_HELP)
    drop = ('<div class="navdrop">'
            '<button class="nav__link navdrop__btn" type="button" aria-haspopup="true" '
            'aria-expanded="false">Помощь'
            '<span class="navdrop__caret" aria-hidden="true"></span></button>'
            '<div class="navdrop__panel"><div class="navdrop__title">%s</div>%s</div></div>'
            % (esc(C.NAV_HELP_TITLE), help_items))
    mob = []
    for url, label in C.NAV:
        mob.append('<a class="mob__link" href="%s">%s <small>→</small></a>' % (url, label))
    mob.append('<div class="mob__cap">%s</div>' % esc(C.NAV_HELP_TITLE))
    for url, label in C.NAV_HELP:
        mob.append('<a class="mob__link" href="%s">%s <small>→</small></a>' % (url, label))
    mob_visit = "" if no_visit else (
        '<a class="btn btn--acc" href="%s">%s %s</a>' % (C.VISIT_URL, art.icon("helmet"),
                                                        esc(C.VISIT_SHORT)))
    return """
<header class="hdr"><div class="wrap hdr__in">
  <a class="brand" href="/" aria-label="РЕКС — на главную">
    <span class="brand__mark">%s</span>
    <span class="brand__txt"><span class="brand__name">РЕКС</span><span class="brand__sub">Инженерная химия</span></span>
  </a>
  <nav class="nav" aria-label="Основная навигация">%s%s</nav>
  <span class="hdr__sp"></span>
  <a class="hdr__phone" href="%s">%s<span class="hdr__phoneT"><b>%s</b><span>%s</span></span></a>
  <a class="btn btn--acc hdr__cta" href="#zapros">Запросить прайс</a>
  <button class="burger" id="burger" aria-label="Меню" aria-expanded="false"><span></span><span></span><span></span></button>
</div>
<div class="mob" id="mob"><div class="wrap mob__in">
  %s
  <div class="mob__phone">
    %s
    <a class="btn btn--ghost" href="#zapros">Запросить прайс</a>
    <a class="btn btn--ghost" href="%s">%s</a>
  </div>
</div></div>
</header>""" % (art.mark(), "".join(links), drop, C.PHONE_HREF, art.icon("phone"), C.PHONE,
               esc(C.HOURS), "".join(mob), mob_visit, C.PHONE_HREF, C.PHONE)


def crumbs(items):
    if not items:
        return ""
    out = ['<a href="/">Главная</a>']
    for i, (url, label) in enumerate(items):
        out.append('<span class="sep">/</span>')
        if url and i < len(items) - 1:
            out.append('<a href="%s">%s</a>' % (url, esc(label)))
        else:
            out.append('<span>%s</span>' % esc(label))
    return '<div class="crumbs"><div class="wrap"><div class="crumbs__in">%s</div></div></div>' % "".join(out)


def cta_band(title="Нужен подбор состава под задачу?",
             text="Опишите конструкцию, условия эксплуатации и объём — инженер подберёт систему "
                  "и пришлёт расчёт с ценой в течение рабочего дня.",
             note="Ответ в течение рабочего дня · расчёт с НДС · отгрузка со склада в Москве"):
    return """
<section class="band" id="zapros"><div class="wrap band__in">
  <div><h2>%s</h2><p>%s</p></div>
  <div class="band__act">
    <a class="btn btn--acc btn--lg" href="mailto:%s?subject=Запрос расчёта">Отправить запрос</a>
    <a class="btn btn--ghost btn--lg" href="%s">%s</a>
    <div class="band__note">%s</div>
  </div>
</div></section>""" % (esc(title), esc(text), C.EMAIL, C.PHONE_HREF, esc(C.PHONE), esc(note))


def visit_cta(label=None):
    """Полоса «вызвать специалиста на объект» (на всех страницах, кроме гидрошпонок)."""
    return """
<div class="visit">
  <span class="visit__i">%s</span>
  <span class="visit__t"><b>%s</b><span>%s</span></span>
  <a class="btn btn--acc" href="%s">%s %s</a>
</div>""" % (art.icon("helmet"), esc(C.VISIT_TITLE), esc(C.VISIT_LEAD), C.VISIT_URL,
             esc(label or C.VISIT_TITLE), art.icon("arrow"))


def lead_form(title="Запросить прайс и расчёт", text="Пришлём актуальный прайс-лист, технические "
              "описания и расчёт под ваш объём."):
    return """
<section class="sec sec--tight" id="form"><div class="wrap lead">
  <div>
    <div class="eyebrow"><b>—</b> запрос</div>
    <h2>%s</h2>
    <p class="sec__lead" style="margin-top:14px">%s</p>
    <div class="catrows" style="margin-top:24px;border-top:0">
      <div class="spec"><div class="spec__row"><dt>%s Телефон</dt><dd><a href="%s">%s</a></dd></div>
      <div class="spec__row"><dt>%s Почта</dt><dd><a href="mailto:%s">%s</a></dd></div>
      <div class="spec__row"><dt>%s Склад</dt><dd>%s</dd></div>
      <div class="spec__row"><dt>%s Адрес</dt><dd>%s</dd></div>
      <div class="spec__row"><dt>%s Часы</dt><dd>%s</dd></div></div>
    </div>
  </div>
  <form class="lead__box form" id="leadForm" novalidate>
    <div class="field"><label for="lf-name">Имя</label><input id="lf-name" name="name" required placeholder="Как к вам обращаться"></div>
    <div class="field"><label for="lf-phone">Телефон</label><input id="lf-phone" name="phone" type="tel" required placeholder="+7 (___) ___-__-__"></div>
    <div class="field"><label for="lf-email">E-mail</label><input id="lf-email" name="email" type="email" placeholder="для прайса и КП"></div>
    <div class="field"><label for="lf-msg">Задача</label><textarea id="lf-msg" name="msg" placeholder="Объект, конструкция, объём, сроки"></textarea></div>
    <button class="btn btn--acc" type="submit">Отправить запрос</button>
    <div class="form__note">Нажимая кнопку, вы соглашаетесь с <a href="/politika-konfidencialnosti">политикой обработки данных</a>.</div>
    <div class="form__ok" id="leadOk">Заявка сформирована — откроется почтовый клиент. Если он не открылся, напишите на %s.</div>
  </form>
</div></section>""" % (esc(title), esc(text), art.icon("phone"), C.PHONE_HREF, esc(C.PHONE),
                        art.icon("mail"), C.EMAIL, C.EMAIL,
                        art.icon("warehouse"), esc(C.ADDR),
                        art.icon("pin"), esc(C.ADDR_2),
                        art.icon("clock"), esc(C.HOURS), C.EMAIL)


def analytics():
    """Яндекс.Метрика: выводится, только если в config.py задан METRIKA_ID."""
    try:
        mid = int(C.METRIKA_ID or 0)
    except (TypeError, ValueError):
        mid = 0
    if not mid:
        return ""
    wv = "true" if C.METRIKA_WEBVISOR else "false"
    return """
<!-- Yandex.Metrika counter -->
<script>
window.__ymId = %d;
(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
m[i].l=1*new Date();
for (var j=0;j<document.scripts.length;j++){if(document.scripts[j].src===r){return;}}
k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");
ym(%d,"init",{webvisor:%s,clickmap:true,referrer:document.referrer,url:location.href,accurateTrackBounce:true,trackLinks:true});
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/%d" width="1" height="1" style="position:absolute;left:-9999px" alt=""></div></noscript>
<!-- /Yandex.Metrika counter -->
""" % (mid, mid, wv, mid)


def footer(no_visit=False):
    groups = "".join('<a href="/%s">%s</a>' % (s, esc(n)) for s, n, _d, _i in C.GROUPS)
    info = "".join('<a href="%s">%s</a>' % (u, esc(n)) for u, n in C.INFO_PAGES)
    visit = "" if no_visit else (
        '<a class="foot__visit" href="%s">%s %s</a>'
        % (C.VISIT_URL, art.icon("helmet"), esc(C.VISIT_TITLE)))
    return """
<footer class="foot"><div class="wrap">
  <div class="foot__top">
    <div class="foot__brand">
      <a class="brand" href="/" style="margin-bottom:16px">
        <span class="brand__mark">%s</span>
        <span class="brand__txt"><span class="brand__name">РЕКС</span><span class="brand__sub">%s</span></span>
      </a>
      <p>Материалы для гидроизоляции, ремонта и защиты бетона: обмазочные и проникающие системы,
      инъекционные составы, гидрошпонки, ремонтные смеси и промышленные полы. Прямые поставки
      с завода РЕКС, склад в Наро-Фоминском районе Подмосковья.</p>
      %s
    </div>
    <div><h4>Каталог</h4><div class="foot__list">%s</div></div>
    <div><h4>Компания</h4><div class="foot__list">%s
      <a href="/blog">Блог</a><a href="/kalkulyatory">Калькуляторы</a><a href="/kontakty">Контакты</a></div></div>
    <div><h4>Контакты</h4><div class="foot__list">
      <a class="foot__row" href="%s">%s<b>%s</b></a>
      <a class="foot__row" href="mailto:%s">%s%s</a>
      <span class="foot__row">%s%s</span>
      <span class="foot__row">%s%s</span>
      <span class="foot__row">%s%s</span>
    </div></div>
  </div>
  <div class="foot__bottom">
    <span>© 2014–2026. %s</span>
    <span><a href="/politika-konfidencialnosti">Политика конфиденциальности</a></span>
  </div>
</div></footer>
<button class="up" id="up" aria-label="Наверх">↑</button>
%s</body></html>""" % (art.mark(), esc(C.DEALER), visit, groups, info,
                    C.PHONE_HREF, art.icon("phone"), esc(C.PHONE),
                    C.EMAIL, art.icon("mail"), C.EMAIL,
                    art.icon("pin"), esc(C.ADDR),
                    art.icon("pin"), esc(C.ADDR_2),
                    art.icon("clock"), esc(C.HOURS),
                    "Информация на сайте не является публичной офертой", analytics())


def page(path, title, desc, body, noindex=False, extra_head="", no_visit=False,
         ld="", og_image=None, canonical=True):
    return (head(title, desc, path, noindex, extra_head, ld, og_image, canonical) +
            topbar(no_visit) + header(path, no_visit) + body + footer(no_visit))


def page_body(path, title, desc, body, noindex=False):
    return page(path, title, desc, body, noindex)


def section_head(num, title, lead="", one=False):
    cls = "sec__head sec__head--one" if one or not lead else "sec__head"
    lead_html = '<div class="sec__lead">%s</div>' % lead if lead else ""
    return '<div class="%s"><div><div class="eyebrow"><b>%s</b> — раздел</div><h2>%s</h2></div>%s</div>' % (
        cls, num, title, lead_html)


def price_block(p):
    if p["price"]:
        old = '<s>%s ₽</s>' % "{:,}".format(p["old"]).replace(",", " ") if p.get("old") else ""
        unit = p.get("unit") or "шт"
        return ('<div class="prod__price">%s <small>₽ / %s</small>%s</div>'
                % ("{:,}".format(p["price"]).replace(",", " "), unit, old))
    return '<div class="prod__price">Цена по запросу</div>'


def money(v):
    return "{:,}".format(int(v)).replace(",", " ") + " ₽"

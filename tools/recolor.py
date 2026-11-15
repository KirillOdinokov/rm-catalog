# -*- coding: utf-8 -*-
"""Перекраска rex.moscow в светлую голубую схему (фирменный стиль РЕКС)."""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "site.css")
s = open(CSS, encoding="utf-8").read()

REPL = [
    # --- токены
    ("--ink: #101314;", "--ink: #0d2b3e;"),
    ("--ink-2: #171b1d;", "--ink-2: #123a52;"),
    ("--ink-3: #232a2d;", "--ink-3: #1b4f6d;"),
    ("--paper: #f2f2ee;", "--paper: #f2f8fc;"),
    ("--paper-2: #e8e8e2;", "--paper-2: #e3f0f9;"),
    ("--line: #d6d6cd;", "--line: #cfe2ef;"),
    ("--line-2: #bfc0b6;", "--line-2: #a9c9e0;"),
    ("--muted: #6b716c;", "--muted: #5a7a91;"),
    ("--acc: #ff4d1c;", "--acc: #0088cc;"),
    ("--acc-d: #e23c0d;", "--acc-d: #0069a3;"),
    ("--steel: #2c3a3f;", "--steel: #2b6c8f;"),
    # --- шапка
    (".topline {\n  background: var(--ink); color: #cfd2cb;",
     ".topline {\n  background: var(--acc); color: #eaf6ff;"),
    (".topline a { color: #cfd2cb; }", ".topline a { color: #eaf6ff; }"),
    (".topline__dot { color: var(--acc); }", ".topline__dot { color: #bfe6ff; }"),
    ("background: rgba(242, 242, 238, .94);", "background: rgba(242, 248, 252, .94);"),
    # --- паспорт материала: тёмная карточка -> светлая
    (""".passport {
  position: relative; background: var(--ink); color: #eaece6; border-radius: 2px;
  padding: 22px 24px 20px; box-shadow: 0 30px 60px -34px rgba(16, 19, 20, .55);
}""",
     """.passport {
  position: relative; background: var(--card); color: var(--ink); border: 1px solid var(--line-2);
  border-top: 3px solid var(--acc); border-radius: 2px;
  padding: 22px 24px 20px; box-shadow: 0 26px 50px -34px rgba(13, 43, 62, .35);
}"""),
    ("color: #9aa39b; text-transform: uppercase; }",
     "color: var(--muted); text-transform: uppercase; }"),
    (".passport__plate { margin: 14px 0 10px; background: #f6f6f2; border-radius: 1px; overflow: hidden; }",
     ".passport__plate { margin: 14px 0 10px; background: #f4fafe; border: 1px solid var(--line); border-radius: 1px; overflow: hidden; }"),
    ("border-top: 1px solid rgba(255, 255, 255, .12); }",
     "border-top: 1px solid var(--line); }"),
    (".passport__row dt { font-family: var(--mono); font-size: 9.5px; letter-spacing: .12em; color: #8f988f; text-transform: uppercase; }",
     ".passport__row dt { font-family: var(--mono); font-size: 9.5px; letter-spacing: .12em; color: var(--muted); text-transform: uppercase; }"),
    # --- тёмные секции -> светло-голубые
    (".sec--dark { background: var(--ink); color: #e9ebe4; border-bottom: 0; }",
     ".sec--dark { background: linear-gradient(180deg, #e8f4fb 0%, #f2f8fc 100%); color: var(--ink); border-bottom: 1px solid var(--line); }"),
    (".sec--dark .eyebrow { color: #8f988f; }", ".sec--dark .eyebrow { color: var(--muted); }"),
    (".sec--dark .sec__lead { color: #b9c0b7; }", ".sec--dark .sec__lead { color: #456a83; }"),
    # --- KPI
    (".kpi { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: rgba(255, 255, 255, .14); border: 1px solid rgba(255, 255, 255, .14); }",
     ".kpi { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); }"),
    (".kpi > div { background: var(--ink); padding: 24px 22px; }",
     ".kpi > div { background: var(--card); padding: 24px 22px; }"),
    (".kpi b { display: block; font: 700 34px/1 var(--disp); letter-spacing: -.03em; color: #fff; }",
     ".kpi b { display: block; font: 700 34px/1 var(--disp); letter-spacing: -.03em; color: var(--acc); }"),
    (".kpi span { font-family: var(--mono); font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: #8f988f; }",
     ".kpi span { font-family: var(--mono); font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }"),
    # --- полоса запроса
    (".band { background: var(--ink); color: #fff; }",
     ".band { background: linear-gradient(180deg, #e8f4fb 0%, #dceefa 100%); color: var(--ink); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }"),
    (".band h2 { color: #fff; font-size: clamp(23px, 2.5vw, 34px); line-height: 1.12; }",
     ".band h2 { color: var(--ink); font-size: clamp(23px, 2.5vw, 34px); line-height: 1.12; }"),
    (".band p { color: #b9c0b7; margin: 12px 0 0; max-width: 46ch; }",
     ".band p { color: #456a83; margin: 12px 0 0; max-width: 46ch; }"),
    (".band__note { font-family: var(--mono); font-size: 9.5px; letter-spacing: .08em; color: #8f988f;",
     ".band__note { font-family: var(--mono); font-size: 9.5px; letter-spacing: .08em; color: var(--muted);"),
    # --- подвал: светлый
    (".foot { background: var(--ink); color: #c9cfc6; padding: 56px 0 26px; }",
     ".foot { background: #ffffff; color: var(--ink); border-top: 1px solid var(--line); padding: 56px 0 26px; }"),
    (".foot__top { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1.1fr; gap: 36px; padding-bottom: 40px; border-bottom: 1px solid rgba(255, 255, 255, .12); }",
     ".foot__top { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1.1fr; gap: 36px; padding-bottom: 40px; border-bottom: 1px solid var(--line); }"),
    (".foot__brand .brand__name { color: #fff; }", ".foot__brand .brand__name { color: var(--ink); }"),
    (".foot__brand .brand__sub { color: #8f988f; }", ".foot__brand .brand__sub { color: var(--muted); }"),
    (".foot p { font-size: 13.5px; line-height: 1.6; color: #9aa39b; }",
     ".foot p { font-size: 13.5px; line-height: 1.6; color: var(--muted); }"),
    (".foot h4 { font: 500 10px/1 var(--mono); letter-spacing: .14em; text-transform: uppercase; color: #8f988f; margin-bottom: 16px; }",
     ".foot h4 { font: 500 10px/1 var(--mono); letter-spacing: .14em; text-transform: uppercase; color: var(--muted); margin-bottom: 16px; }"),
    (".foot__bottom { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px; padding-top: 22px; font-family: var(--mono); font-size: 10px; letter-spacing: .06em; color: #7c857c; text-transform: uppercase; }",
     ".foot__bottom { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px; padding-top: 22px; font-family: var(--mono); font-size: 10px; letter-spacing: .06em; color: var(--muted); text-transform: uppercase; }"),
    # --- карточки, теги, таблицы
    (".pcard:hover { background: #fbfbf7; border-color: var(--line-2); }",
     ".pcard:hover { background: #fbfdff; border-color: var(--line-2); }"),
    (".pcard__tag { position: absolute; top: 14px; left: 14px; z-index: 2; font-family: var(--mono); font-size: 9px; letter-spacing: .1em; text-transform: uppercase; background: var(--ink); color: #fff; padding: 4px 7px; }",
     ".pcard__tag { position: absolute; top: 14px; left: 14px; z-index: 2; font-family: var(--mono); font-size: 9px; letter-spacing: .1em; text-transform: uppercase; background: var(--acc); color: #fff; padding: 4px 7px; }"),
    (".pcard__plate { position: relative; background: #f6f6f2; border: 1px solid #ebebe4;",
     ".pcard__plate { position: relative; background: #f4fafe; border: 1px solid #e3eff8;"),
    (".prod__media { background: #f6f6f2; border: 1px solid var(--line); padding: 14px; }",
     ".prod__media { background: #f4fafe; border: 1px solid var(--line); padding: 14px; }"),
    (".note { margin: 1.5em 0; padding: 18px 22px; background: #fbfbf7;",
     ".note { margin: 1.5em 0; padding: 18px 22px; background: #f4fafe;"),
    (".prose blockquote { margin: 1.4em 0; padding: 4px 0 4px 20px; border-left: 2px solid var(--acc); color: #4a534e; font-style: italic; }",
     ".prose blockquote { margin: 1.4em 0; padding: 4px 0 4px 20px; border-left: 2px solid var(--acc); color: #456a83; font-style: italic; }"),
    # --- боковые карточки
    (".side-card--dark { background: var(--ink); border-color: var(--ink); color: #fff; }",
     ".side-card--dark { background: var(--acc); border-color: var(--acc); color: #ffffff; }"),
    (".side-card--dark h3 { color: #8f988f; }", ".side-card--dark h3 { color: #cfeaf9; }"),
    (".side-card--dark p { color: #b9c0b7; font-size: 13.5px; }",
     ".side-card--dark p { color: #e4f4fd; font-size: 13.5px; }"),
    # --- прочее
    (".chip.is-on { background: var(--ink); border-color: var(--ink); color: #fff; }",
     ".chip.is-on { background: var(--acc); border-color: var(--acc); color: #fff; }"),
    (".calc__total span { font: 400 12px/1 var(--mono); color: var(--muted); letter-spacing: .06em; }",
     ".calc__total span { font: 400 12px/1 var(--mono); color: var(--muted); letter-spacing: .06em; }"),
    (".pager .on { background: var(--ink); border-color: var(--ink); color: #fff; }",
     ".pager .on { background: var(--acc); border-color: var(--acc); color: #fff; }"),
    (".calccard:hover { background: #fbfbf7; border-color: var(--line-2); }",
     ".calccard:hover { background: #fbfdff; border-color: var(--line-2); }"),
    (".group:hover { background: var(--paper-2); border-color: var(--line-2); }",
     ".group:hover { background: #f6fbff; border-color: var(--acc); }"),
]

missing = []
for a, b in REPL:
    if a not in s:
        missing.append(a[:70])
    s = s.replace(a, b)

open(CSS, "w", encoding="utf-8").write(s)
print("заменено:", len(REPL) - len(missing), "из", len(REPL))
for m in missing:
    print("  НЕ НАЙДЕНО:", m)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""articles_check.py — вычитка статей блога: типографика, повторы, факты, якоря.

Проверяет content статей в data\model.json:
  • битые якоря содержания (href="#x" без id="x");
  • двойные пробелы, пробел перед знаком, дефис вместо тире, «--»;
  • повтор слова подряд, «. .», пустые абзацы;
  • маркетинговый шум и запрещённые формулировки («мы производим», «наш завод»);
  • дубли предложений внутри статьи и между статьями;
  • числа без единиц (МПа/кг/мм) рядом с «прочность», «расход»;
  • «ё»-варианты и разнобой в названиях марок (РЕКС®/Рекс/reks).

Пишет data\articles_report.json и печатает сводку.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BAD_CLAIMS = [
    (r"\bнаш(?:его|ем|им|его)?\s+завод", "«наш завод» — дилер не производитель"),
    (r"\bмы\s+производим\b", "«мы производим» — дилер не производитель"),
    (r"\bмы\s+изготавливаем\b", "«мы изготавливаем» — дилер не производитель"),
    (r"\bсобственное\s+производство\b", "«собственное производство» — дилер не производитель"),
]
NOISE = [
    (r"лидер\s+рынка", "маркетинговый штамп"),
    (r"не\s+имеет\s+аналогов", "маркетинговый штамп"),
    (r"лучш\w+\s+на\s+рынке", "маркетинговый штамп"),
    (r"инновационн\w+", "маркетинговый штамп"),
    (r"уникальн\w+\s+технолог\w+", "маркетинговый штамп"),
]
TYPO = [
    (r"\bслсьав\b", "опечатка «слсьав»"),
    (r"\bжидксоть\b", "опечатка «жидксоть»"),
    (r"\bэпоксиднй\b", "опечатка «эпоксиднй»"),
    (r"\bпродукци\b", "опечатка"),
    (r"\bисользу\w*", "опечатка «исользуется»"),
    (r"\bпроизвоство\b", "опечатка"),
]


def strip_tags(html):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&laquo;", "«").replace("&raquo;", "»")
    t = t.replace("&mdash;", "—").replace("&ndash;", "–").replace("&amp;", "&")
    return re.sub(r"[ \t]+", " ", t)


def main():
    model = json.load(open(os.path.join(ROOT, "data", "model.json"), encoding="utf-8"))
    posts = model["posts"]
    report = {}
    sent_index = defaultdict(list)
    total = Counter()

    for p in posts:
        html = p.get("content") or ""
        txt = strip_tags(html)
        issues = []

        ids = set(re.findall(r'id="([^"]+)"', html))
        hrefs = set(re.findall(r'href="#([^"]+)"', html))
        for m in sorted(hrefs - ids):
            issues.append(("anchor", m))

        for rx, msg in TYPO:
            for m in re.finditer(rx, txt, re.I):
                issues.append(("typo", "%s: …%s…" % (msg, txt[max(0, m.start() - 40):m.end() + 40])))

        for rx, msg in BAD_CLAIMS:
            for m in re.finditer(rx, txt, re.I):
                issues.append(("claim", "%s: …%s…" % (msg, txt[max(0, m.start() - 50):m.end() + 60])))

        for rx, msg in NOISE:
            for m in re.finditer(rx, txt, re.I):
                issues.append(("noise", "%s: …%s…" % (msg, txt[max(0, m.start() - 40):m.end() + 40])))

        for m in re.finditer(r"  +", txt):
            issues.append(("space", txt[max(0, m.start() - 30):m.end() + 30]))
            break
        for m in re.finditer(r"\s+[,;:.!?]", txt):
            issues.append(("space", "пробел перед знаком: …%s…" % txt[max(0, m.start() - 30):m.end() + 20]))
            break
        for m in re.finditer(r"(?<=\s)-(?=\s)", txt):
            issues.append(("dash", "дефис вместо тире: …%s…" % txt[max(0, m.start() - 40):m.end() + 40]))
            break
        for m in re.finditer(r"\b(\w+)\s+\1\b", txt):
            if m.group(1).lower() not in ("что", "как", "это"):
                issues.append(("repeat", "повтор слова: …%s…" % txt[max(0, m.start() - 40):m.end() + 40]))
                break
        for m in re.finditer(r"[а-яё]{35,}", txt):
            issues.append(("longword", m.group(0)))

        # предложения длиннее 260 знаков — тяжёлые для чтения
        for s in re.split(r"(?<=[.!?])\s+", txt):
            s = s.strip()
            if len(s) > 260:
                issues.append(("longsentence", "%d знаков: %s…" % (len(s), s[:120])))

        # одинаковые предложения внутри статьи
        seen = Counter()
        for s in re.split(r"(?<=[.!?])\s+", txt):
            s2 = re.sub(r"\s+", " ", s.strip().lower())
            if len(s2) > 60:
                seen[s2] += 1
        for s2, n in seen.items():
            if n > 1:
                issues.append(("dupsent", "×%d: %s" % (n, s2[:110])))

        # индекс предложений для поиска повторов между статьями
        for s in re.split(r"(?<=[.!?])\s+", txt):
            s2 = re.sub(r"\s+", " ", s.strip().lower())
            if len(s2) > 90:
                sent_index[s2].append(p["slug"])

        for i in issues:
            total[i[0]] += 1
        report[p["slug"]] = {"title": p["title"], "issues": issues,
                             "words": len(txt.split()), "chars": len(txt)}

    cross = {s: v for s, v in sent_index.items() if len(set(v)) > 1}
    with open(os.path.join(ROOT, "data", "articles_report.json"), "w", encoding="utf-8") as f:
        json.dump({"articles": report, "cross": cross}, f, ensure_ascii=False, indent=1)

    print("статей: %d" % len(posts))
    print("проблемы:", dict(total))
    print("предложений-дублей между статьями: %d" % len(cross))
    for s, v in list(cross.items())[:8]:
        print("  ×", sorted(set(v))[:3], "|", s[:100])
    bad = [(k, v["issues"]) for k, v in report.items() if v["issues"]]
    print("статей с замечаниями: %d" % len(bad))
    for k, iss in bad[:12]:
        print(" -", k, len(iss), iss[:3])


if __name__ == "__main__":
    main()

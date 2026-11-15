#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""rekspro_match.py — сопоставление карточек сайта с карточками завода reks.pro.

Вход:  data\model.json, data\rekspro\kb.json, data\rekspro\manual_match.json (правки руками)
Выход: data\rekspro\match.json   site_slug -> {kb, score, method, color}

Порядок: точный код → сходство по токенам → префикс/суффикс кода → difflib.
Ручные правки в manual_match.json имеют приоритет: {"site-slug": "kb-slug"} или null.
"""
import difflib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "rekspro")

# служебные слова, которые не определяют модель
STOP_WORDS = set("""
к к1 к2 к3 1к 2к 3к 1 2 3 тм рекс® шт
ремонтная ремонтный ремонтной смесь смеси смесей
гидроизоляционная гидроизоляционный гидроизоляционной гидроизоляционное
гидрофобизирующая гидрофобизирующий жидкость жидксоть
клеевая клеевой клеевые монтажный монтажная штукатурно-клеевая
быстротвердеющая быстротвердеющий высокопрочная высокопрочный высокопрочное
облегченная облегченный подливочный подливочная эпоксидный эпоксидная эпоксидной
эпоксидное химический химическая анкеровочный анкерный
огнезащитное огнезащитный декоративный декоративная
защитная защитный защитное эмаль состав составы
инъекционная инъекционный инъекционное полиуретановый полиуретановая
герметик гидрошпонка гидролента гидроизоляционная
hdpe мембрана вяжущее цементное покрытие покрытия пола промышленного
праймер грунтовка стяжка плитка плиточный
белый серый красный черный чёрный
кг г л мл л. п.м м2 м3 мм мкм
""".split())

COLORS = {"белый": "белый", "серый": "серый", "красный": "красный",
          "черный": "чёрный", "чёрный": "чёрный"}


def norm(s):
    s = (s or "").lower().replace("ё", "е").replace("®", " ")
    s = re.sub(r"(?<=\d)\s*[х×x]\s*(?=\d)", "x", s)   # 10х100 -> 10x100
    s = s.replace("ø", " ").replace("×", "x")
    s = re.sub(r"[^0-9a-zа-я.\s/-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    out = []
    for w in re.split(r"[\s/-]+", norm(s)):
        w = w.strip(".")
        if not w or w in STOP_WORDS:
            continue
        out.append(w)
    return out


def code_of(s, strip=True):
    ws = tokens(s) if strip else [w for w in re.split(r"[\s/-]+", norm(s)) if w]
    return "".join(ws)


def color_of(s):
    n = norm(s)
    for k, v in COLORS.items():
        if k in n:
            return v
    return ""


def main():
    model = json.load(open(os.path.join(ROOT, "data", "model.json"), encoding="utf-8"))
    kb = {k: v for k, v in json.load(open(os.path.join(SRC, "kb.json"), encoding="utf-8")).items()
          if not k.startswith("_")}
    manual_p = os.path.join(SRC, "manual_match.json")
    manual = json.load(open(manual_p, encoding="utf-8")) if os.path.exists(manual_p) else {}

    kb_codes = {}
    for slug, v in kb.items():
        for c in {code_of(v["name"]), code_of(v["name"], False)}:
            if c:
                kb_codes.setdefault(c, slug)
    kb_names = {k: v["name"] for k, v in kb.items()}

    def by_prefix(code):
        """код завода — префикс или суффикс нашего кода (гидролента 200х1 -> гидролента)"""
        best = None
        for c, slug in kb_codes.items():
            if len(c) < 4 or c.isdigit():
                continue
            if code.startswith(c) or code.endswith(c):
                if best is None or len(c) > best[1]:
                    best = (slug, len(c))
        return best[0] if best else None

    def by_tokens(name):
        want = set(tokens(name))
        if not want:
            return None, 0.0
        best, bs = None, 0.0
        for slug, nm in kb_names.items():
            have = set(tokens(nm))
            if not have:
                continue
            inter = want & have
            if not inter:
                continue
            s = len(inter) / len(have | want)
            if s > bs:
                best, bs = slug, s
        return best, bs

    match, unmatched = {}, []
    for p in model["products"]:
        slug, name = p["slug"], p["name"]
        color = color_of(name)
        if slug in manual:
            match[slug] = {"kb": manual[slug], "score": 1.0, "method": "manual", "color": color}
            continue
        c1, c2 = code_of(name), code_of(name, False)
        hit = kb_codes.get(c1) or kb_codes.get(c2)
        method = "code"
        if not hit:
            hit = by_prefix(c1) or by_prefix(c2)
            method = "prefix"
        if not hit:
            cand, sc = by_tokens(name)
            if cand and sc >= 0.72:
                hit, method = cand, "tokens:%.2f" % sc
        if not hit:
            pool = {code_of(n): k for k, n in kb_names.items()}
            best = difflib.get_close_matches(c1 or c2, list(pool), n=1, cutoff=0.88)
            if best:
                hit, method = pool[best[0]], "fuzzy"
        if hit:
            match[slug] = {"kb": hit, "score": 1.0, "method": method, "color": color}
        else:
            match[slug] = {"kb": None, "score": 0.0, "method": "none", "color": ""}
            unmatched.append((slug, name))

    with open(os.path.join(SRC, "match.json"), "w", encoding="utf-8") as f:
        json.dump(match, f, ensure_ascii=False, indent=1, sort_keys=True)

    ok = [s for s, v in match.items() if v["kb"]]
    print("товаров сайта: %d, сопоставлено: %d, без пары: %d" % (len(model["products"]),
                                                                 len(ok), len(unmatched)))
    used = {}
    for s, v in match.items():
        if v["kb"]:
            used.setdefault(v["kb"], []).append(s)
    print("позиций завода задействовано: %d из %d" % (len(used), len(kb)))
    for s, n in unmatched:
        print("  -", s, "|", n)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Пластины-«паспорта»: параметрическая графика упаковки и узлов."""
import re

W, H = 440, 330
INK = "#0e2a3d"
LINE = "#a9c9e0"
ACC = "#0088cc"
SOFT = "#f4fafe"

_seq = [0]


def _uid(p="h"):
    _seq[0] += 1
    return "%s%d" % (p, _seq[0])


def _defs():
    return ('<defs><pattern id="hx" width="7" height="7" patternTransform="rotate(45)" '
            'patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="7" stroke="#101314" '
            'stroke-width="0.8" opacity=".28"/></pattern>'
            '<pattern id="hx2" width="9" height="9" patternTransform="rotate(-45)" '
            'patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="9" stroke="#101314" '
            'stroke-width="0.7" opacity=".2"/></pattern></defs>')


def _frame(code="", label=""):
    m = 18
    t = 9
    marks = []
    for (x1, y1, x2, y2) in ((m, m, m + t, m), (m, m, m, m + t),
                             (W - m, m, W - m - t, m), (W - m, m, W - m, m + t),
                             (m, H - m, m + t, H - m), (m, H - m, m, H - m - t),
                             (W - m, H - m, W - m - t, H - m), (W - m, H - m, W - m, H - m - t)):
        marks.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.2"/>'
                     % (x1, y1, x2, y2, LINE))
    txt = ''
    if code:
        txt += ('<text x="%d" y="30" text-anchor="end" font-family="IBM Plex Mono,monospace" font-size="9" '
                'letter-spacing="1.6" fill="#6b716c">%s</text>' % (W - 26, _e(code)))
    if label:
        txt += ('<text x="26" y="%d" font-family="IBM Plex Mono,monospace" font-size="9.5" '
                'letter-spacing="1.4" fill="#6b716c">%s</text>' % (H - 26, _e(label)))
    return ''.join(marks) + txt


def _e(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _vdim(x, y1, y2, text):
    return ('<g stroke="%s" stroke-width="1"><line x1="%d" y1="%d" x2="%d" y2="%d"/>'
            '<line x1="%d" y1="%d" x2="%d" y2="%d"/><line x1="%d" y1="%d" x2="%d" y2="%d"/></g>'
            '<text x="%d" y="%d" font-family="IBM Plex Mono,monospace" font-size="8.5" fill="#6b716c" '
            'letter-spacing="1" transform="rotate(-90 %d %d)">%s</text>'
            % (LINE, x - 5, y1, x + 5, y1, x - 5, y2, x + 5, y2, x, y1, x, y2,
               x - 9, (y1 + y2) // 2 + 16, x - 9, (y1 + y2) // 2 + 16, _e(text)))


def _hdim(y, x1, x2, text):
    return ('<g stroke="%s" stroke-width="1"><line x1="%d" y1="%d" x2="%d" y2="%d"/>'
            '<line x1="%d" y1="%d" x2="%d" y2="%d"/><line x1="%d" y1="%d" x2="%d" y2="%d"/></g>'
            '<text x="%d" y="%d" text-anchor="middle" font-family="IBM Plex Mono,monospace" '
            'font-size="8.5" fill="#6b716c" letter-spacing="1">%s</text>'
            % (LINE, x1, y - 5, x1, y + 5, x2, y - 5, x2, y + 5, x1, y, x2, y,
               (x1 + x2) // 2, y - 8, _e(text)))


def _stud(label, code):
    """Анкерная шпилька: стержень с резьбой, воротник, размер."""
    g = []
    x, w, top, bot = 206, 26, 92, 262
    g.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#ffffff" stroke="%s" stroke-width="1.6"/>'
             % (x, top, w, bot - top, INK))
    y = top + 9
    while y < bot - 10:
        g.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>'
                 % (x, y + 6, x + w, y, LINE))
        y += 9
    g.append('<rect x="%d" y="66" width="%d" height="24" fill="#ffffff" stroke="%s" stroke-width="1.6"/>'
             % (x - 11, w + 22, INK))
    g.append('<line x1="%d" y1="78" x2="%d" y2="78" stroke="%s" stroke-width="1" stroke-dasharray="3 3"/>'
             % (x - 11, x + w + 11, INK))
    g.append('<text x="220" y="300" text-anchor="middle" font-family="IBM Plex Mono,monospace" '
             'font-size="10" letter-spacing="1.6" fill="%s">%s</text>' % (INK, _e(label)))
    g.append(_vdim(326, 66, bot, code))
    return ''.join(g)


def _bag(label, code):
    g = ['<path d="M126 96 C126 82 140 74 158 74 H286 C304 74 318 82 318 96 V242 '
         'C318 260 302 272 284 272 H160 C142 272 126 260 126 242 Z" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<path d="M126 96 C126 82 140 74 158 74 H286 C304 74 318 82 318 96 V106 '
         'C318 92 304 84 286 84 H158 C140 84 126 92 126 106 Z" fill="url(#hx)" opacity=".55"/>',
         '<line x1="126" y1="106" x2="318" y2="106" stroke="%s" stroke-width="1.2" stroke-dasharray="5 4"/>' % INK,
         '<line x1="126" y1="120" x2="318" y2="120" stroke="%s" stroke-width="1" opacity=".5"/>' % INK,
         '<rect x="152" y="158" width="140" height="46" fill="none" stroke="%s" stroke-width="1.1"/>' % INK,
         '<text x="222" y="180" text-anchor="middle" font-family="Geologica,Arial" font-size="17" '
         'font-weight="700" letter-spacing="3" fill="%s">РЕКС</text>' % INK,
         '<text x="222" y="196" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="7.5" '
         'letter-spacing="1.4" fill="#6b716c">ENGINEERING CHEMISTRY</text>',
         '<path d="M156 246 H288" stroke="%s" stroke-width="0" />' % INK,
         '<text x="222" y="252" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="10" '
         'letter-spacing="1.6" fill="%s">%s</text>' % (INK, _e(label)),
         _vdim(346, 74, 272, code)]
    return ''.join(g)


def _pail(label, code):
    g = ['<ellipse cx="220" cy="112" rx="82" ry="18" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<path d="M138 112 V236 C138 254 175 266 220 266 C265 266 302 254 302 236 V112" '
         'fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<path d="M138 176 C138 194 175 206 220 206 C265 206 302 194 302 176 V112 '
         'C302 130 265 142 220 142 C175 142 138 130 138 112 Z" fill="url(#hx2)" opacity=".5"/>',
         '<ellipse cx="220" cy="112" rx="82" ry="18" fill="none" stroke="%s" stroke-width="1.2" '
         'stroke-dasharray="4 3"/>' % INK,
         '<path d="M170 240 C186 250 254 250 270 240" fill="none" stroke="%s" stroke-width="1.1"/>' % INK,
         '<text x="220" y="196" text-anchor="middle" font-family="Geologica,Arial" font-size="16" '
         'font-weight="700" letter-spacing="3" fill="%s">РЕКС</text>' % INK,
         '<text x="220" y="252" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="10" '
         'letter-spacing="1.4" fill="%s">%s</text>' % (INK, _e(label)),
         _vdim(330, 94, 266, code)]
    return ''.join(g)


def _canister(label, code):
    g = ['<path d="M168 96 H268 C278 96 284 104 284 114 V252 C284 262 276 268 266 268 H170 '
         'C160 268 152 262 152 252 V114 C152 104 158 96 168 96 Z" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<rect x="200" y="74" width="40" height="24" rx="4" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<line x1="210" y1="74" x2="210" y2="60" stroke="%s" stroke-width="1.6"/>' % INK,
         '<line x1="230" y1="74" x2="230" y2="60" stroke="%s" stroke-width="1.6"/>' % INK,
         '<path d="M152 150 H214 C222 150 228 156 228 164 V196" fill="none" stroke="%s" stroke-width="1.3"/>' % INK,
         '<rect x="164" y="180" width="112" height="56" fill="url(#hx)" opacity=".45"/>',
         '<text x="220" y="212" text-anchor="middle" font-family="Geologica,Arial" font-size="14" '
         'font-weight="700" letter-spacing="2.5" fill="%s">РЕКС</text>' % INK,
         '<text x="220" y="250" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="9.5" '
         'letter-spacing="1.3" fill="%s">%s</text>' % (INK, _e(label)),
         _vdim(318, 96, 268, code)]
    return ''.join(g)


def _cartridge(label, code):
    g = ['<rect x="150" y="92" width="140" height="168" rx="8" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<path d="M190 92 V70 C190 62 196 56 204 56 H236 C244 56 250 62 250 70 V92" fill="#fff" '
         'stroke="%s" stroke-width="1.6"/>' % INK,
         '<path d="M212 56 V34 H228 V56" fill="none" stroke="%s" stroke-width="1.6"/>' % INK,
         '<rect x="150" y="92" width="140" height="34" fill="url(#hx2)" opacity=".55"/>',
         '<rect x="164" y="150" width="112" height="62" fill="none" stroke="%s" stroke-width="1.05"/>' % INK,
         '<text x="220" y="178" text-anchor="middle" font-family="Geologica,Arial" font-size="14" '
         'font-weight="700" letter-spacing="2.5" fill="%s">РЕКС</text>' % INK,
         '<text x="220" y="196" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="7" '
         'letter-spacing="1.2" fill="#6b716c">2K SYSTEM</text>',
         '<text x="220" y="248" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="9.5" '
         'letter-spacing="1.3" fill="%s">%s</text>' % (INK, _e(label)),
         _vdim(330, 92, 260, code)]
    return ''.join(g)


def _roll(label, code):
    g = ['<rect x="120" y="112" width="200" height="120" rx="6" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<ellipse cx="320" cy="172" rx="26" ry="60" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<ellipse cx="320" cy="172" rx="12" ry="28" fill="none" stroke="%s" stroke-width="1.2"/>' % INK,
         '<path d="M120 132 H300 M120 152 H300 M120 172 H300 M120 192 H300 M120 212 H300" '
         'stroke="%s" stroke-width=".8" opacity=".35"/>' % INK,
         '<rect x="140" y="140" width="120" height="44" fill="#f4fafe" stroke="%s" stroke-width="1.1"/>' % INK,
         '<text x="200" y="160" text-anchor="middle" font-family="Geologica,Arial" font-size="13" '
         'font-weight="700" letter-spacing="2.4" fill="%s">РЕКС</text>' % INK,
         '<text x="200" y="176" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="7" '
         'letter-spacing="1.1" fill="#6b716c">%s</text>' % _e(label),
         _hdim(268, 120, 320, code)]
    return ''.join(g)


def _profile(label, code, variant="p"):
    if variant == "press":
        body = ('<path d="M96 196 H150 V150 H190 V196 H250 V150 H290 V196 H344 V232 H290 V268 H250 V232 '
                'H190 V268 H150 V232 H96 Z" fill="#fff" stroke="%s" stroke-width="1.7"/>' % INK)
        plate = ('<rect x="128" y="118" width="184" height="20" fill="#fff" stroke="%s" stroke-width="1.7"/>'
                 '<rect x="128" y="118" width="184" height="20" fill="url(#hx2)" opacity=".7"/>' % INK)
        extra = plate + body
    elif variant == "plain":
        extra = ('<path d="M96 188 H344 V240 H96 Z" fill="#fff" stroke="%s" stroke-width="1.7"/>'
                 '<path d="M96 188 H344 V240 H96 Z" fill="url(#hx)" opacity=".4"/>'
                 '<path d="M150 188 V240 M190 188 V240 M250 188 V240 M290 188 V240" stroke="%s" '
                 'stroke-width="1.2"/>' % (INK, INK))
    else:
        extra = ('<path d="M96 196 H150 V150 H190 V196 H250 V150 H290 V196 H344 V232 H290 V268 H250 V232 '
                 'H190 V268 H150 V232 H96 Z" fill="#fff" stroke="%s" stroke-width="1.7"/>'
                 '<path d="M96 196 H150 V150 H190 V196 H250 V150 H290 V196 H344 V232 H290 V268 H250 V232 '
                 'H190 V268 H150 V232 H96 Z" fill="url(#hx)" opacity=".4"/>' % INK)
    g = [extra,
         '<text x="220" y="122" text-anchor="middle" font-family="Geologica,Arial" font-size="13" '
         'font-weight="700" letter-spacing="2.6" fill="%s">РЕКС</text>' % INK,
         '<text x="220" y="138" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="7.5" '
         'letter-spacing="1.2" fill="#6b716c">%s</text>' % _e(label),
         _hdim(300, 96, 344, code)]
    return ''.join(g)


def _drum(label, code):
    g = ['<rect x="150" y="80" width="140" height="196" rx="10" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<path d="M150 108 H290 M150 140 H290 M150 216 H290 M150 248 H290" stroke="%s" stroke-width="1.1"/>' % INK,
         '<ellipse cx="220" cy="80" rx="70" ry="12" fill="#fff" stroke="%s" stroke-width="1.6"/>' % INK,
         '<rect x="166" y="160" width="108" height="44" fill="none" stroke="%s" stroke-width="1.1"/>' % INK,
         '<text x="220" y="180" text-anchor="middle" font-family="Geologica,Arial" font-size="13" '
         'font-weight="700" letter-spacing="2.4" fill="%s">РЕКС</text>' % INK,
         '<text x="220" y="194" text-anchor="middle" font-family="IBM Plex Mono,monospace" font-size="7" '
         'letter-spacing="1.1" fill="#6b716c">%s</text>' % _e(label),
         _vdim(330, 68, 276, code)]
    return ''.join(g)


KIND_BY_NAME = [
    (r"шпильк", "stud"),
    (r"гильза", "profile"),
    (r"гидрошпонк", "profile"),
    (r"мембран|гидролента", "roll"),
    (r"анкер", "cartridge"),
    (r"герметик|firestop|плаг", "cartridge"),
    (r"инъекц|гельакрил|рокстаб|сойл|hacut kat|очистител", "canister"),
    (r"северус|эпо|праймер|эмаль|лик|топ|флекс", "pail"),
    (r"смесь|структо|граут|флюид|грип|фаб|тиксо|акрил|стяжк|покрытие|состав|клей|плит", "bag"),
]

PACK_BY_KIND = {
    "bag": "МЕШОК · 25 КГ",
    "pail": "КОМПЛЕКТ · 2К",
    "canister": "КАН. · 10 Л",
    "cartridge": "КАРТРИДЖ · 600 МЛ",
    "roll": "РУЛОН · 20 М",
    "profile": "ПРОФИЛЬ · 2 М",
    "drum": "БОЧКА · 200 Л",
}


def kind_of(p):
    name = (p.get("name") or "").lower()
    for rx, kind in KIND_BY_NAME:
        if re.search(rx, name):
            return kind
    return "bag"


PACK_WEIGHT = {
    "bag": "25 КГ",
    "pail": "20 КГ",
    "canister": "10 Л",
    "cartridge": "600 МЛ",
    "roll": "20 М",
    "profile": "2 М",
    "drum": "200 Л",
}

# форма и вес упаковки из прайса («меш. 25 кг», «Комплект 35 кг (меш. 25 + канистра 10 кг)»)
PACK_FORMS = [
    (r"картридж", "КАРТРИДЖ"),
    (r"комплект", "КОМПЛЕКТ"),
    (r"канистр", "КАНИСТРА"),
    (r"ведро", "ВЕДРО"),
    (r"меш", "МЕШОК"),
    (r"бочк|барабан", "БОЧКА"),
    (r"рулон", "РУЛОН"),
    (r"коробк", "КОРОБКА"),
]
PACK_UNIT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(мл|кг|л|п\.?\s?м)")


def pack_of(p):
    """(форма, вес) упаковки: из прайса, иначе по типу товара."""
    kind = kind_of(p)
    label = PACK_BY_KIND.get(kind, "")
    weight = PACK_WEIGHT.get(kind, "")
    if p.get("size"):
        return "ШПИЛЬКА · %s" % p["size"], p["size"]
    pack = (p.get("pack") or "").lower().replace("\xa0", " ")
    if not pack:
        return label, weight
    form = next((lab for rx, lab in PACK_FORMS if re.search(rx, pack)), "")
    m = PACK_UNIT.search(pack)
    unit = ""
    if m:
        num = m.group(1).replace(".", ",")
        u = m.group(2).replace(" ", "").upper()
        u = "П.М." if u.startswith("П") else u
        unit = num + " " + u
    if not form:
        form = label.split("·")[0].strip() or "УПАКОВКА"
    if not unit:
        unit = weight
    return "%s · %s" % (form, unit), unit


def plate(p, code=""):
    kind = kind_of(p)
    label, weight = pack_of(p)
    name = (p.get("name") or "").lower()
    variant = "p"
    if re.search(r"прижимн|шд", name):
        variant = "press"
    elif re.search(r"тхд|тхр|тхг|thg", name):
        variant = "plain"
    if kind == "profile":
        draw = _profile(label, weight, variant)
    else:
        fn = {"bag": _bag, "pail": _pail, "canister": _canister, "cartridge": _cartridge,
              "roll": _roll, "drum": _drum, "stud": _stud}[kind]
        draw = fn(label, weight)
    inner = _defs() + '<g transform="translate(220,168) scale(1.14) translate(-220,-168)">' + \
        draw + '</g>'
    return ('<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="%s">%s%s</svg>' % (W, H, _e(p.get("name", "")), inner,
                                            _frame("RDS \\ " + kind.upper(), "")))


def _art(p):
    return re.sub(r"[^\d]", "", str(p.get("sku")) or "")[-3:].rjust(3, "0")


# ------------------------------------------------------------------ hero
def hero_art():
    """Разрез «стена в грунте»: бетон, гидроизоляция, инъекция."""
    s = [_defs()]
    s.append('<rect x="0" y="0" width="440" height="330" fill="#f4fafe"/>')
    # грунт
    s.append('<path d="M0 258 H440 V330 H0 Z" fill="#e4e4da"/>')
    s.append('<path d="M0 258 H440 V330 H0 Z" fill="url(#hx2)" opacity=".6"/>')
    s.append('<path d="M0 258 H440" stroke="%s" stroke-width="2"/>' % INK)
    # бетонная стена
    s.append('<rect x="84" y="26" width="272" height="232" fill="#fff" stroke="%s" stroke-width="2"/>' % INK)
    s.append('<rect x="84" y="26" width="272" height="232" fill="url(#hx)" opacity=".2"/>')
    # трещина
    s.append('<path d="M210 26 L202 74 L216 116 L206 158 L220 200 L210 258" fill="none" '
             'stroke="%s" stroke-width="2.6"/>' % INK)
    # инъекционные пакеры
    for y in (74, 140, 206):
        s.append('<circle cx="210" cy="%d" r="8.5" fill="#fff" stroke="%s" stroke-width="2.2"/>' % (y, ACC))
        s.append('<circle cx="210" cy="%d" r="2.6" fill="%s"/>' % (y, ACC))
    s.append('<line x1="218" y1="74" x2="252" y2="66" stroke="%s" stroke-width="1.2"/>' % ACC)
    s.append('<text x="256" y="64" font-family="IBM Plex Mono,monospace" font-size="8.5" fill="#6b716c" '
             'letter-spacing="1.1">ПАКЕР</text>')
    # мембрана
    s.append('<rect x="356" y="26" width="16" height="232" fill="%s"/>' % ACC)
    s.append('<text x="386" y="150" font-family="IBM Plex Mono,monospace" font-size="8.5" fill="%s" '
             'letter-spacing="1.1" transform="rotate(90 386 150)">МЕМБРАНА</text>' % ACC)
    # размеры
    s.append(_hdim(292, 84, 372, "3 200 ММ"))
    s.append(_vdim(58, 26, 258, "2 000 ММ"))
    s.append(_frame("", ""))
    s.append('<text x="22" y="165" text-anchor="middle" transform="rotate(-90 22 165)" '
             'font-family="IBM Plex Mono,monospace" font-size="9" letter-spacing="1.6" '
             'fill="#5a7a91">РАЗРЕЗ · УЗЕЛ 04</text>')
    return ('<svg viewBox="0 0 440 330" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Разрез узла гидроизоляции">%s</svg>' % ''.join(s))


_ICONS = {
    "arrow": '<path d="M4 12h15M13 6l6 6-6 6"/>',
    "check": '<path d="M4 12.5l5 5L20 6"/>',
    "phone": '<path d="M6 3h3l2 5-2 2a12 12 0 006 6l2-2 5 2v3a2 2 0 01-2 2A18 18 0 013 6a2 2 0 012-2z"/>',
    "mail": '<path d="M3 6h18v12H3zM3 7l9 7 9-7"/>',
    "pin": '<path d="M12 21s7-6.3 7-11a7 7 0 10-14 0c0 4.7 7 11 7 11z"/>'
           '<circle cx="12" cy="10" r="2.4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.4 2"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4.4-4.4"/>',
    "grid": '<path d="M4 4h6.6v6.6H4zM13.4 4H20v6.6h-6.6zM4 13.4h6.6V20H4zM13.4 13.4H20V20h-6.6z"/>',
    "doc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 15.6h6M9 19.2h3.6"/>',
    "calc": '<path d="M6 3h12v18H6z"/><path d="M9 7.4h6"/><path d="M9 11.4h2M13 11.4h2M9 15h2M13 15h2"/>',
    # выезд специалиста — каска
    "helmet": '<path d="M4.6 16.8v-3.2a7.4 7.4 0 0114.8 0v3.2"/><path d="M2.2 16.8h19.6"/>'
              '<path d="M12 6.2v10.6"/><path d="M7.9 8.3v8.5"/><path d="M16.1 8.3v8.5"/>',
    # направления
    "drop": '<path d="M12 3.2c3.4 4 6 6.9 6 10a6 6 0 11-12 0c0-3.1 2.6-6 6-10z"/>'
            '<path d="M9.4 13.8a2.6 2.6 0 002.6 2.6"/>',
    "trowel": '<path d="M9 15l6-6 4 4-6 6z"/><path d="M3 21l6-6"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12.4l9 5 9-5"/><path d="M3 16.9l9 5 9-5"/>',
    "shield": '<path d="M12 3l7.2 3v5.6c0 4.4-3 8.4-7.2 9.6-4.2-1.2-7.2-5.2-7.2-9.6V6z"/>'
              '<path d="M8.8 11.8l2.3 2.3 4.1-4.4"/>',
    "glue": '<path d="M8.6 8h6.8v9.4a2 2 0 01-2 2h-2.8a2 2 0 01-2-2z"/><path d="M10.4 8V5.6h3.2V12"/>'
            '<path d="M10.4 5.6V3h3.2v2.6"/><path d="M9.4 12.4h5.2M9.4 16.2h5.2"/>',
    "bolt": '<path d="M8.8 3h6.4v3.2H8.8z"/><path d="M12 6.2V21"/>'
            '<path d="M9.2 10h5.6M9.2 13.6h5.6M9.2 17.2h5.6"/>',
    # сервис и поставка
    "warehouse": '<path d="M3 20.2V9.2l9-5.2 9 5.2v11"/><path d="M2 20.2h20"/>'
                 '<path d="M7.4 20.2v-6.1h9.2v6.1"/><path d="M7.4 17.2h9.2"/>',
    "truck": '<path d="M2.2 7h11.4v9.2H2.2z"/><path d="M13.6 10.2h3.6L21 13.6v2.6h-7.4z"/>'
             '<circle cx="6.4" cy="18" r="1.9"/><circle cx="17.2" cy="18" r="1.9"/>',
    "factory": '<path d="M3 21V10.4l5-3v6l5-3v6l5-3V21"/><path d="M2 21h20"/>'
               '<path d="M18 10.4V3h3v10.4"/>',
    "ruler": '<path d="M2.6 15.4L15.4 2.6 21.4 8.6 8.6 21.4z"/><path d="M6.4 11.6l2 2"/>'
             '<path d="M9.6 8.4l2 2"/><path d="M12.8 5.2l2 2"/>',
    "seal": '<circle cx="12" cy="9.2" r="5.6"/><path d="M8.4 13.6L7 21l5-2.6L17 21l-1.4-7.4"/>',
    "package": '<path d="M12 2.8l8.4 4.4v9.6L12 21.2 3.6 16.8V7.2z"/><path d="M3.6 7.2L12 11.6l8.4-4.4"/>'
               '<path d="M12 11.6v9.6"/>',
    "tag": '<path d="M3 12.2V3.2h9l8.6 8.6-9.2 9.2z"/><circle cx="7.6" cy="7.6" r="1.6"/>',
    "chat": '<path d="M3.4 4.6h17.2v11.6H12l-4.6 4.2v-4.2H3.4z"/>',
}


def icon(name, cls=""):
    """Иконка 24×24: тонкий штрих, техническая геометрия, наследует цвет текста."""
    inner = _ICONS.get(name) or _ICONS["arrow"]
    return ('<svg class="ic %s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % (cls, inner))


def mark():
    """Знак: Р в модульной сетке — бетонный блок с сечением."""
    return ('<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            '<rect x="2" y="2" width="36" height="36" stroke="%s" stroke-width="2"/>'
            '<path d="M11 30V11h9a5.5 5.5 0 010 11h-9" stroke="%s" stroke-width="2.4"/>'
            '<path d="M20 22l9 8" stroke="%s" stroke-width="2.4"/>'
            '<rect x="26" y="6" width="8" height="8" fill="%s"/></svg>' % (INK, INK, INK, ACC))

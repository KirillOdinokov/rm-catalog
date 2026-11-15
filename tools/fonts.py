# -*- coding: utf-8 -*-
"""Скачиваем шрифты Google Fonts (woff2, cyrillic+latin) для rex.moscow."""
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'fonts')
os.makedirs(OUT, exist_ok=True)
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0.0.0 Safari/537.36')

FAMILIES = {
    'geologica': 'Geologica:wght@500;600;700;800',
    'commissioner': 'Commissioner:wght@300;400;500;600;700',
}


def get(url, binary=False):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read() if binary else r.read().decode('utf-8')


lines = ['/* self-hosted: Geologica (display), Commissioner (text), IBM Plex Mono */']
for key, fam in FAMILIES.items():
    css = get('https://fonts.googleapis.com/css2?family=%s&display=swap' % fam)
    blocks = re.findall(r'/\*\s*([a-z\-]+)\s*\*/\s*@font-face\s*\{(.*?)\}', css, re.S)
    if not blocks:
        blocks = [('all', b) for b in re.findall(r'@font-face\s*\{(.*?)\}', css, re.S)]
    for subset, body in blocks:
        subset = subset.strip()
        if subset not in ('cyrillic', 'cyrillic-ext', 'latin', 'latin-ext'):
            continue
        m = re.search(r'url\((https://[^)]+\.woff2)\)', body)
        if not m:
            continue
        w = re.search(r'font-weight:\s*(\d+)', body)
        weight = w.group(1) if w else '400'
        fname = '%s-%s-%s.woff2' % (key, weight, subset)
        path = os.path.join(OUT, fname)
        if not os.path.exists(path):
            open(path, 'wb').write(get(m.group(1), binary=True))
        rng = re.search(r'unicode-range:\s*([^;]+);', body)
        lines.append(
            "@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;"
            "src:url(/assets/fonts/%s) format('woff2');%s}"
            % ('Geologica' if key == 'geologica' else 'Commissioner', weight, fname,
               ('unicode-range:%s;' % rng.group(1).strip()) if rng else ''))
        print('ok', fname)

# IBM Plex Mono — берём готовые файлы из соседнего проекта
SRC = r'E:\Design\vr\assets\fonts'
for want, dst in (('ibm-plex-mono-400', 'plex-400'), ('ibm-plex-mono-500', 'plex-500')):
    for suf in ('cyrillic', 'latin'):
        src = os.path.join(SRC, '%s-%s.woff2' % (want, suf))
        if os.path.exists(src):
            import shutil
            target = os.path.join(OUT, 'plex-%s-%s.woff2' % (want.rsplit('-', 1)[-1], suf))
            shutil.copy2(src, target)
            lines.append(
                "@font-face{font-family:'IBM Plex Mono';font-style:normal;font-weight:%s;font-display:swap;"
                "src:url(/assets/fonts/%s) format('woff2');}" % (want.rsplit('-', 1)[-1], os.path.basename(target)))
            print('copy', os.path.basename(target))

open(os.path.join(OUT, 'fonts.css'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('fonts.css written,', len(lines) - 1, 'faces')

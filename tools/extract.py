# -*- coding: utf-8 -*-
"""Собираем единую модель rex.moscow из данных прошлого проекта + архива."""
import ast
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SRC = r'E:\Оптимизация\Rex.moscow'
DATA = os.path.join(SRC, 'data')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(OUT, exist_ok=True)


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


products = load('products.json')
cats = load('categories.json')
pages = load('pages.json')
linking = load('linking_data.json')

# ------------------------------------------------------------------ статьи
articles = {}
for fn in ('publish_all_articles.py', 'articles_16_75_part1.py', 'articles_22_30.py',
           'articles_31_45.py', 'articles_46_60.py', 'articles_61_75.py'):
    p = os.path.join(SRC, fn)
    if not os.path.exists(p):
        continue
    try:
        tree = ast.parse(open(p, encoding='utf-8', errors='replace').read())
    except SyntaxError as e:
        print('skip', fn, e)
        continue
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)):
            continue
        if not node.targets[0].id.startswith('ARTICLE'):
            continue
        try:
            d = ast.literal_eval(node.value)
        except Exception:
            continue
        slug = d.get('slug')
        if not slug:
            continue
        if slug not in articles or len(d.get('content', '')) > len(articles[slug].get('content', '')):
            articles[slug] = d

# ------------------------------------------------------------------ продукты
def clean_name(n):
    n = re.sub(r'\s+', ' ', n).strip()
    n = n.replace('\u2044', '/')
    return n

CAT_BY_SLUG = {c['slug']: c for c in cats}

prods = []
for p in sorted(products, key=lambda x: x['id']):
    slug = p['slug']
    cs = [c['slug'] for c in p.get('categories', []) if c['slug'] in CAT_BY_SLUG]
    price = int(float(p.get('price') or 0))
    old = int(float(p.get('regular_price') or 0))
    prods.append({
        'id': p['id'],
        'slug': slug,
        'name': clean_name(p['name']),
        'cats': cs,
        'price': price,
        'old': old if old > price else 0,
        'sku': p.get('sku') or '',
        'short': re.sub(r'<[^>]+>', '', p.get('short_description') or '').strip(),
        'desc': (p.get('description') or '').strip(),
        'img': (p.get('images') or [{}])[0].get('src', ''),
        'meta_title': ((p.get('yoast_head_json') or {}).get('title') or ''),
        'meta_desc': ((p.get('yoast_head_json') or {}).get('description') or ''),
        'posts_link': (p.get('permalink') or ''),
    })

# ------------------------------------------------------------------ категории
cat_list = []
for c in cats:
    cat_list.append({
        'id': c['id'],
        'slug': c['slug'],
        'name': clean_name(c['name']),
        'parent': c['parent'],
        'count': c.get('count') or 0,
        'meta_title': ((c.get('yoast_head_json') or {}).get('title') or ''),
        'meta_desc': ((c.get('yoast_head_json') or {}).get('description') or ''),
        'desc': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c.get('description') or '')).strip(),
    })

# ------------------------------------------------------------------ страницы
page_list = []
for g in pages:
    title = re.sub(r'<[^>]+>', '', (g.get('title') or {}).get('rendered', ''))
    if not title:
        continue
    page_list.append({
        'id': g['id'],
        'slug': g['slug'],
        'title': title.strip(),
        'content': (g.get('content') or {}).get('rendered', ''),
    })

posts = sorted(articles.values(), key=lambda a: a['slug'])
for a in posts:
    a['content_len'] = len(a.get('content', ''))

calcs = [c for c in linking['calc_pages'] if c['slug'] != 'calculators']

model = {
    'max_id': max(p['id'] for p in prods),
    'products': prods,
    'cats': cat_list,
    'pages': page_list,
    'posts': posts,
    'calcs': calcs,
    'blog_cats': load('blog_categories.json'),
    'tags': load('tags_data.json'),
}
json.dump(model, open(os.path.join(OUT, 'model.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('products', len(prods))
print('cats', len(cat_list))
print('pages', len(page_list))
print('posts', len(posts), 'content', sum(a['content_len'] for a in posts))
print('calcs', len(calcs))
print('blog cats', len(model['blog_cats']), 'tags', len(model['tags']))

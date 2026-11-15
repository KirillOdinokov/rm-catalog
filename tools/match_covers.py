# -*- coding: utf-8 -*-
"""Глобальное (жадное) сопоставление обложек статей и постов."""
import difflib, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Сайты\rex.moscow"
free = json.load(open(os.path.join(BASE, "data", "_db", "free_images.json"), encoding="utf-8"))
m = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
covers = [k for k in free if re.match(r"^[A-Z][A-Za-z0-9-]{20,}\.jpg$", k)]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


pairs = []
for p in m["posts"]:
    s = norm(p["slug"])
    for c in covers:
        r = difflib.SequenceMatcher(None, norm(os.path.splitext(c)[0]), s).ratio()
        if r >= 0.55:
            pairs.append((r, p["slug"], c))
pairs.sort(reverse=True)
assigned, used_posts, used_imgs = {}, set(), set()
for r, slug, c in pairs:
    if slug in used_posts or c in used_imgs:
        continue
    assigned[slug] = (c, round(r, 2))
    used_posts.add(slug)
    used_imgs.add(c)
print("постов %d, обложек %d, сопоставлено %d" % (len(m["posts"]), len(covers), len(assigned)))
miss = [p["slug"] for p in m["posts"] if p["slug"] not in assigned]
print("без обложки (%d):" % len(miss))
for s in miss:
    print("   ", s)
low = sorted(((v[1], k, v[0]) for k, v in assigned.items()))[:6]
print("самые слабые совпадения:")
for r, k, c in low:
    print("   %.2f  %s  <-  %s" % (r, k, c))
json.dump({k: v[0] for k, v in assigned.items()},
          open(os.path.join(BASE, "data", "_db", "post_covers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# -*- coding: utf-8 -*-
"""Разбор дампа БД rex.moscow: товары WooCommerce + метаданные."""
import json
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SQL = r"E:\Сайты\rex.moscow\data\_db\rex.sql"
OUT = r"E:\Сайты\rex.moscow\data\_db"

sql = open(SQL, encoding="utf-8", errors="replace").read()


def table_rows(name):
    """Возвращает список списков значений для таблицы rex_<name>."""
    m = re.search(r"INSERT INTO `rex_%s` VALUES (.*?);\n" % re.escape(name), sql, re.S)
    if not m:
        return []
    body = m.group(1)
    rows, row, i, n = [], [], 0, len(body)
    while i < n:
        c = body[i]
        if c == "(":
            row, i = [], i + 1
            while i < n:
                while body[i] in " ,":
                    i += 1
                if body[i] == ")":
                    rows.append(row)
                    i += 1
                    break
                if body[i] == "'":
                    i += 1
                    buf = []
                    while i < n:
                        ch = body[i]
                        if ch == "\\":
                            nxt = body[i + 1]
                            buf.append({"n": "\n", "r": "\r", "t": "\t", "0": "\0"}.get(nxt, nxt))
                            i += 2
                        elif ch == "'":
                            if i + 1 < n and body[i + 1] == "'":
                                buf.append("'")
                                i += 2
                            else:
                                i += 1
                                break
                        else:
                            buf.append(ch)
                            i += 1
                    row.append("".join(buf))
                else:
                    start = i
                    while i < n and body[i] not in ",)":
                        i += 1
                    tok = body[start:i].strip()
                    row.append(None if tok.upper() == "NULL" else tok)
        else:
            i += 1
    return rows


posts = table_rows("posts")
print("posts:", len(posts))
# схема: ID, post_author, post_date, post_date_gmt, post_content, post_title, post_excerpt,
# post_status, comment_status, ping_status, post_password, post_name, to_ping, pinged,
# post_modified, post_modified_gmt, post_content_filtered, post_parent, guid, menu_order,
# post_type, post_mime_type, comment_count
products, attachments = [], []
for r in posts:
    if len(r) < 21:
        continue
    ptype = r[20]
    if ptype == "product":
        products.append(dict(
            id=int(r[0]), title=r[5], slug=r[11], content=r[4] or "", excerpt=r[6] or "",
            status=r[7], parent=int(r[17] or 0), guid=r[18] or "", modified=r[14] or ""))
    elif ptype == "attachment":
        attachments.append(dict(id=int(r[0]), title=r[5], guid=r[18] or "",
                                parent=int(r[17] or 0), mime=r[21] or ""))
print("products:", len(products), "attachments:", len(attachments))

meta = table_rows("postmeta")
print("postmeta:", len(meta))
by_post = defaultdict(dict)
for r in meta:
    if len(r) < 4:
        continue
    by_post[int(r[1])][r[2]] = r[3]

att_by_id = {a["id"]: a for a in attachments}
for p in products:
    m = by_post.get(p["id"], {})
    p["sku"] = m.get("_sku") or ""
    p["price"] = m.get("_price") or m.get("_regular_price") or ""
    thumb = m.get("_thumbnail_id")
    p["img"] = att_by_id[int(thumb)]["guid"] if thumb and int(thumb) in att_by_id else ""
    gal = m.get("_product_image_gallery") or ""
    p["gallery"] = [att_by_id[int(x)]["guid"] for x in gal.split(",") if x.strip().isdigit() and int(x) in att_by_id]
    p["cats"] = [r[2] for r in table_rows("term_relationships")] if False else []

json.dump(products, open(os.path.join(OUT, "products_db.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(attachments, open(os.path.join(OUT, "attachments_db.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("сохранено в", OUT)
print("\nпервые 25 товаров:")
for p in products[:25]:
    print("  %-6s %-70s %s" % (p["id"], p["title"][:70], p["sku"]))

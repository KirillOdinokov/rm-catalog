# -*- coding: utf-8 -*-
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Сайты\rex.moscow"
m = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
by_id = {c["id"]: c for c in m["cats"]}
print("категорий:", len(m["cats"]))
for c in sorted(m["cats"], key=lambda x: (x["parent"] or 0, x["slug"])):
    par = by_id.get(c["parent"], {}).get("slug", "")
    n = sum(1 for p in m["products"] if c["slug"] in p["cats"])
    print("%-38s %-40s parent=%-32s товаров=%d" % (c["slug"][:38], c["name"][:40], par[:32], n))

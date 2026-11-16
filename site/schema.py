# -*- coding: utf-8 -*-
"""JSON-LD: организация, сайт, товар, хлебные крошки, статья, FAQ."""
import json

import config as C


def dumps(*nodes):
    """Сериализует один или несколько узлов в один тег @graph."""
    flat = []
    for n in nodes:
        if not n:
            continue
        if isinstance(n, list):
            flat.extend([x for x in n if x])
        else:
            flat.append(n)
    if not flat:
        return ""
    doc = {"@context": "https://schema.org", "@graph": flat}
    return ('<script type="application/ld+json">%s</script>'
            % json.dumps(doc, ensure_ascii=False, separators=(",", ":")))


def _addr(street, locality, region):
    return {"@type": "PostalAddress", "streetAddress": street, "addressLocality": locality,
            "addressRegion": region, "addressCountry": C.ADDR_SCHEMA["country"]}


def org():
    """Organization + два LocalBusiness (Наро-Фоминск и Феодосия) + WebSite."""
    main = {
        "@type": "Organization",
        "@id": C.SITE + "/#org",
        "name": "РЕКС",
        "url": C.SITE,
        "description": "%s. Инженерная химия для бетона: гидроизоляция, ремонт, защита, "
                       "промышленные полы, клеевые системы, анкеровка." % C.DEALER,
        "telephone": C.PHONE,
        "email": C.EMAIL,
        "logo": {"@type": "ImageObject", "url": C.SITE + "/assets/og.jpg",
                 "width": 1200, "height": 630},
        "image": C.SITE + "/assets/og.jpg",
        "address": _addr(C.ADDR_SCHEMA["street"], C.ADDR_SCHEMA["locality"],
                          C.ADDR_SCHEMA["region"]),
        "openingHoursSpecification": [{
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "opens": "09:00", "closes": "18:00"}],
        "department": [
            {"@type": "LocalBusiness", "name": "РЕКС — Наро-Фоминск",
             "telephone": C.PHONE, "email": C.EMAIL,
             "address": _addr(C.ADDR_SCHEMA["street"], C.ADDR_SCHEMA["locality"],
                              C.ADDR_SCHEMA["region"])},
            {"@type": "LocalBusiness", "name": "РЕКС — Феодосия",
             "telephone": C.PHONE, "email": C.EMAIL,
             "address": _addr("ул. Чехова, 5", "г. Феодосия", "Республика Крым")},
        ],
    }
    site = {
        "@type": "WebSite",
        "@id": C.SITE + "/#site",
        "url": C.SITE,
        "name": "РЕКС — инженерная химия для бетона",
        "inLanguage": "ru-RU",
        "publisher": {"@id": C.SITE + "/#org"},
    }
    return [main, site]


def breadcrumbs(items, with_home=True):
    """items: [(url, label), ...] без главной (она добавится сама)."""
    chain = [("/", "Главная")] if with_home else []
    chain += [(u, l) for u, l in items if u or l]
    out = []
    pos = 0
    for u, l in chain:
        if not l:
            continue
        pos += 1
        node = {"@type": "ListItem", "position": pos, "name": l}
        if u:
            node["item"] = C.SITE + u
        out.append(node)
    return {"@type": "BreadcrumbList", "itemCount": len(out), "itemListElement": out}


def product(p, path, desc, category, pack, image=None):
    node = {
        "@type": "Product",
        "@id": C.SITE + path + "#product",
        "name": p["name"],
        "url": C.SITE + path,
        "description": desc,
        "sku": p.get("sku") or "",
        "category": category,
        "brand": {"@type": "Brand", "name": "РЕКС"},
        "manufacturer": {"@id": C.SITE + "/#org"},
    }
    if image:
        node["image"] = [C.SITE + "/assets/img/" + image]
    if pack:
        node["additionalProperty"] = [{"@type": "PropertyValue", "name": "Фасовка",
                                       "value": pack}]
    if p.get("price"):
        node["offers"] = {
            "@type": "Offer",
            "url": C.SITE + path,
            "price": str(int(p["price"])),
            "priceCurrency": "RUB",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@id": C.SITE + "/#org"},
        }
    return node


def article(a, path, cover=None, published="", modified="", section=""):
    node = {
        "@type": "Article",
        "@id": C.SITE + path + "#article",
        "headline": a["title"][:110],
        "url": C.SITE + path,
        "mainEntityOfPage": {"@type": "WebPage", "@id": C.SITE + path},
        "inLanguage": "ru-RU",
        "author": {"@type": "Organization", "name": "РЕКС", "url": C.SITE},
        "publisher": {"@id": C.SITE + "/#org"},
        "image": [C.SITE + "/assets/img/" + cover] if cover else [C.SITE + "/assets/og.jpg"],
    }
    if section:
        node["articleSection"] = section
    if a.get("meta_desc"):
        node["description"] = a["meta_desc"]
    if published:
        node["datePublished"] = published
    node["dateModified"] = modified or published or ""
    if not node["dateModified"]:
        del node["dateModified"]
    return node


def faq(items):
    qa = [{"@type": "Question", "name": q,
           "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]
    return {"@type": "FAQPage", "mainEntity": qa}


def collection(path, name, desc, items=None):
    node = {"@type": "CollectionPage", "@id": C.SITE + path,
            "url": C.SITE + path, "name": name, "description": desc, "inLanguage": "ru-RU"}
    if items:
        node["mainEntity"] = {"@type": "ItemList", "numberOfItems": len(items),
                              "itemListElement": [
                                  {"@type": "ListItem", "position": i + 1,
                                   "url": C.SITE + u, "name": n}
                                  for i, (u, n) in enumerate(items[:60])]}
    return node

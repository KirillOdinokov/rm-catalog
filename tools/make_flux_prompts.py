# -*- coding: utf-8 -*-
"""CSV с промптами для обложек статей (FLUX Klein 2 / Krea).

Колонки: id (post_id из metadata.csv), prompt (английский), aspect_ratio (16:9).

Правила промпта (по ТЗ заказчика):
- фотореализм, инженерная съёмка, без людей и рук;
- никаких длинных надписей и кириллицы; допустима только латинская марка 'Rex.moscow'
  на одном из объектов в кадре;
- соотношение сторон 16:9 (карточка блога 760×428).

Промпт собирается из четырёх частей: сцена по теме статьи, материал в кадре (по ключевому
слову заголовка), ракурс/свет (по хешу слага) и брендированный объект (по кругу).
Так у каждой статьи свой кадр, а не 200 одинаковых.

    & $py tools\\make_flux_prompts.py            # -> flux-prompts.csv
"""
import csv
import json
import os
import re
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(BASE, "articles-future", "metadata.csv")
OUT = os.path.join(BASE, "flux-prompts.csv")

# тема статьи -> сцена (первое совпадение выигрывает)
SCENES = [
    (r"тоннел|метрополитен|подземн", "the concrete lining of a deep tunnel, damp surface, work lights"),
    (r"бассейн", "the empty shell of an indoor swimming pool, tiled edge, concrete walls"),
    (r"резервуар|емкост|водонапорн|водоем", "the interior of a concrete water tank, curved wall, inspection ladder"),
    (r"подвал|фундамент|цокол", "a basement wall of a building under construction, formwork marks on the concrete"),
    (r"кровл|террас|эксплуатируем", "a flat roof terrace slab with a fresh waterproofing layer"),
    (r"шов|шпонк|герметизац|стык|примыкан", "a construction joint in a concrete wall with a waterstop profile installed"),
    (r"протечк|гидропломб|течь|фильтрац", "an active water leak seeping through a crack in a concrete wall"),
    (r"трещин|инъекц|инъектир|пакер", "a crack in a concrete ceiling with injection packers inserted and tubing attached"),
    (r"анкер|шпильк|гильз|дюбел|крепёж|закладн", "a threaded anchor rod set into a drilled hole in a concrete slab, steel base plate nearby"),
    (r"арматур|каркас|монолит|опалубк|бетонирован", "a reinforcement cage inside aluminium formwork, freshly poured concrete"),
    (r"плиточн|керамогранит|плитк|кладк|газобетон|пеноблок|кирпич", "a wall of aerated concrete blocks being laid with a notched trowel"),
    (r"стяжк|ровнител|наливн|полы|пол\b|гараж|склад|паркинг|производств", "a freshly poured self-levelling floor in an industrial hall, smooth grey surface"),
    (r"пропитк|гидрофоб|обеспыл|упрочн", "a concrete floor being treated with a clear penetrating sealer, wet sheen on the surface"),
    (r"краск|огнезащит|покрыти|эмал|декор", "a steel column being coated with a protective paint, brush marks visible"),
    (r"мембран", "a rolled HDPE membrane being unrolled over a foundation slab"),
    (r"клей|адгези|грунтовк|бетон.?контакт|праймер", "a concrete wall being primed with a roller, tacky surface ready for the next layer"),
    (r"смес|ремонт|восстановлен|торкрет|подлив", "a damaged concrete column being repaired with mortar, repaired section freshly finished"),
]
DEFAULT_SCENES = {
    "hydro": "a basement wall of a building under construction treated with a waterproofing coating",
    "repair": "a damaged concrete structure being repaired with mortar",
    "floors": "a freshly poured industrial floor in a production hall",
    "protection": "a concrete facade panel being coated with a protective compound",
    "anchor": "a steel base plate anchored into a concrete slab",
    "adhesive": "a wall of aerated concrete blocks with adhesive mortar",
}

# материал в кадре (по ключевому слову заголовка)
CUES = [
    (r"пропитк", "a clear penetrating sealer soaking into the concrete surface"),
    (r"гидрофоб", "a silane water-repellent liquid beading on the concrete"),
    (r"гидропломб", "a fast-setting hydraulic plug mortar packed into the leak"),
    (r"бетон.?контакт|бетоноконтакт|грунтовк|праймер", "a bonding primer slurry brushed onto the substrate"),
    (r"плиточн|керамогранит|плитк", "a thin bed of cementitious tile adhesive with combed ridges"),
    (r"кладк|газобетон|пеноблок|кирпич|клей.?для.?блок", "a thin-bed block adhesive joint, mortar squeezed out at the edge"),
    (r"стяжк|ровнител", "a self-levelling screed spreading into a smooth sheet"),
    (r"наливн|полы", "a glossy epoxy self-levelling floor coating"),
    (r"анкер|шпильк|гильз|дюбел|закладн|крепёж", "a two-component chemical anchor cartridge and a threaded rod"),
    (r"шпонк|шов|герметик|лент|примыкан", "a PVC waterstop profile embedded in the fresh concrete"),
    (r"мембран", "a black HDPE geomembrane sheet with welded seams"),
    (r"краск|эмал|огнезащит|покрыти|декор", "a protective coating layer with a uniform satin finish"),
    (r"ремонт|восстановлен|смес|торкрет|подлив|трещин", "a fibre-reinforced repair mortar smoothed over the damaged area"),
    (r"инъекц|пакер|смол|гел", "a resin being injected through a packer into the crack"),
    (r"добавк|модификатор|пластификатор", "a measured dose of concrete admixture poured into the mixer"),
    (r"обеспыл|упрочн", "a densified, dust-free concrete surface"),
]
DEFAULT_CUES = {
    "hydro": "a freshly applied waterproofing coating",
    "repair": "a freshly applied repair mortar",
    "floors": "a freshly applied floor coating",
    "protection": "a freshly applied protective coating",
    "anchor": "an installed chemical anchor",
    "adhesive": "a freshly applied adhesive layer",
}

ANGLES = [
    "eye-level close-up", "three-quarter view from a low angle", "slightly top-down view",
    "wide establishing shot", "tight detail shot", "diagonal composition",
]
LIGHTS = [
    "overcast daylight", "warm afternoon side light", "cool morning light from a high window",
    "mixed site lighting with a soft fill", "low sun with long shadows", "diffused light through scaffolding",
]
SETTINGS = [
    "on an active construction site", "during renovation of an industrial hall",
    "in a residential basement under construction", "inside a water-treatment facility",
    "at a road-bridge repair site", "in a warehouse with concrete columns",
]

BRAND_OBJECTS = [
    "a plain white 25 kg paper bag printed with a small clean 'Rex.moscow' logo stands at the edge of the frame",
    "a white plastic pail with a 'Rex.moscow' label on the lid sits in the foreground",
    "a steel bucket stencilled 'Rex.moscow' stands beside the work area",
    "a neat stack of white paper bags, the top one printed 'Rex.moscow', is visible in the background",
    "a white jerry can with a small 'Rex.moscow' sticker rests on the floor nearby",
]

TAIL = ("Editorial construction-chemistry photography, sharp focus on the material surface, "
        "shallow depth of field, realistic dust and texture. No people, no hands, no faces, "
        "no text overlays, no Cyrillic lettering, no watermarks, no logos other than 'Rex.moscow'.")


def pick(rx_list, text, default):
    for rx, val in rx_list:
        if re.search(rx, text):
            return val
    return default


def build(title, cluster, slug):
    t = (title or "").lower()
    scene = pick(SCENES, t, DEFAULT_SCENES.get(cluster, DEFAULT_SCENES["hydro"]))
    cue = pick(CUES, t, DEFAULT_CUES.get(cluster, DEFAULT_CUES["hydro"]))
    h = zlib.crc32(slug.encode("utf-8"))
    angle = ANGLES[h % len(ANGLES)]
    light = LIGHTS[(h // 7) % len(LIGHTS)]
    setting = SETTINGS[(h // 13) % len(SETTINGS)]
    obj = BRAND_OBJECTS[(h // 3) % len(BRAND_OBJECTS)]
    prompt = ("Photorealistic 16:9 photo for an engineering-chemistry website. "
              "Scene: %s, %s. Subject: %s. Camera: %s, %s. "
              "In the frame %s. %s"
              % (scene, setting, cue, angle, light, obj, TAIL))
    return " ".join(prompt.split())


def main():
    rows = list(csv.DictReader(open(META, encoding="utf-8-sig")))
    by_slug = {r["slug"]: r for r in rows}
    model = json.load(open(os.path.join(BASE, "data", "model.json"), encoding="utf-8"))
    posts = [p for p in model["posts"] if p.get("file")]
    posts.sort(key=lambda p: (p.get("publish_at") or "", p["slug"]))
    cat = {"gidroizolyaciya": "hydro", "remont-betona": "repair", "promyshlennye-poly": "floors",
           "zashhita-betona": "protection", "kleevye-ankernye-sistemy": "anchor"}

    out = []
    for p in posts:
        meta = by_slug.get(p["slug"])
        if not meta:
            continue
        prompt = build(p["title"], cat.get(p["category"], "hydro"), p["slug"])
        out.append((meta["post_id"], prompt, "16:9"))

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "prompt", "aspect_ratio"])
        w.writerows(out)

    print("строк:", len(out), "| уникальных промптов:", len({r[1] for r in out}), "| файл:", OUT)
    for r in out[:2]:
        print("\n%s\n%s" % (r[0], r[1]))


if __name__ == "__main__":
    main()

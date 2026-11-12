"""Build docs/data.js for the quiz.

Usage:
  python3 -I tools/extract.py --html <dir> [--json <dir>] [--geolearnr <repo>/sources] [--poles <poles.json>] > docs/data.js

Sources (all point at images hosted by geohints.com; only an index is stored here):
  --html       saved geohints.com /meta pages, named <path>.html with "/" -> "__" (signs__stop.html)
  --geolearnr  "sources" folder of github.com/lembergmax/GeoLearnr (markdown per category)
  --poles      poles.json from github.com/dntAtMe/geoguessr-quiz (MIT)
  --json       geohints-*.json files saved by the collector bookmarklet (docs/collect.html);
               a JSON category replaces the same category from the other sources
"""
import argparse, html, json, os, re

GEO = "https://geohints.com/meta/"
CARD = re.compile(r'font-bold h-12[^>]*>\s*([^<]+?)\s*</div>\s*<img[^>]*src="([^"]+)"')
SECTION = re.compile(r'<h3 class="text-xl font-semibold text-white">\s*([^<]+?)\s*</h3>')
LOGO = re.compile(r'<img\s+src="([^"]+/storage/[^"]+)"\s+alt="([^"]*)"')
DOMAIN = re.compile(r'<div class="text-white text-md">\s*([^<]+?)\s*</div>((?:\s*<div class="text-gray-500 grid text-md">\s*<div>[^<]+</div>\s*</div>)+)')
MD_ROW = re.compile(r'^(.+?) !\[\]\((https://[^)]+)\)', re.M)

HTML_CATS = {  # file key -> (label, kind)
    "bollards": ("Столбики", "photo"), "architecture": ("Архитектура", "photo"),
    "companies__post": ("Почта — логотипы", "logo"), "companies__beer": ("Пиво", "logo"),
    "companies__gasStations": ("АЗС", "logo"), "domains": ("Домены", "text"),
}
# labels for pages collected with the bookmarklet; anything else gets its path as a label
PAGE_LABELS = {
    "licensePlates": "Номера машин", "lines": "Разметка", "followCars": "Машины сопровождения",
    "googleVehicles": "Машины Google", "googleVehicles__cars": "Машины Google", "houseNumbers": "Номера домов",
    "trafficLights": "Светофоры", "utilityPoles": "Столбы ЛЭП", "postBoxes": "Почтовые ящики", "rifts": "Рифты",
    "sidewalks": "Тротуары", "nature": "Природа", "snow": "Снег", "sceneries": "Пейзажи", "phoneNumbers": "Телефонные номера",
    "currencies": "Валюты", "streetSuffix": "Типы улиц", "honey": "Мёд", "years": "Годы съёмки", "flags": "Флаги (geohints)",
    "signs": "Знаки", "signs__animalWarning": "Знаки — животные", "signs__backOfSigns": "Знаки — обратная сторона",
    "signs__busStop": "Знаки — остановки", "signs__chevrons": "Знаки — шевроны", "signs__citySigns": "Знаки — въезд в город",
    "signs__directions": "Знаки — направления", "signs__pedestrian": "Знаки — пешеходный переход",
    "signs__railwayCrossing": "Знаки — ж/д переезд", "signs__river": "Знаки — реки", "signs__roadNumbering": "Знаки — номера дорог",
    "signs__signPosts": "Знаки — стойки", "signs__speed": "Знаки — скорость", "signs__stop": "Знаки — STOP",
    "signs__streetNames": "Знаки — названия улиц", "signs__tramSpeed": "Знаки — скорость трамвая",
    "signs__tramStop": "Знаки — трамвайные остановки", "signs__yield": "Знаки — уступи дорогу",
    **{k: v[0] for k, v in HTML_CATS.items()},
}
LOGO_PAGES = ("companies", "flags", "currencies")
GL_CATS = {"Post Boxes": ("postBoxes", "Почтовые ящики"), "Rifts": ("rifts", "Рифты"), "Sidewalks": ("sidewalks", "Тротуары")}


def parse_html(path, kind):
    h = open(path, encoding="utf-8").read()
    if kind == "text":
        return [(html.unescape(c), None, d) for c, block in DOMAIN.findall(h) for d in re.findall(r'<div>([^<]+)</div>', block)]
    if kind == "photo":
        return [(html.unescape(c), u, None) for c, u in CARD.findall(h)]
    out, secs = [], list(SECTION.finditer(h))
    for i, s in enumerate(secs):
        end = secs[i + 1].start() if i + 1 < len(secs) else len(h)
        out += [(html.unescape(s.group(1)), u, html.unescape(alt)) for u, alt in LOGO.findall(h[s.end():end])]
    return out


def only_unique(rows, key):
    """Drop clues that point at more than one country (Shell logo, .eu domain)."""
    seen = {}
    for r in rows:
        seen.setdefault(key(r), set()).add(r[0])
    return [r for r in rows if len(seen[key(r)]) == 1]


def category(cid, name, kind, source, rows):
    rows = list(dict.fromkeys(rows))
    items = []
    for c, img, cap in rows:
        it = {"c": c.strip()}
        if img: it["img"] = img
        if cap: it["cap" if img else "text"] = cap
        items.append(it)
    return {"id": cid, "name": name, "kind": kind, "source": source, "items": items}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html"); ap.add_argument("--json"); ap.add_argument("--geolearnr"); ap.add_argument("--poles")
    a = ap.parse_args()
    cats = []
    if a.html:
        for key, (name, kind) in HTML_CATS.items():
            p = os.path.join(a.html, key + ".html")
            if not os.path.exists(p) or os.path.getsize(p) < 1000:
                continue
            rows = parse_html(p, kind)
            if kind == "logo": rows = only_unique(rows, lambda r: r[1])
            if kind == "text": rows = only_unique(rows, lambda r: r[2])
            cats.append(category(key, name, kind, GEO + key.replace("__", "/"), rows))
    if a.poles:
        d = json.load(open(a.poles, encoding="utf-8"))
        rows = [(e["country"], e["image_url"], None) for v in d.values() if isinstance(v, list) for e in v]
        cats.append(category("utilityPoles", "Столбы ЛЭП", "photo", GEO + "utilityPoles", rows))
    if a.geolearnr:
        for folder, (cid, name) in GL_CATS.items():
            rows = []
            for root, _, files in sorted(os.walk(os.path.join(a.geolearnr, folder))):
                for f in sorted(files):
                    if f.endswith(".md"):
                        rows += [(c, u, None) for c, u in MD_ROW.findall(open(os.path.join(root, f), encoding="utf-8").read())]
            cats.append(category(cid, name, "photo", GEO + cid, rows))
    if a.json:
        for f in sorted(os.listdir(a.json)):
            if not (f.startswith("geohints-") and f.endswith(".json")):
                continue
            d = json.load(open(os.path.join(a.json, f), encoding="utf-8"))
            key = d["page"].replace("/", "__")
            kind = "logo" if key.startswith(LOGO_PAGES) else "photo"
            rows = only_unique([(i["c"], i["img"], i.get("cap")) for i in d["items"]], lambda r: r[1])
            cats = [c for c in cats if c["id"] != key]
            cats.append(category(key, PAGE_LABELS.get(key, key), kind, GEO + d["page"], rows))
    cats = [c for c in cats if len({i["c"] for i in c["items"]}) >= 4]  # need 4 countries for the answer options
    print("window.GEO_DATA = " + json.dumps({"categories": cats}, ensure_ascii=False, separators=(",", ":")) + ";")


main()

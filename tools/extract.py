"""Build the quiz index with remote image URLs; tools/localize.py then copies the images into docs/img.

Usage:
  python3 -I tools/extract.py --html <dir> [--json <dir>] [--poles <poles.json>] [--geolearnr <repo>/sources] > data.remote.js

Sources:
  --html       geohints.com /meta pages saved from a browser, named <path>.html with "/" -> "__" (signs__stop.html)
  --json       geohints-*.json from the collector bookmarklet (tools/collect.html), same naming
  --poles      poles.json from github.com/dntAtMe/geoguessr-quiz (MIT), used when utilityPoles.html is missing
  --geolearnr  "sources" folder of github.com/lembergmax/GeoLearnr, used for post boxes when postBoxes.html is missing
"""
import argparse, html, json, os, re, sys

GEO = "https://geohints.com/meta/"
CARD = re.compile(r'font-bold h-12[^>]*>\s*([^<]+?)\s*</div>\s*<img[^>]*src="([^"]+)"')
SECTION = re.compile(r'<h3 class="text-xl font-semibold text-white">\s*([^<]+?)\s*</h3>')
LOGO = re.compile(r'<img\s+src="([^"]+/storage/[^"]+)"\s+alt="([^"]*)"')
DOMAIN = re.compile(r'<div class="text-white text-md">\s*([^<]+?)\s*</div>((?:\s*<div class="text-gray-500 grid text-md">\s*<div>[^<]+</div>\s*</div>)+)')
CUR_SEC = re.compile(r'<h2 class="text-xl font-semibold mb-2 text-blue-500 text-center">\s*([^<]+?)\s*</h2>(.*?)(?=<h2 class="text-xl font-semibold mb-2 text-blue-500|$)', re.S)
CUR = re.compile(r'<h3[^>]*>\s*([^<]+?)\s*</h3>.*?Symbol:</td>\s*<td>([^<]*)</td>.*?Status:</td>\s*<td>([^<]*)</td>', re.S)
SEQ = re.compile(r'<span class="font-bold[^"]*">\s*([^<]+?)\s*</span>|<img[^>]*src="([^"]+/storage/(?!/?logos/)[^"]+)"|<div class="text-center font-thin[^"]*">\s*([^<]*?)\s*</div>')
PHONE = re.compile(r'<div>\s*(\+[\d ]+?)\s*<span class="font-thin">\s*([^<]+?)\s*</span>\s*</div>')
SUFFIX_CARD = re.compile(r'<div class="grid items-start h-full bg-gray-800 p-4 border-white-400 border-2">\s*<div>\s*([^<]+?)\s*</div>(.*?)(?=<div class="grid items-start h-full bg-gray-800|$)', re.S)
SUFFIX_ROW = re.compile(r'<div class="font-thin">\s*([^<]+?)\s*</div>|<div class="w-full">\s*([^<]+?)\s*</div>\s*<div class="w-full font-thin">\s*([^<]*?)\s*</div>')
LINE_CARD = re.compile(r'<div class="text-white text-md p-2 grid">\s*<span class="font-bold">\s*([^<]+?)\s*</span>(.*?)(?=<div class="text-white text-md p-2 grid">|<div class="text-center text-3xl|</main|<footer|$)', re.S)
CONTINENTS = {"Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Middle East", "Central America", "Caribbean", "Antarctica"}
MD_ROW = re.compile(r'^(.+?) !\[\]\((https://[^)]+)\)', re.M)

# category id -> (label, kind, source pages). Pages of one category are merged (all signs -> "signs").
CATS = {
    "architecture": ("Архитектура", "photo", ["architecture"]),
    "bollards": ("Столбики", "photo", ["bollards"]),
    "companies": ("Компании", "logo", ["companies__post", "companies__beer", "companies__gasStations"]),
    "currencies": ("Валюты", "text", ["currencies"]),
    "domains": ("Домены", "text", ["domains"]),
    "followCars": ("Машины сопровождения", "photo", ["followCars"]),
    "licensePlates": ("Номера машин", "photo", ["licensePlates"]),
    "lines": ("Разметка", "lines", ["lines"]),
    "nature": ("Природа", "photo", ["nature"]),
    "phoneNumbers": ("Телефонные номера", "text", ["phoneNumbers"]),
    "postBoxes": ("Почтовые ящики", "photo", ["postBoxes"]),
    "sceneries": ("Пейзажи", "photo", ["sceneries"]),
    "signs": ("Знаки", "photo", ["signs"] + ["signs__" + s for s in (
        "animalWarning backOfSigns busStop chevrons citySigns directions pedestrian railwayCrossing river "
        "roadNumbering signPosts speed stop streetNames tramSpeed tramStop yield").split()]),
    "streetSuffix": ("Типы улиц", "text", ["streetSuffix"]),
    "trafficLights": ("Светофоры", "photo", ["trafficLights"]),
    "utilityPoles": ("Столбы ЛЭП", "photo", ["utilityPoles"]),
}
PER_COUNTRY_TYPE = {"signs": 2}  # max cards per (country, sign type)
SIGN_LABELS = {"animalWarning": "животные", "backOfSigns": "обратная сторона", "busStop": "остановка", "chevrons": "шевроны",
               "citySigns": "въезд в город", "directions": "направления", "pedestrian": "пешеходный переход",
               "railwayCrossing": "ж/д переезд", "river": "река", "roadNumbering": "номер дороги", "signPosts": "стойки",
               "speed": "скорость", "stop": "STOP", "streetNames": "название улицы", "tramSpeed": "скорость трамвая",
               "tramStop": "трамвайная остановка", "yield": "уступи дорогу"}


def parse_html(h, page):
    """-> list of (country, img or None, caption or None, text or None)"""
    if page == "currencies":
        out = []
        for c, block in CUR_SEC.findall(h):
            for name, sym, status in CUR.findall(block):
                if status.strip().lower() == "official":
                    # the symbol is the clue (prices on signs); the name would give the country away, so it is shown after answering
                    syms = [x.strip() for x in html.unescape(sym).split(" or ") if x.strip()]
                    if syms:
                        out.append((html.unescape(c), None, html.unescape(name), syms[0]))
        return out
    if page == "phoneNumbers":
        return [(html.unescape(c), None, None, code.replace(" ", "")) for code, c in PHONE.findall(h)]
    if page == "streetSuffix":
        out = []
        for c, block in SUFFIX_CARD.findall(h):
            lang = None
            for l, word, meaning in SUFFIX_ROW.findall(block):
                if l: lang = html.unescape(l); continue
                cap = html.unescape(meaning) + (f" · {lang}" if lang else "")
                out.append((html.unescape(c), None, cap, html.unescape(word)))
        return out
    if page == "lines":
        # roads are drawn in CSS: 3 columns (edge, centre, edge) of coloured stripes -> "W|WY|W"
        out = []
        for c, block in LINE_CARD.findall(h):
            for road in block.split("h-32 bg-gray-400")[1:]:
                cols = road.split("flex justify-center gap-2")[1:4]
                out.append((html.unescape(c), None, None, "|".join("".join(x[0].upper() for x in re.findall(r"bg-\[(\w+)\]", col)) for col in cols)))
        return out
    if page == "domains":
        return [(html.unescape(c), None, None, d) for c, block in DOMAIN.findall(h) for d in re.findall(r'<div>([^<]+)</div>', block)]
    cards = [(html.unescape(c), u, None, None) for c, u in CARD.findall(h)]
    if cards:
        return cards
    out, secs = [], list(SECTION.finditer(h))
    for i, s in enumerate(secs):
        end = secs[i + 1].start() if i + 1 < len(secs) else len(h)
        out += [(html.unescape(s.group(1)), u, html.unescape(alt) or None, None) for u, alt in LOGO.findall(h[s.end():end])]
    return out or parse_sequence(h)


def parse_sequence(h):
    """Signs, plates: a country name, then its images, each optionally followed by a caption (speed value, plate type)."""
    out, country, open_ = [], None, []
    for name, src, cap in SEQ.findall(h):
        if name:
            name = html.unescape(name).strip()
            if name not in CONTINENTS:
                country, open_ = name, []
        elif src and country:
            out.append([country, src, None, None]); open_.append(out[-1])
        elif cap is not None and open_:
            cap = html.unescape(cap).replace("\u200c", "").strip()
            if cap:
                for r in open_: r[2] = cap
            open_ = []
    return [tuple(r) for r in out]


def only_unique(rows):
    """Drop clues that point at more than one country (Shell logo, .eu, Euro)."""
    key = lambda r: r[1] or r[3]
    seen = {}
    for r in rows:
        seen.setdefault(key(r), set()).add(r[0])
    return [r for r in rows if len(seen[key(r)]) == 1]


def to_items(rows):
    items = []
    for c, img, cap, text in dict.fromkeys(rows):
        it = {"c": c.strip()}
        if img: it["img"] = img
        if text: it["text"] = text
        if cap: it["cap"] = cap
        items.append(it)
    return items


def main():
    ap = argparse.ArgumentParser()
    for f in ("--html", "--json", "--poles", "--geolearnr"): ap.add_argument(f)
    a = ap.parse_args()
    found = {}  # page -> rows
    for page in [p for _, _, ps in CATS.values() for p in ps]:
        rows = None
        jp = a.json and os.path.join(a.json, f"geohints-{page}.json")
        hp = a.html and os.path.join(a.html, page + ".html")
        if jp and os.path.exists(jp):
            d = json.load(open(jp, encoding="utf-8"))
            rows = [(i["c"], i.get("img"), i.get("cap"), i.get("text")) for i in d["items"]]
        elif hp and os.path.exists(hp) and os.path.getsize(hp) > 1000:
            rows = parse_html(open(hp, encoding="utf-8").read(), page)
        if rows:
            if page.startswith("signs__"):  # name the sign type after answering
                rows = [(c, u, SIGN_LABELS[page[7:]] + (f": {cap}" if cap else ""), t) for c, u, cap, t in rows]
            found[page] = rows
    if a.poles and "utilityPoles" not in found:
        d = json.load(open(a.poles, encoding="utf-8"))
        found["utilityPoles"] = [(e["country"], e["image_url"], None, None) for v in d.values() if isinstance(v, list) for e in v]
    if a.geolearnr and "postBoxes" not in found:
        rows = []
        for root, _, files in sorted(os.walk(os.path.join(a.geolearnr, "Post Boxes"))):
            for f in sorted(files):
                if f.endswith(".md"):
                    rows += [(c, u, None, None) for c, u in MD_ROW.findall(open(os.path.join(root, f), encoding="utf-8").read())]
        found["postBoxes"] = rows

    cats, missing = [], []
    for cid, (name, kind, pages) in CATS.items():
        rows = [r for p in pages for r in found.get(p, [])]
        missing += [p for p in pages if p not in found]
        if kind == "lines":
            pats = {}
            for c, _, _, p in rows: pats.setdefault(c.strip(), []).append(p) if p not in pats.get(c.strip(), []) else None
            items = [{"c": c, "lines": ps} for c, ps in pats.items()]
        else:
            items = to_items(only_unique(rows))
        if cid in PER_COUNTRY_TYPE:  # e.g. dozens of speed plates per country: keep a few of each sign type
            seen, kept = {}, []
            for it in items:
                k = (it["c"], (it.get("cap") or "").split(":")[0])
                seen[k] = seen.get(k, 0) + 1
                if seen[k] <= PER_COUNTRY_TYPE[cid]:
                    kept.append(it)
            items = kept
        if len({i["c"] for i in items}) >= 4:  # need 4 countries for the answer options
            cats.append({"id": cid, "name": name, "kind": kind, "source": GEO + pages[0].replace("__", "/"), "items": items})
    # Street View countries as listed on the currencies page: the driving-side test asks about these
    coverage = sorted({r[0] for r in found.get("currencies", [])})
    print("window.GEO_DATA = " + json.dumps({"categories": cats, "coverage": coverage}, ensure_ascii=False, separators=(",", ":")) + ";")
    print("missing pages: " + (", ".join(missing) or "none"), file=sys.stderr)


main()

"""Build data.json for the quiz from saved geohints.com /meta pages.

Usage: python3 -I tools/extract.py <dir-with-saved-html> > docs/data.js
File names: <category>.html, with "/" in the path written as "__" (signs__stop.html).
Only an index (country, image URL, source page) is extracted; the images stay on geohints.
"""
import re, sys, os, json, html

CARD = re.compile(r'font-bold h-12[^>]*>\s*([^<]+?)\s*</div>\s*<img[^>]*src="([^"]+)"')
SECTION = re.compile(r'<h3 class="text-xl font-semibold text-white">\s*([^<]+?)\s*</h3>')
LOGO = re.compile(r'<img\s+src="([^"]+/storage/[^"]+)"\s+alt="([^"]*)"')

LABELS = {
    "bollards": "Bollards", "architecture": "Architecture", "companies__post": "Postal logos",
    "companies__beer": "Beer", "companies__gasStations": "Gas stations",
}

def parse(path):
    h = open(path, encoding="utf-8").read()
    out = [(html.unescape(c), u, None) for c, u in CARD.findall(h)]
    if out:
        return out
    # company layout: <h3>Country</h3> followed by logo tiles
    secs = list(SECTION.finditer(h))
    for i, s in enumerate(secs):
        end = secs[i + 1].start() if i + 1 < len(secs) else len(h)
        for u, alt in LOGO.findall(h[s.end():end]):
            out.append((html.unescape(s.group(1)), u, html.unescape(alt)))
    return out

def main(d):
    cats = []
    for f in sorted(os.listdir(d)):
        key = f[:-5]
        if not f.endswith(".html") or key not in LABELS:
            continue
        rows = parse(os.path.join(d, f))
        if key.startswith("companies"):
            # A brand that is listed in several countries is not a clue: keep logos seen in one country only.
            seen = {}
            for c, u, alt in rows:
                seen.setdefault(u, set()).add(c)
            rows = [r for r in rows if len(seen[r[1]]) == 1]
        rows = list(dict.fromkeys(rows))
        items = [{"c": c, "img": u, **({"cap": alt} if alt else {})} for c, u, alt in rows]
        if items:
            cats.append({"id": key, "name": LABELS[key], "logo": key.startswith("companies"),
                         "source": "https://geohints.com/meta/" + key.replace("__", "/"), "items": items})
    print("window.GEO_DATA = " + json.dumps({"categories": cats}, ensure_ascii=False, separators=(",", ":")) + ";")

main(sys.argv[1])

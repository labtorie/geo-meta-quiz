"""Write docs/collect.html: an install page with the collector bookmarklet (tools/bookmarklet.js)."""
import re, urllib.parse, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
src = (root / "tools/bookmarklet.js").read_text(encoding="utf-8")
src = re.sub(r"^/\*.*?\*/\s*", "", src, flags=re.S)  # drop the header comment
href = "javascript:" + urllib.parse.quote(src, safe="()[]{}=;:,.'!*/+-_~@$?&<>|^`")
page = (root / "tools/collect.template.html").read_text(encoding="utf-8").replace("{{HREF}}", href.replace('"', "%22"))
(root / "docs/collect.html").write_text(page, encoding="utf-8")
print(f"docs/collect.html written, bookmarklet {len(href)} chars")

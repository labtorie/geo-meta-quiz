"""Copy the quiz images into docs/img and write docs/data.js with local paths.

Usage: python3 -I tools/localize.py build/data.remote.js [--offline] [--delay SECONDS]
  --offline  use only what is already in docs/img, download nothing
  --delay    pause after each download (default 0.15)
Downloads one file at a time with a short pause and keeps what is already on disk, so it can be re-run.
Photos are shrunk to 960px JPEG and raster logos over 150 KB to 480px (macOS sips); SVGs and flags are kept as they are.
Stops after 10 failed downloads in a row; items whose image could not be fetched are left out of data.js.
"""
import hashlib, json, os, pathlib, re, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FLAG_CODES = ("ad ae af ag ai al am ao ar as at au aw ax az ba bb bd be bf bg bh bi bj bl bm bn bo bq br bs bt bw by bz ca cc cd cf "
              "cg ch ci ck cl cm cn co cr cu cv cw cx cy cz de dj dk dm do dz ec ee eg eh er es et fi fj fk fm fo fr ga gb gd ge gf gg "
              "gh gi gl gm gn gp gq gr gs gt gu gw gy hk hn hr ht hu id ie il im in io iq ir is it je jm jo jp ke kg kh ki km kn kp kr "
              "kw ky kz la lb lc li lk lr ls lt lu lv ly ma mc md me mf mg mh mk ml mm mn mo mp mq mr ms mt mu mv mw mx my mz na nc ne "
              "nf ng ni nl no np nr nu nz om pa pe pf pg ph pk pl pm pn pr ps pt pw py qa re ro rs ru rw sa sb sc sd se sg sh si sj sk "
              "sl sm sn so sr ss st sv sx sy sz tc td tf tg th tj tk tl tm tn to tr tt tv tw tz ua ug us uy uz va vc ve vg vi vn vu wf "
              "ws xk ye yt za zm zw").split()
UA = "geo-meta-quiz image copier"
fails_in_row = 0
OFFLINE = "--offline" in sys.argv
DELAY = float(sys.argv[sys.argv.index("--delay") + 1]) if "--delay" in sys.argv else 0.15


def fetch(url, dest):
    global fails_in_row
    if dest.exists() and dest.stat().st_size > 0:
        return True
    if OFFLINE or fails_in_row >= 10:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            data = r.read()
    except Exception as e:
        fails_in_row += 1
        print(f"FAIL {url}: {e}", file=sys.stderr)
        if fails_in_row == 10:
            print("10 failures in a row, stopping downloads", file=sys.stderr)
        return False
    fails_in_row = 0
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.rename(dest)
    time.sleep(DELAY)
    return True


MAX_SIDE = {"signs": 640}  # px; other photo categories get 960


def size_of(f):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(f)], capture_output=True, text=True).stdout
    nums = [int(x) for x in re.findall(r"pixel(?:Width|Height): (\d+)", out)]
    return max(nums) if nums else 0


def shrink(src, dest, max_side=960):
    """Photo -> JPEG q70, longest side at most max_side (never enlarged). Returns the file actually used."""
    if dest.exists():
        return dest
    resize = ["-Z", str(max_side)] if size_of(src) > max_side else []
    r = subprocess.run(["sips", *resize, "-s", "format", "jpeg", "-s", "formatOptions", "70", str(src), "--out", str(dest)],
                       capture_output=True)
    if r.returncode == 0 and dest.exists():
        src.unlink()
        return dest
    return src


def shrink_logo(f):
    """Raster logos over 150 KB -> at most 480px, same format."""
    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and f.stat().st_size > 150_000:
        subprocess.run(["sips", "-Z", "480", str(f)], capture_output=True)


def main(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8").strip()
    data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    total = sum(1 for c in data["categories"] for i in c["items"] if "img" in i)
    done = dropped = 0
    names = {}
    for cat in data["categories"]:
        keep = []
        for it in cat["items"]:
            if "img" not in it:
                keep.append(it); continue
            name = it["img"].split("?")[0].rstrip("/").split("/")[-1]
            # same name for different URLs (case-insensitive disk, x.png vs x.jpg after conversion): add a short hash
            stem, ext = os.path.splitext(name)
            key = (cat["id"], stem.lower())
            if names.setdefault(key, it["img"]) != it["img"]:
                name = f"{stem}-{hashlib.sha1(it['img'].encode()).hexdigest()[:6]}{ext}"
            raw_file = DOCS / "img" / cat["id"] / ("orig-" + name)
            raster = os.path.splitext(name)[1].lower() in (".jpg", ".jpeg", ".png", ".webp")
            as_photo = cat["kind"] == "photo" and raster
            final = DOCS / "img" / cat["id"] / (os.path.splitext(name)[0] + ".jpg" if as_photo else name)
            ok = final.exists() or fetch(it["img"], raw_file)
            if ok and not final.exists():
                final = shrink(raw_file, final, MAX_SIDE.get(cat["id"], 960)) if as_photo else raw_file.rename(final) or final
            if ok and cat["kind"] == "logo":
                shrink_logo(final)
            done += 1
            if ok:
                keep.append({**it, "img": final.relative_to(DOCS).as_posix()})
            else:
                dropped += 1
            if done % 100 == 0:
                print(f"{done}/{total}", file=sys.stderr)
        cat["items"] = keep
    flags = []
    for code in FLAG_CODES:
        if fetch(f"https://flagcdn.com/w320/{code}.png", DOCS / "img" / "flags" / f"{code}.png"):
            flags.append(code)
    data["flags"] = flags
    # a category needs 4 countries for the answer options; hide the ones whose images are not here yet
    data["categories"] = [c for c in data["categories"] if len({i["c"] for i in c["items"]}) >= 4]
    (DOCS / "data.js").write_text("window.GEO_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"done: {done - dropped} images, {dropped} dropped, {len(flags)} flags", file=sys.stderr)


main(sys.argv[1])

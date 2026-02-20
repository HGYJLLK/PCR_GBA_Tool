"""
Download PCR character icons from redive.estertion.win/icon/unit/
Names are parsed from the inline JavaScript `names={...}` object on the icon index page.
Only star-3 icons (suffix 31) with a name are downloaded.

Output layout:
    assets/icons/unit/
        100131.png   ← {unit_id}.png  (star-3 icon)
        ...
    assets/icons/unit_names.json   ← {unit_id: name}

Usage:
    python dev_tools/download_icons.py
    python dev_tools/download_icons.py --out assets/icons/unit --workers 16
    python dev_tools/download_icons.py --clean   # delete existing PNGs first
"""

import argparse
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ensure stdout handles Japanese / other non-ASCII characters on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from PIL import Image

ICON_BASE = "https://redive.estertion.win/icon/unit/"
OUT_DIR   = "./assets/icons/unit"
WORKERS   = 16
TIMEOUT   = 15


# ── 1. parse names from icon page inline JS ───────────────────────────────────
def fetch_names(session):
    """
    Fetch the icon index page and extract the inline `names={...}` JS object.
    Returns {unit_id_str: name_str}.
    """
    print(f"Fetching icon index: {ICON_BASE}")
    r = session.get(ICON_BASE, timeout=TIMEOUT)
    r.raise_for_status()

    # The page contains:  names={"100131":"\u30d2\u30e8\u30ea",...};
    m = re.search(r'\bnames\s*=\s*(\{[^;]+\})', r.text)
    if not m:
        print("ERROR: could not find names={} in page source")
        sys.exit(1)

    names = json.loads(m.group(1))
    print(f"  Parsed {len(names)} named icons from page")
    return names, r.text


# ── 2. build download list from icon page filenames ───────────────────────────
def fetch_icon_list(html):
    """Return sorted list of current-version filenames (no date suffix)."""
    filenames = sorted(set(re.findall(r'href="(\d+\.webp)"', html)))
    print(f"  Found {len(filenames)} icons total on page")
    return filenames


# ── 3. download one icon ──────────────────────────────────────────────────────
def download_one(session, filename, out_dir):
    """Download webp, convert to PNG, save as {id}.png. Returns (id, ok, msg)."""
    unit_id  = filename.replace(".webp", "")
    out_path = os.path.join(out_dir, f"{unit_id}.png")

    if os.path.exists(out_path):
        return unit_id, True, "skip"

    try:
        r = session.get(ICON_BASE + filename, timeout=TIMEOUT)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img.save(out_path, "PNG")
        return unit_id, True, "ok"
    except Exception as e:
        return unit_id, False, str(e)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",     default=OUT_DIR)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--clean",   action="store_true",
                        help="Delete all existing PNGs in out dir before downloading")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # --- clean existing PNGs ---
    if args.clean:
        existing = [f for f in os.listdir(args.out) if f.endswith(".png")]
        if existing:
            print(f"Cleaning {len(existing)} existing PNGs from {args.out} ...")
            for fn in existing:
                os.remove(os.path.join(args.out, fn))
            print("  Done.\n")

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"

    # --- names + icon list (single request) ---
    names, html = fetch_names(session)
    all_filenames = fetch_icon_list(html)

    # build full name mapping: expand star-3 keys → all star variants
    # names keys are like "100131" (char prefix "1001", suffix "31")
    # we want to also cover "100111", "100121", "100161", etc.
    named_prefixes = {uid[:-2]: name for uid, name in names.items()}  # "1001" → "ヒヨリ"
    full_names = {}
    for fn in all_filenames:
        uid = fn.replace(".webp", "")
        prefix = uid[:-2]
        if prefix not in named_prefixes:
            continue
        # last 2 digits of uid: first digit = star level (e.g. "31" → 3, "11" → 1)
        suffix = uid[-2:]
        star = int(suffix[0]) if suffix[0].isdigit() and suffix[0] != "0" else None
        base_name = named_prefixes[prefix]
        full_names[uid] = f"{base_name} ★{star}" if star else base_name

    # save expanded name mapping
    names_path = os.path.join(os.path.dirname(args.out), "unit_names.json")
    with open(names_path, "w", encoding="utf-8") as f:
        json.dump(full_names, f, ensure_ascii=False, indent=2)
    print(f"  Name mapping saved → {names_path}  ({len(full_names)} entries)\n")

    # download all variants of named characters
    filenames = [fn for fn in all_filenames if fn.replace(".webp", "") in full_names]
    print(f"  Downloading {len(filenames)} icons for {len(named_prefixes)} characters "
          f"(skipping {len(all_filenames) - len(filenames)} unnamed)\n")

    ok = skip = fail = 0
    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(download_one, session, fn, args.out): fn
            for fn in filenames
        }
        for i, f in enumerate(as_completed(futures), 1):
            unit_id, success, msg = f.result()
            if msg == "skip":
                skip += 1
            elif success:
                ok += 1
                name = full_names.get(unit_id, "")
                print(f"  {unit_id}  {name}")
            else:
                fail += 1
                print(f"  FAIL {unit_id}: {msg}")

            if i % 50 == 0 or i == len(filenames):
                elapsed = time.perf_counter() - t0
                print(f"  [{i}/{len(filenames)}] "
                      f"ok={ok} skip={skip} fail={fail} ({elapsed:.1f}s)")

    print(f"\nDone. {ok} downloaded, {skip} skipped, {fail} failed")
    print(f"Icons  → {args.out}/")
    print(f"Names  → {names_path}")


if __name__ == "__main__":
    main()

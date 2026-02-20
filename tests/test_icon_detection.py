"""
Character detection using downloaded icons from assets/icons/unit/.

Uses cv2.matchTemplate (grayscale) against the character-select ROI.
Templates are loaded from assets/icons/unit/*.png and names from
assets/icons/unit_names.json.

By default only star-3 icons (suffix 31) are used — one per character.
Pass --all-stars to use every downloaded variant.

Center-crop mode (--crop):
    The downloaded 128x128 icons are the same portraits used in the game's
    character-select cards.  The card displays the icon at ~112px; the manually-
    annotated templates capture only the central ~55px face region (≈58% of the
    card, ≈70px of the source icon).  Use --crop to replicate this: a square
    crop of the given percentage of the icon's width is taken from the centre,
    then resized to --size x --size before matching.

Usage:
    python tests/test_icon_detection.py
    python tests/test_icon_detection.py --size 55 --thresh 0.80 --all-stars
    python tests/test_icon_detection.py --crop 0.55 --size 55 --thresh 0.80
"""

import argparse
import json
import os
import sys

sys.path.insert(0, "./")

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from module.logger import logger

# ── constants ─────────────────────────────────────────────────────────────────
ICONS_DIR         = "./assets/icons/unit"
ICONS_DIR_CROPPED = "./assets/icons/unit_cropped"
NAMES_FILE        = "./assets/icons/unit_names.json"
MASK_PATH   = "./assets/mask/MASK_CHARACTER_LIST.png"
OUTPUT_DIR  = "./tests/output"
OUTPUT_FILE = "icon_detection_result.png"

ICON_SIZE   = 55          # resize icons to this (matches on-screen character cell)
THRESHOLD   = 0.80
STAR3_ONLY  = True        # default: one icon per character (star-3 version)
CROP_RATIO  = 0.0         # 0 = no crop; >0 = keep this fraction of center (e.g. 0.55)

FONT_PATHS = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
]


# ── load templates ────────────────────────────────────────────────────────────
def load_templates(icons_dir, names, icon_size, star3_only, crop_ratio=0.0):
    """
    Load PNG icons, optionally center-crop, resize, convert to grayscale.

    crop_ratio: fraction of the icon width to keep from the centre (0 = no crop).
                e.g. 0.55 keeps the central 55% of a 128px icon → 70px crop → resize to icon_size.

    Returns list of (unit_id, display_name, gray_template).
    """
    templates = []
    files = sorted(f for f in os.listdir(icons_dir) if f.endswith(".png"))

    for fn in files:
        uid = fn.replace(".png", "")
        if uid not in names:
            continue
        if star3_only and not uid.endswith("31"):
            continue

        path = os.path.join(icons_dir, fn)
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            logger.warning(f"Cannot read {path}")
            continue

        # RGBA → BGR (composite on white so transparent corners don't confuse matcher)
        if img.shape[2] == 4:
            alpha = img[:, :, 3:4].astype(float) / 255.0
            bgr   = img[:, :, :3].astype(float)
            bgr   = (bgr * alpha + 255 * (1 - alpha)).astype(np.uint8)
        else:
            bgr = img

        # center crop — replicate the manual-annotation style
        if crop_ratio > 0.0:
            h, w = bgr.shape[:2]
            crop_h = int(round(h * crop_ratio))
            crop_w = int(round(w * crop_ratio))
            y0 = (h - crop_h) // 2
            x0 = (w - crop_w) // 2
            bgr = bgr[y0:y0 + crop_h, x0:x0 + crop_w]

        bgr  = cv2.resize(bgr, (icon_size, icon_size), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        templates.append((uid, names[uid], gray))

    return templates


# ── mask ROI ──────────────────────────────────────────────────────────────────
def get_mask_roi(path):
    m = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if m is None:
        return None
    rows = np.where(m.max(axis=1) > 0)[0]
    cols = np.where(m.max(axis=0) > 0)[0]
    if rows.size == 0 or cols.size == 0:
        return None
    return int(rows[0]), int(rows[-1]) + 1, int(cols[0]), int(cols[-1]) + 1


# ── detection ─────────────────────────────────────────────────────────────────
def detect(image_rgb, templates, roi, threshold):
    """
    Run matchTemplate over the ROI for every template.

    Returns list of (display_name, (x1,y1,x2,y2), sim) sorted by sim desc.
    """
    if roi:
        ry1, ry2, rx1, rx2 = roi
        crop   = image_rgb[ry1:ry2, rx1:rx2]
        ox, oy = rx1, ry1
    else:
        crop   = image_rgb
        ox, oy = 0, 0

    gray_roi = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hits = []

    for uid, name, tmpl in templates:
        th, tw = tmpl.shape[:2]
        if gray_roi.shape[0] < th or gray_roi.shape[1] < tw:
            continue
        res = cv2.matchTemplate(gray_roi, tmpl, cv2.TM_CCOEFF_NORMED)
        _, sim, _, (mx, my) = cv2.minMaxLoc(res)
        if sim >= threshold:
            hits.append((name, (ox + mx, oy + my, ox + mx + tw, oy + my + th), sim))

    hits.sort(key=lambda x: -x[2])
    return hits


# ── visualise ─────────────────────────────────────────────────────────────────
def draw_results(image_rgb, detections):
    pil = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(pil)

    font = None
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                font = ImageFont.truetype(p, 14)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    for name, (x1, y1, x2, y2), sim in detections:
        draw.rectangle([x1, y1, x2, y2], outline=(0, 220, 0), width=2)
        label = f"{name} {sim:.2f}"
        bb = draw.textbbox((0, 0), label, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        ty = y1 - th - 4 if y1 - th - 4 >= 0 else y2 + 2
        draw.rectangle([x1, ty - 1, x1 + tw + 4, ty + th + 1], fill=(0, 0, 0))
        draw.text((x1 + 2, ty), label, fill=(0, 255, 0), font=font)

    return np.array(pil)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size",       type=int,   default=ICON_SIZE,
                        help="Resize icons to NxN before matching (default 55)")
    parser.add_argument("--thresh",     type=float, default=THRESHOLD,
                        help="Similarity threshold (default 0.80)")
    parser.add_argument("--crop",       type=float, default=CROP_RATIO,
                        help="Center-crop fraction before resize (0=off, e.g. 0.45 keeps "
                             "central 45%% of icon — mimics manual-annotation crop)")
    parser.add_argument("--use-cropped", action="store_true",
                        help=f"Use pre-cropped icons from {ICONS_DIR_CROPPED} "
                             "(generated by dev_tools/crop_icons.py) — no further crop applied")
    parser.add_argument("--all-stars",  action="store_true",
                        help="Use all star variants instead of star-3 only")
    parser.add_argument("--screenshot", type=str,   default=None,
                        help="Path to a screenshot PNG to use instead of live capture")
    args = parser.parse_args()

    star3_only = not args.all_stars

    # load name mapping
    with open(NAMES_FILE, encoding="utf-8") as f:
        names = json.load(f)

    # load templates
    if args.use_cropped:
        icons_dir = ICONS_DIR_CROPPED
        crop_ratio = 0.0   # already cropped
        crop_info  = " [pre-cropped]"
    else:
        icons_dir  = ICONS_DIR
        crop_ratio = args.crop
        crop_info  = f", center-crop={args.crop:.0%}" if args.crop > 0 else ""
    templates = load_templates(icons_dir, names, args.size, star3_only, crop_ratio)
    logger.info(f"Loaded {len(templates)} templates "
                f"({'star-3 only' if star3_only else 'all stars'}), "
                f"size={args.size}x{args.size}, thresh={args.thresh}{crop_info}")

    # mask ROI
    roi = get_mask_roi(MASK_PATH)
    if roi:
        ry1, ry2, rx1, rx2 = roi
        logger.info(f"Mask ROI: x={rx1}-{rx2}, y={ry1}-{ry2}")
    else:
        logger.warning("Mask not found, using full frame")

    # get screenshot
    if args.screenshot:
        logger.info(f"Loading screenshot: {args.screenshot}")
        pil = Image.open(args.screenshot).convert("RGB")
        image_rgb = np.array(pil)
    else:
        # lazy import Device only when doing live capture
        try:
            from module.config.config import PriconneConfig
            from module.device.device import Device
        except ImportError as e:
            logger.error(f"Device import failed: {e}")
            logger.error("Use --screenshot <path> to run without a device connection.")
            sys.exit(1)
        config = PriconneConfig("maple", "Pcr")
        device = Device(config)
        device.disable_stuck_detection()
        logger.info("Taking screenshot...")
        device.screenshot()
        image_rgb = device.image.copy()

    logger.info(f"Screenshot size: {image_rgb.shape[1]}x{image_rgb.shape[0]}")

    # detect
    logger.hr("Detection", level=1)
    hits = detect(image_rgb, templates, roi, args.thresh)

    # print results
    if hits:
        logger.info(f"Detected {len(hits)} characters:")
        for i, (name, area, sim) in enumerate(hits, 1):
            logger.info(f"  {i:3d}. {name:<20}  sim={sim:.3f}  area={area}")
    else:
        logger.warning("No characters detected. "
                       "Try --thresh 0.70 or check the game is on character-select screen.")

    # save visualisation
    result = draw_results(image_rgb, hits)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    Image.fromarray(result).save(out_path)
    logger.info(f"Result saved → {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()

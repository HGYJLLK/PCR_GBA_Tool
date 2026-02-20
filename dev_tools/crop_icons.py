"""
Center-crop downloaded unit icons to replicate the manually-annotated template style.

The manually-annotated templates (assets/character/TEMPLATE_*.png) capture
the central face area of the character portrait as it appears in the game's
character-select cards (~55 px out of a ~112 px card).

This script takes the same 128×128 icons from assets/icons/unit/, crops the
central fraction of the image (default 45 %), and saves the result resized
to a target size (default 55×55) into assets/icons/unit_cropped/.

Usage:
    python dev_tools/crop_icons.py
    python dev_tools/crop_icons.py --crop 0.45 --size 55
    python dev_tools/crop_icons.py --crop 0.40 --size 60 --out assets/icons/unit_cropped
"""

import argparse
import os

import cv2
import numpy as np

SRC_DIR  = "./assets/icons/unit"
OUT_DIR  = "./assets/icons/unit_cropped"
CROP     = 0.40   # keep central 40 % of icon width/height
SIZE     = 50     # output px (square)


def process_icon(path, crop_ratio, size):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None

    # RGBA → BGR composited on white
    if img.ndim == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3:4].astype(float) / 255.0
        bgr   = img[:, :, :3].astype(float)
        bgr   = (bgr * alpha + 255 * (1 - alpha)).astype(np.uint8)
    else:
        bgr = img

    # center crop
    h, w = bgr.shape[:2]
    ch = int(round(h * crop_ratio))
    cw = int(round(w * crop_ratio))
    y0 = (h - ch) // 2
    x0 = (w - cw) // 2
    bgr = bgr[y0:y0 + ch, x0:x0 + cw]

    # resize
    bgr = cv2.resize(bgr, (size, size), interpolation=cv2.INTER_AREA)
    return bgr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src",  default=SRC_DIR)
    parser.add_argument("--out",  default=OUT_DIR)
    parser.add_argument("--crop", type=float, default=CROP,
                        help="Fraction of icon width/height to keep from centre (default 0.45)")
    parser.add_argument("--size", type=int,   default=SIZE,
                        help="Output icon size in pixels (default 55)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing files")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    files = sorted(f for f in os.listdir(args.src) if f.endswith(".png"))
    ok = skip = fail = 0

    for fn in files:
        out_path = os.path.join(args.out, fn)
        if os.path.exists(out_path) and not args.force:
            skip += 1
            continue

        result = process_icon(os.path.join(args.src, fn), args.crop, args.size)
        if result is None:
            print(f"FAIL: {fn}")
            fail += 1
            continue

        cv2.imwrite(out_path, result)
        ok += 1

    total = ok + skip + fail
    print(f"Done. {total} icons: {ok} written, {skip} skipped (already exist), {fail} failed")
    print(f"crop={args.crop:.0%}  size={args.size}x{args.size}  -> {args.out}/")


if __name__ == "__main__":
    main()

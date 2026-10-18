r"""Prepare benchmark photos: fix rotation, remove EXIF (GPS!), shrink, save as JPEG.

Put your original photos in benchmark/raw/ named like their manifest id
(for example indoor_01.jpg or text_03.png). The cleaned copies go to benchmark/images/.
Your originals are never changed.

Usage (from backend/, venv active):
    python scripts/strip_and_resize.py
"""
from pathlib import Path

from PIL import Image, ImageOps

RAW = Path("benchmark/raw")
OUT = Path("benchmark/images")
MAX_SIDE = 1600

RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

files = [p for p in sorted(RAW.iterdir()) if p.is_file()]
if not files:
    print(f"No files in {RAW}. Copy your photos there first (named like indoor_01.jpg).")

for src in files:
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            dst = OUT / f"{src.stem}.jpg"
            im.save(dst, format="JPEG", quality=85, optimize=True)
            print(f"{src.name} -> {dst.name} ({im.width}x{im.height}, {dst.stat().st_size // 1024} KB)")
    except (OSError, ValueError) as exc:
        print(f"skipped {src.name}: {exc}")

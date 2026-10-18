r"""Check the benchmark manifest and photos. Run it as often as you like.

Usage (from backend/, venv active):
    python scripts/check_manifest.py
    python scripts/check_manifest.py --strict     (exit code 1 if anything is missing)
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

IMAGES = Path("benchmark/images")
MANIFEST = IMAGES / "manifest.csv"
GPS_TAG = 34853
CATEGORIES = {"indoor": "describe", "outdoor": "describe", "text": "read",
              "product": "product", "currency": "currency", "find": "find"}
PER_CATEGORY = 10
REQUIRED = {
    "indoor": ["must_mention", "must_not_mention"],
    "outdoor": ["must_mention", "must_not_mention"],
    "text": ["exact_text"],
    "product": ["exact_text", "must_mention"],
    "currency": ["must_mention"],
    "find": ["must_mention"],
}

parser = argparse.ArgumentParser()
parser.add_argument("--strict", action="store_true")
args = parser.parse_args()

if not MANIFEST.exists():
    sys.exit(f"{MANIFEST} not found. Run: python scripts/make_manifest.py")

try:
    with MANIFEST.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
except UnicodeDecodeError:
    sys.exit("The manifest is not saved as UTF-8. In Excel use 'CSV UTF-8', or edit it in VS Code.")


def bad_groups(value: str) -> bool:
    """must_mention format: groups separated by |, alternatives inside a group separated by /."""
    return any(not alt.strip() for group in value.split("|") for alt in group.split("/"))


problems: dict[str, list[str]] = {}
photographed = Counter()
ready = Counter()
seen_ids: set[str] = set()

for row in rows:
    pid = (row.get("id") or "").strip()
    issues: list[str] = []
    cat = row.get("category", "")
    if pid in seen_ids:
        issues.append("duplicate id")
    seen_ids.add(pid)
    if cat not in CATEGORIES:
        issues.append(f"unknown category {cat!r}")
    elif row.get("mode") != CATEGORIES[cat]:
        issues.append(f"mode should be {CATEGORIES[cat]!r}")

    path = IMAGES / (row.get("file") or "")
    if not path.is_file():
        issues.append("photo missing")
    else:
        photographed[cat] += 1
        try:
            with Image.open(path) as im:
                if min(im.size) < 400:
                    issues.append(f"photo too small {im.size}")
                if im.getexif().get(GPS_TAG):
                    issues.append("photo still has GPS data (run strip_and_resize.py)")
            if path.stat().st_size > 4 * 1024 * 1024:
                issues.append("photo larger than 4 MB")
        except OSError as exc:
            issues.append(f"photo unreadable: {exc}")

    for field in REQUIRED.get(cat, []) + ["source", "license"]:
        if not (row.get(field) or "").strip():
            issues.append(f"{field} empty")
    for field in ("must_mention", "must_not_mention"):
        value = (row.get(field) or "").strip()
        if value and bad_groups(value):
            issues.append(f"{field} has an empty group or alternative")

    problems[pid] = issues
    if not issues:
        ready[cat] += 1

print(f"{'category':<10}{'photos':>8}{'ready':>8}")
for cat in CATEGORIES:
    print(f"{cat:<10}{photographed[cat]:>5}/{PER_CATEGORY:<2}{ready[cat]:>5}/{PER_CATEGORY}")
total_ready = sum(ready.values())
print(f"\nReady: {total_ready}/{len(rows)}")

shown = 0
for pid, issues in problems.items():
    if issues and shown < 40:
        print(f"  {pid}: {', '.join(issues)}")
        shown += 1
if shown == 40:
    print("  ... (first 40 problems shown)")

if args.strict and total_ready != len(rows):
    sys.exit(1)

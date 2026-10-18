r"""Create the benchmark manifest (one row per photo to take). Run once.

Usage (from backend/, venv active):
    python scripts/make_manifest.py
"""
import csv
import sys
from pathlib import Path

OUT = Path("benchmark/images/manifest.csv")

COLUMNS = [
    "id", "category", "file", "mode", "question", "subject",
    "must_mention", "must_not_mention", "exact_text", "source", "license", "notes",
]

DESCRIBE_Q = "What is in front of me?"

SHOTS = {
    "indoor": ("describe", [(DESCRIBE_Q, s) for s in [
        "living room with sofa and TV",
        "kitchen counter with appliances",
        "bedroom with bed and wardrobe",
        "desk with laptop and objects",
        "bathroom sink",
        "staircase indoors",
        "corridor with several doors",
        "dining table with plates and glasses",
        "cluttered desk",
        "shoes and bags near an entrance door",
    ]]),
    "outdoor": ("describe", [(DESCRIBE_Q, s) for s in [
        "street with a pedestrian crossing",
        "bus stop or tram stop",
        "sidewalk with an obstacle (pole, bin or bike)",
        "building entrance with steps",
        "market stall or shop front",
        "parked cars along a road",
        "garden or trees",
        "outdoor staircase",
        "cafe terrace with tables",
        "park bench and path",
    ]]),
    "text": ("read", [("Read the text.", s) for s in [
        "printed page of a book or document",
        "street name sign",
        "shop sign",
        "menu or price board",
        "handwritten note",
        "bus timetable or notice",
        "notice board with several papers",
        "phone or computer screen with text",
        "book cover",
        "label on a bottle or can",
    ]]),
    "product": ("product", [("What product is this?", s) for s in [
        "medicine box (no patient name on it)",
        "canned food",
        "milk or juice carton",
        "shampoo or soap bottle",
        "cereal or biscuit box",
        "snack bag",
        "spice jar",
        "cleaning product",
        "bottle of water or soda",
        "packaged bread or pastry",
    ]]),
    "currency": ("currency", [("How much money is this?", s) for s in [
        "20 dirham banknote",
        "50 dirham banknote",
        "100 dirham banknote",
        "200 dirham banknote",
        "a handful of coins (write which coins in notes)",
        "a single large coin",
        "several banknotes together (write the total in notes)",
        "banknote held in a hand",
        "slightly blurry banknote",
        "banknote partly covered by a finger",
    ]]),
    "find": ("find", [
        ("Where are my keys?", "keys on a table among other objects"),
        ("Where is the cup?", "cup on a desk"),
        ("Where is the remote control?", "remote control on a sofa"),
        ("Where is my phone?", "phone on a bed"),
        ("Where is the door handle?", "a door seen from inside"),
        ("Where is the light switch?", "wall with a light switch"),
        ("Where are my glasses?", "glasses on a table"),
        ("Where is the bottle?", "bottle on a shelf"),
        ("Where is the cat?", "a room with NO cat (absence test)"),
        ("Where is the umbrella?", "a hallway with NO umbrella (absence test)"),
    ]),
}

if OUT.exists():
    sys.exit(f"{OUT} already exists: not overwriting your ground truth.")

OUT.parent.mkdir(parents=True, exist_ok=True)
rows = []
for category, (mode, items) in SHOTS.items():
    for i, (question, subject) in enumerate(items, start=1):
        pid = f"{category}_{i:02d}"
        rows.append({
            "id": pid, "category": category, "file": pid + ".jpg", "mode": mode,
            "question": question, "subject": subject,
            "must_mention": "", "must_not_mention": "", "exact_text": "",
            "source": "", "license": "", "notes": "",
        })

with OUT.open("w", newline="", encoding="utf-8-sig") as fh:
    writer = csv.DictWriter(fh, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {OUT} with {len(rows)} rows")

r"""Send an image to the running API.

Usage (from backend/, with the server running):
    python scripts/try_describe.py C:\path\photo.jpg
    python scripts/try_describe.py C:\path\photo.jpg --mode read --lang fr --detail detailed
    python scripts/try_describe.py C:\path\photo.jpg --mode find --question "the door"
    python scripts/try_describe.py C:\path\dark.jpg --force      (describe even if the photo is bad)
"""
import argparse
import mimetypes
import sys
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("image")
parser.add_argument("--mode", default="describe")
parser.add_argument("--lang", default="en")
parser.add_argument("--detail", default="brief")
parser.add_argument("--question", default="")
parser.add_argument("--force", action="store_true")
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()

path = Path(args.image)
if not path.exists():
    sys.exit(f"File not found: {path}")

mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
with path.open("rb") as fh:
    r = httpx.post(
        f"{args.url}/api/describe",
        files={"image": (path.name, fh, mime)},
        data={
            "mode": args.mode,
            "lang": args.lang,
            "detail": args.detail,
            "question": args.question,
            "force": "true" if args.force else "false",
        },
        timeout=90,
    )

if r.status_code != 200:
    sys.exit(f"HTTP {r.status_code}: {r.text}")

body = r.json()
q = body["quality"]
t = body["timings_ms"]
header = f"[{body['mode']} | {body['lang']} | {body['detail']}] {body['model'] or 'model NOT called'}"
print(f"\n{header}  vlm={t['vlm']} ms  total={t['total']} ms")
print(f"quality: {q['severity']} {q['issues']}  {q['metrics']}\n")
print(body["text"])

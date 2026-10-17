r"""Talk to the running API: send a photo, then ask follow-up questions in one session.

Usage (from backend/, server running):
    python scripts/try_ask.py "C:\path\photo.jpg" "what color is it?" "is there any text?"
    python scripts/try_ask.py "C:\path\photo.jpg" --audio "benchmark\audio\ar.m4a" --lang ar
"""
import argparse
import mimetypes
import sys
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("image")
parser.add_argument("questions", nargs="*")
parser.add_argument("--audio", default="")
parser.add_argument("--lang", default="en")
parser.add_argument("--detail", default="brief")
parser.add_argument("--mode", default="describe")
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()

image = Path(args.image)
if not image.exists():
    sys.exit(f"File not found: {image}")
audio = Path(args.audio) if args.audio else None
if audio is not None and not audio.exists():
    sys.exit(f"File not found: {audio}")

client = httpx.Client(base_url=args.url, timeout=120)
common = {"lang": args.lang, "detail": args.detail, "mode": args.mode}


def show(label, r):
    if r.status_code != 200:
        sys.exit(f"{label}: HTTP {r.status_code}: {r.text}")
    b = r.json()
    t = b["timings_ms"]
    heard = ("  heard: " + b["transcript"]) if b["transcript"] else ""
    print(
        f"\n[{label}] model={b['model']} turns={b['turns']} "
        f"stt={t['stt']} vlm={t['vlm']} wait={t['rate_wait']} total={t['total']} ms{heard}"
    )
    print(b["text"])


sid = client.post("/api/session").json()["session_id"]

mime = mimetypes.guess_type(image.name)[0] or "image/jpeg"
with image.open("rb") as fh:
    show("photo", client.post("/api/ask", data={"session_id": sid, **common}, files={"image": (image.name, fh, mime)}))

for q in args.questions:
    show("text", client.post("/api/ask", data={"session_id": sid, "text": q, **common}))

if audio is not None:
    amime = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
    with audio.open("rb") as fh:
        show("audio", client.post("/api/ask", data={"session_id": sid, **common}, files={"audio": (audio.name, fh, amime)}))

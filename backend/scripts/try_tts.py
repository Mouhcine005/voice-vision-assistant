"""Ask the running API to speak a sentence, save the MP3 and play it.

Usage (from backend/, server running):
    python scripts/try_tts.py "Stairs ahead, on your left." --lang en
    python scripts/try_tts.py "Attention, un escalier devant vous." --lang fr
    python scripts/try_tts.py "انتبه، هناك درج أمامك" --lang ar --speed 1.1
"""
import argparse
import os
import sys
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("text")
parser.add_argument("--lang", default="en")
parser.add_argument("--speed", type=float, default=1.0)
parser.add_argument("--no-play", action="store_true")
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()

out_dir = Path(__file__).resolve().parent.parent / "benchmark" / "tts_out"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"tts_{args.lang}.mp3"

t0 = time.perf_counter()
r = httpx.post(
    f"{args.url}/api/tts",
    json={"text": args.text, "lang": args.lang, "speed": args.speed},
    timeout=60,
)
total_ms = (time.perf_counter() - t0) * 1000
if r.status_code != 200:
    sys.exit(f"HTTP {r.status_code}: {r.text}")

out.write_bytes(r.content)
print(f"voice={r.headers.get('x-tts-voice')}  synth={r.headers.get('x-tts-ms')} ms  "
      f"round trip={total_ms:.0f} ms  size={len(r.content) / 1024:.0f} KB")
print(f"saved: {out}")
if not args.no_play and hasattr(os, "startfile"):
    os.startfile(out)

"""Send an audio file to the running API's /api/stt endpoint.

Usage (from backend/, server running):
    python scripts/try_stt.py "C:\path\recording.m4a"
    python scripts/try_stt.py "C:\path\recording.m4a" --lang ar
"""
import argparse
import mimetypes
import sys
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("audio")
parser.add_argument("--lang", default="")
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()

path = Path(args.audio)
if not path.exists():
    sys.exit(f"File not found: {path}")

mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
with path.open("rb") as fh:
    r = httpx.post(
        f"{args.url}/api/stt",
        files={"audio": (path.name, fh, mime)},
        data={"lang": args.lang},
        timeout=300,
    )

if r.status_code != 200:
    sys.exit(f"HTTP {r.status_code}: {r.text}")

b = r.json()
print(f"\nlanguage={b['language']} (p={b['language_probability']})  audio={b['audio_seconds']} s  "
      f"transcribe={b['timings_ms']['transcribe']} ms  model_loaded_now={b['model_loaded_now']}")
print(f"\n{b['text'] or '(no speech detected)'}")

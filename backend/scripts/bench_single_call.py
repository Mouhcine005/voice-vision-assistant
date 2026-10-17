r"""Experiment: ask by voice in ONE Gemini call (photo + spoken question together).

Usage (from backend/, venv active, server NOT needed):
    python scripts/bench_single_call.py "C:\path\photo.jpg" "benchmark\audio\ar.m4a" --lang ar
    python scripts/bench_single_call.py photo.jpg clip1.m4a clip2.m4a --lang en --runs 2
"""
import argparse
import base64
import io
import json
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.prompts import build_system_prompt  # noqa: E402
from app.stt_gemini import _to_wav  # noqa: E402

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
PAUSE_S = 4.5  # stay under 15 requests per minute
SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "description": "Exact transcript of the spoken question."},
        "answer": {"type": "string", "description": "The answer to the question about the photo."},
    },
    "required": ["question", "answer"],
}
INSTRUCTION = (
    "The user's question is spoken in the attached audio. First transcribe it exactly as spoken "
    "(field question). Then answer it about the attached photo, following all the rules above "
    "(field answer). If the audio contains no speech, return an empty question and an empty answer."
)

parser = argparse.ArgumentParser()
parser.add_argument("image")
parser.add_argument("audio", nargs="+")
parser.add_argument("--lang", default="en")
parser.add_argument("--detail", default="brief")
parser.add_argument("--model", default=settings.gemini_model)
parser.add_argument("--runs", type=int, default=1)
args = parser.parse_args()

if not settings.gemini_api_key:
    sys.exit("GEMINI_API_KEY is missing in backend/.env")


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


image_path = Path(args.image)
if not image_path.exists():
    sys.exit(f"File not found: {image_path}")
with Image.open(image_path) as im:
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    image_bytes = buf.getvalue()

system_prompt = build_system_prompt(args.lang, args.detail, "describe")
url = f"{BASE_URL}/models/{args.model}:generateContent"

with httpx.Client(timeout=60) as client:
    for name in args.audio:
        path = Path(name)
        if not path.exists():
            sys.exit(f"File not found: {path}")
        wav = _to_wav(path.read_bytes(), path.suffix)
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64(image_bytes)}},
                        {"inline_data": {"mime_type": "audio/wav", "data": b64(wav)}},
                        {"text": INSTRUCTION},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseJsonSchema": SCHEMA,
            },
        }
        for run in range(1, args.runs + 1):
            t0 = time.perf_counter()
            r = client.post(url, json=payload, headers={"x-goog-api-key": settings.gemini_api_key})
            ms = (time.perf_counter() - t0) * 1000
            label = f"[{path.name} run{run}] {ms:.0f} ms"
            if r.status_code != 200:
                print(f"{label}  HTTP {r.status_code}: {r.text[:300]}")
            else:
                parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                raw = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
                try:
                    data = json.loads(raw)
                    print(f"{label}  heard: {data.get('question', '')!r}")
                    print(f"  answer: {data.get('answer', '')}")
                except ValueError:
                    print(f"{label}  (not valid JSON) {raw[:300]}")
            time.sleep(PAUSE_S)

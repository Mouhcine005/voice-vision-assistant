r"""Test Gemini as a speech-to-text engine on your own clips (server NOT needed).

Usage (from backend/, venv active):
    python scripts/bench_gemini_audio.py "benchmark\audio\a.m4a" "benchmark\audio\b.m4a"
    python scripts/bench_gemini_audio.py clip.m4a --models gemini-3.5-flash-lite gemini-3.5-transcribe
"""
import argparse
import base64
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
PROMPT = "Transcribe this audio exactly as spoken, in the language spoken. Output only the transcript."
PAUSE_S = 4.5  # stay under 15 requests per minute


def to_wav(path: Path) -> bytes:
    """Convert any audio to 16 kHz mono WAV with ffmpeg."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "clip.wav"
        proc = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000", str(out)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            sys.exit(f"ffmpeg failed on {path.name}: {proc.stderr[:300]}")
        return out.read_bytes()


def transcribe(client: httpx.Client, model: str, wav: bytes) -> tuple[float, str]:
    parts = [{"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav).decode()}}]
    if "transcribe" not in model:
        parts.append({"text": PROMPT})
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0},
    }
    t0 = time.perf_counter()
    r = client.post(
        f"{BASE_URL}/models/{model}:generateContent",
        json=payload,
        headers={"x-goog-api-key": settings.gemini_api_key},
    )
    ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        return ms, f"(HTTP {r.status_code}: {r.text[:200]})"
    candidates = r.json().get("candidates") or []
    out_parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
    text = "".join(p.get("text", "") for p in out_parts if not p.get("thought")).strip()
    return ms, text or "(empty answer)"


parser = argparse.ArgumentParser()
parser.add_argument("files", nargs="+")
parser.add_argument("--models", nargs="+", default=["gemini-3.5-flash-lite", "gemini-3.5-transcribe"])
parser.add_argument("--runs", type=int, default=2)
args = parser.parse_args()

if not settings.gemini_api_key:
    sys.exit("GEMINI_API_KEY is missing in backend/.env")

files = [Path(f) for f in args.files]
for f in files:
    if not f.exists():
        sys.exit(f"File not found: {f}")

wavs = {f: to_wav(f) for f in files}
with httpx.Client(timeout=60) as client:
    for model in args.models:
        print(f"\n== {model} ==")
        for f in files:
            for run in range(1, args.runs + 1):
                ms, text = transcribe(client, model, wavs[f])
                print(f"{f.name[:28]:<28} run{run} {ms:6.0f} ms  |  {text}")
                time.sleep(PAUSE_S)

"""Speech to text with Gemini (primary engine). Whisper stays as the fallback."""
import asyncio
import base64
import logging
import os
import re
import subprocess
import tempfile
import time

import httpx

from app.config import settings
from app.stt import SttError, SttResult

log = logging.getLogger("uvicorn.error")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
PROMPT = (
    "Transcribe this audio exactly as spoken, in the language spoken. "
    "Output only the transcript, with no comments. "
    "If there is no speech, output nothing."
)


def _safe_suffix(suffix: str) -> str:
    return suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,5}", suffix or "") else ".bin"


def _to_wav(raw: bytes, suffix: str) -> bytes:
    """Convert any audio to 16 kHz mono WAV with ffmpeg."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in" + suffix)
        dst = os.path.join(tmp, "out.wav")
        with open(src, "wb") as fh:
            fh.write(raw)
        try:
            proc = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", dst],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError as exc:
            raise SttError("ffmpeg is not installed or not on PATH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise SttError("ffmpeg timed out converting the audio.") from exc
        if proc.returncode != 0:
            raise SttError(f"Could not decode the audio: {proc.stderr[:200]}")
        with open(dst, "rb") as fh:
            return fh.read()


def extract_text(data: dict) -> str:
    """Pull the transcript out of a generateContent response. Empty string = no speech."""
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "unknown")
        raise SttError(f"Gemini returned no candidates (blockReason={reason})")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()


async def transcribe_gemini(raw: bytes, suffix: str = ".webm") -> SttResult:
    if not settings.gemini_api_key:
        raise SttError("GEMINI_API_KEY is missing in backend/.env")

    started = time.perf_counter()
    wav = await asyncio.to_thread(_to_wav, raw, _safe_suffix(suffix))
    duration_s = max(0.0, (len(wav) - 44) / 32000)  # 16 kHz, 16-bit, mono PCM

    model = settings.gemini_stt_model
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav).decode()}},
                    {"text": PROMPT},
                ],
            }
        ],
        "generationConfig": {"temperature": 0},
    }
    url = f"{BASE_URL}/models/{model}:generateContent"
    last_error = "unknown"

    async with httpx.AsyncClient(timeout=settings.vlm_timeout_seconds) as client:
        for attempt in (1, 2):
            try:
                resp = await client.post(
                    url, json=payload, headers={"x-goog-api-key": settings.gemini_api_key}
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = f"network problem: {type(exc).__name__}"
            else:
                if resp.status_code == 200:
                    try:
                        text = extract_text(resp.json())
                    except ValueError as exc:
                        raise SttError("Gemini returned invalid JSON.") from exc
                    return SttResult(
                        text=text,
                        language="",
                        language_probability=0.0,
                        duration_s=round(duration_s, 2),
                        transcribe_ms=(time.perf_counter() - started) * 1000,
                        model_loaded_now=False,
                        engine="gemini",
                    )
                last_error = f"HTTP {resp.status_code}"
                if resp.status_code not in RETRYABLE_STATUS:
                    raise SttError(f"Gemini STT ({model}) failed: {last_error}")
            if attempt == 1:
                await asyncio.sleep(1.0)

    raise SttError(f"Gemini STT ({model}) failed: {last_error}")

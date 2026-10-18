import logging
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ask import build_ask_router
from app.config import BASE_DIR, settings
from app.imaging import ImageError, prepare_image
from app.metrics import MetricsStore
from app.prompts import (
    LANGUAGE_NAMES,
    VALID_DETAILS,
    VALID_MODES,
    build_system_prompt,
    default_question,
)
from app.providers import ProviderError, get_provider
from app.quality import analyze_quality
from app.ratelimit import RateLimiter
from app.sessions import SessionStore
from app.stt import SttError, SttResult, transcribe_audio
from app.stt_gemini import transcribe_gemini
from app.tts import TtsError, synthesize

MAX_AUDIO_MB = 25

log = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Voice Vision Assistant API",
    description="Voice-first image description assistant for visually impaired users.",
    version="0.9.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-TTS-Voice", "X-TTS-Ms"],
)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    """Quick status check: is the API up and is the active provider configured?"""
    provider = settings.vlm_provider
    model = getattr(settings, f"{provider}_model", "")
    if provider == "ollama":
        configured = bool(model)
    else:
        configured = bool(getattr(settings, f"{provider}_api_key", "")) and bool(model)
    return {
        "status": "ok",
        "env": settings.app_env,
        "provider": provider,
        "model": model,
        "provider_configured": configured,
        "whisper_model": settings.whisper_model_size,
    }


@app.get("/api/modes", tags=["system"])
def modes() -> dict:
    """Modes, languages and detail levels the frontend can offer."""
    return {
        "modes": list(VALID_MODES),
        "languages": LANGUAGE_NAMES,
        "details": list(VALID_DETAILS),
    }


async def _read_and_prepare(image: UploadFile):
    """Read the upload, enforce the size limit, resize and re-encode it."""
    raw = await image.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image is larger than {settings.max_upload_mb} MB.")
    try:
        return await run_in_threadpool(prepare_image, raw)
    except ImageError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/quality", tags=["vision"])
async def quality(
    image: UploadFile = File(...),
    lang: str = Form("en"),
) -> dict:
    """Fast photo quality check (too dark, too bright, blurry, flat). No AI model is called."""
    if lang not in LANGUAGE_NAMES:
        raise HTTPException(400, f"lang must be one of: {', '.join(LANGUAGE_NAMES)}")
    t_start = time.perf_counter()
    prepared = await _read_and_prepare(image)
    report = await run_in_threadpool(analyze_quality, prepared.data)
    body = report.to_dict(lang)
    body["timings_ms"] = {"total": round((time.perf_counter() - t_start) * 1000)}
    return body


@app.post("/api/describe", tags=["vision"])
async def describe(
    image: UploadFile = File(...),
    question: str = Form(""),
    lang: str = Form("en"),
    detail: str = Form("brief"),
    mode: str = Form("describe"),
    force: bool = Form(False),
) -> dict:
    """Describe an uploaded image (or answer a question about it) in the chosen mode.

    If the photo is unusable (very dark, very blurry...), the AI model is NOT called and
    the answer is spoken-friendly advice for retaking the photo. Send force=true to skip this check.
    """
    if lang not in LANGUAGE_NAMES:
        raise HTTPException(400, f"lang must be one of: {', '.join(LANGUAGE_NAMES)}")
    if detail not in VALID_DETAILS:
        raise HTTPException(400, f"detail must be one of: {', '.join(VALID_DETAILS)}")
    if mode not in VALID_MODES:
        raise HTTPException(400, f"mode must be one of: {', '.join(VALID_MODES)}")

    t_start = time.perf_counter()
    prepared = await _read_and_prepare(image)
    t_prepared = time.perf_counter()

    report = await run_in_threadpool(analyze_quality, prepared.data)
    quality_dict = report.to_dict(lang)
    t_quality = time.perf_counter()

    image_info = {
        "width": prepared.width,
        "height": prepared.height,
        "original_bytes": prepared.original_bytes,
        "sent_bytes": len(prepared.data),
    }

    if report.severity == "bad" and not force:
        return {
            "text": quality_dict["advice"],
            "skipped_model": True,
            "mode": mode,
            "lang": lang,
            "detail": detail,
            "provider": None,
            "model": None,
            "used_fallback": False,
            "attempts": 0,
            "quality": quality_dict,
            "image": image_info,
            "timings_ms": {
                "preprocess": round((t_prepared - t_start) * 1000),
                "quality": round((t_quality - t_prepared) * 1000),
                "vlm": 0,
                "total": round((time.perf_counter() - t_start) * 1000),
            },
        }

    try:
        provider = get_provider()
        result = await provider.generate(
            system_prompt=build_system_prompt(lang, detail, mode),
            user_text=question.strip() or default_question(mode),
            image_bytes=prepared.data,
            mime_type=prepared.mime_type,
        )
    except ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc
    t_end = time.perf_counter()

    return {
        "text": result.text,
        "skipped_model": False,
        "mode": mode,
        "lang": lang,
        "detail": detail,
        "provider": result.provider,
        "model": result.model,
        "used_fallback": result.used_fallback,
        "attempts": result.attempts,
        "quality": quality_dict,
        "image": image_info,
        "timings_ms": {
            "preprocess": round((t_prepared - t_start) * 1000),
            "quality": round((t_quality - t_prepared) * 1000),
            "vlm": round(result.latency_ms),
            "total": round((t_end - t_start) * 1000),
        },
    }


async def _transcribe(raw: bytes, suffix: str, lang: str | None) -> SttResult:
    """Gemini first (fast and accurate on real voices); Whisper as the fallback."""
    if settings.stt_engine == "gemini":
        try:
            return await transcribe_gemini(raw, suffix)
        except SttError as exc:
            log.warning("Gemini STT failed (%s). Falling back to Whisper.", exc)
    return await run_in_threadpool(transcribe_audio, raw, suffix, lang)


@app.post("/api/stt", tags=["speech"])
async def stt(
    audio: UploadFile = File(...),
    lang: str = Form(""),
) -> dict:
    """Speech to text. Leave `lang` empty to auto-detect (ar / fr / en)."""
    if lang and lang not in LANGUAGE_NAMES:
        raise HTTPException(400, f"lang must be empty or one of: {', '.join(LANGUAGE_NAMES)}")

    t_start = time.perf_counter()
    raw = await audio.read()
    if not raw:
        raise HTTPException(400, "The uploaded audio file is empty.")
    if len(raw) > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(413, f"Audio is larger than {MAX_AUDIO_MB} MB.")

    suffix = Path(audio.filename or "").suffix or ".webm"
    try:
        result = await _transcribe(raw, suffix, lang or None)
    except SttError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {
        "text": result.text,
        "engine": result.engine,
        "convert_ms": round(result.convert_ms),
        "api_ms": round(result.api_ms),
        "no_speech": not result.text,
        "language": result.language,
        "language_probability": result.language_probability,
        "audio_seconds": result.duration_s,
        "model_loaded_now": result.model_loaded_now,
        "timings_ms": {
            "transcribe": round(result.transcribe_ms),
            "total": round((time.perf_counter() - t_start) * 1000),
        },
    }


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    lang: Literal["en", "fr", "ar"] = "en"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@app.post("/api/tts", tags=["speech"])
async def tts(req: TtsRequest) -> Response:
    """Text to speech. Returns MP3 audio. If this fails, the frontend can use the browser voice."""
    try:
        result = await synthesize(req.text, req.lang, req.speed)
    except TtsError as exc:
        raise HTTPException(502, str(exc)) from exc
    return Response(
        content=result.audio,
        media_type="audio/mpeg",
        headers={
            "X-TTS-Voice": result.voice,
            "X-TTS-Ms": str(round(result.synth_ms)),
        },
    )


session_store = SessionStore()
gemini_limiter = RateLimiter(settings.gemini_rpm_limit)
metrics_store = MetricsStore(BASE_DIR / "data" / "metrics.db")

app.include_router(
    build_ask_router(
        read_and_prepare=_read_and_prepare,
        transcribe=_transcribe,
        get_provider=lambda: get_provider(),
        store=session_store,
        limiter=gemini_limiter,
        metrics=metrics_store,
    )
)


@app.get("/api/metrics/summary", tags=["system"])
def metrics_summary(window: int = 200) -> dict:
    """Latency percentiles per stage over the last `window` requests (feeds the Jury panel)."""
    return metrics_store.summary(window)


@app.get("/api/metrics/recent", tags=["system"])
def metrics_recent(limit: int = 20) -> dict:
    """The most recent requests with their per-stage timings, newest first."""
    return {"items": metrics_store.recent(limit)}

"""Conversation endpoints: sessions and /api/ask (follow-up questions about a photo)."""
import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.imaging import PreparedImage
from app.metrics import MetricsStore
from app.prompts import (
    LANGUAGE_NAMES,
    VALID_DETAILS,
    VALID_MODES,
    build_system_prompt,
    default_question,
)
from app.providers import ProviderError, VLMProvider
from app.quality import analyze_quality
from app.ratelimit import RateLimiter, RateLimitExceeded
from app.sessions import SessionStore
from app.stt import SttError, SttResult

MAX_AUDIO_MB = 25
MAX_QUESTION_CHARS = 1000
MAX_RATE_WAIT_S = 6.0

NO_SPEECH = {
    "en": "I did not catch your question. Please try again.",
    "fr": "Je n'ai pas entendu votre question. Pouvez-vous r\u00e9p\u00e9ter, s'il vous pla\u00eet ?",
    "ar": "\u0644\u0645 \u0623\u0633\u0645\u0639 \u0633\u0624\u0627\u0644\u0643\u060c \u0645\u0646 \u0641\u0636\u0644\u0643 \u0623\u0639\u062f \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629.",
}

ReadAndPrepare = Callable[[UploadFile], Awaitable[PreparedImage]]
Transcribe = Callable[[bytes, str, str | None], Awaitable[SttResult]]


def build_ask_router(
    *,
    read_and_prepare: ReadAndPrepare,
    transcribe: Transcribe,
    get_provider: Callable[[], VLMProvider],
    store: SessionStore,
    limiter: RateLimiter,
    metrics: MetricsStore | None = None,
) -> APIRouter:
    router = APIRouter(tags=["conversation"])

    def require_session(session_id: str):
        session = store.get(session_id)
        if session is None:
            raise HTTPException(404, "Session not found or expired. Start a new session.")
        return session

    @router.post("/api/session")
    async def create_session() -> dict:
        session = store.create()
        return {
            "session_id": session.id,
            "ttl_seconds": store.ttl_seconds,
            "max_turns": store.max_turns,
        }

    @router.get("/api/session/{session_id}")
    async def session_info(session_id: str) -> dict:
        session = require_session(session_id)
        img = session.image
        return {
            "session_id": session.id,
            "turns": len(session.history) // 2,
            "has_image": img is not None,
            "image": {"width": img.width, "height": img.height} if img else None,
        }

    @router.delete("/api/session/{session_id}")
    async def delete_session(session_id: str) -> dict:
        if not store.delete(session_id):
            raise HTTPException(404, "Session not found or expired.")
        return {"deleted": True}

    @router.post("/api/ask")
    async def ask(
        session_id: str = Form(...),
        text: str = Form(""),
        audio: UploadFile | None = File(None),
        image: UploadFile | None = File(None),
        lang: str = Form("en"),
        detail: str = Form("brief"),
        mode: str = Form("describe"),
        force: bool = Form(False),
    ) -> dict:
        """Ask about the session's photo, by text or voice. Send an image to start or change topic."""
        if lang not in LANGUAGE_NAMES:
            raise HTTPException(400, f"lang must be one of: {', '.join(LANGUAGE_NAMES)}")
        if detail not in VALID_DETAILS:
            raise HTTPException(400, f"detail must be one of: {', '.join(VALID_DETAILS)}")
        if mode not in VALID_MODES:
            raise HTTPException(400, f"mode must be one of: {', '.join(VALID_MODES)}")

        t_start = time.perf_counter()
        session = require_session(session_id)

        question = text.strip()
        if len(question) > MAX_QUESTION_CHARS:
            raise HTTPException(400, f"The question is longer than {MAX_QUESTION_CHARS} characters.")
        if question and audio is not None:
            raise HTTPException(400, "Send either text or audio, not both.")
        if not question and audio is None and image is None:
            raise HTTPException(400, "Send a question (text or audio) and/or a photo.")

        audio_raw = b""
        if audio is not None:
            audio_raw = await audio.read()
            if not audio_raw:
                raise HTTPException(400, "The uploaded audio file is empty.")
            if len(audio_raw) > MAX_AUDIO_MB * 1024 * 1024:
                raise HTTPException(413, f"Audio is larger than {MAX_AUDIO_MB} MB.")

        t = {"preprocess": 0, "rate_wait": 0, "stt": 0, "vlm": 0, "total": 0}
        transcript: str | None = None
        quality_dict: dict | None = None

        def record(status: int, body: dict | None = None) -> None:
            if metrics is None:
                return
            body = body or {}
            metrics.record(
                endpoint="ask",
                status=status,
                mode=mode,
                lang=lang,
                detail=detail,
                provider=body.get("provider"),
                model=body.get("model"),
                used_fallback=bool(body.get("used_fallback")),
                attempts=int(body.get("attempts") or 0),
                skipped_model=bool(body.get("skipped_model")),
                stt_engine=(body.get("stt") or {}).get("engine"),
                timings=t,
            )

        def make(answer: str, skipped: bool, **fields) -> dict:
            t["total"] = round((time.perf_counter() - t_start) * 1000)
            body = {
                "text": answer,
                "skipped_model": skipped,
                "no_speech": False,
                "transcript": transcript,
                "session_id": session.id,
                "turns": len(session.history) // 2,
                "mode": mode,
                "lang": lang,
                "detail": detail,
                "provider": None,
                "model": None,
                "used_fallback": False,
                "attempts": 0,
                "stt": None,
                "image": None,
                "quality": quality_dict,
                "timings_ms": t,
                **fields,
            }
            record(200, body)
            return body

        # 1. A new photo? Check its quality before spending any API call.
        new_image: PreparedImage | None = None
        if image is not None:
            t0 = time.perf_counter()
            new_image = await read_and_prepare(image)
            report = await run_in_threadpool(analyze_quality, new_image.data)
            quality_dict = report.to_dict(lang)
            t["preprocess"] = round((time.perf_counter() - t0) * 1000)
            if report.severity == "bad" and not force:
                return make(quality_dict["advice"], True)

        photo = new_image or session.image
        if photo is None:
            raise HTTPException(400, "No photo in this session yet. Send a photo first.")
        image_info = {
            "width": photo.width,
            "height": photo.height,
            "sent_bytes": len(photo.data),
            "new": new_image is not None,
        }

        # 2. Stay under the free-tier requests-per-minute limit (a voice turn = 2 calls).
        try:
            wait = limiter.reserve(2 if audio is not None else 1, max_wait=MAX_RATE_WAIT_S)
        except RateLimitExceeded as exc:
            retry = math.ceil(exc.retry_after)
            raise HTTPException(
                429,
                f"Too many requests. Try again in {retry} seconds.",
                headers={"Retry-After": str(retry)},
            ) from exc
        if wait > 0:
            await asyncio.sleep(wait)
        t["rate_wait"] = round(wait * 1000)

        # 3. Speech to text, if the question was spoken.
        stt_info = None
        if audio is not None:
            suffix = Path(audio.filename or "").suffix or ".webm"
            t1 = time.perf_counter()
            try:
                heard = await transcribe(audio_raw, suffix, lang)
            except SttError as exc:
                raise HTTPException(400, str(exc)) from exc
            t["stt"] = round((time.perf_counter() - t1) * 1000)
            transcript = heard.text
            stt_info = {"engine": heard.engine, "audio_seconds": heard.duration_s}
            if not transcript:
                return make(NO_SPEECH[lang], True, no_speech=True, stt=stt_info, image=image_info)
            question = transcript

        # 4. Ask the vision model. A new photo starts with a clean history.
        user_text = question or default_question(mode)
        history = [] if new_image is not None else list(session.history)
        try:
            result = await get_provider().generate(
                system_prompt=build_system_prompt(lang, detail, mode),
                user_text=user_text,
                image_bytes=photo.data,
                mime_type=photo.mime_type,
                history=history,
            )
        except ProviderError as exc:
            t["total"] = round((time.perf_counter() - t_start) * 1000)
            record(502)
            raise HTTPException(502, str(exc)) from exc
        t["vlm"] = round(result.latency_ms)

        # 5. Only now remember the photo and the turn (a failed call leaves the session untouched).
        if new_image is not None:
            store.set_image(session, new_image)
        store.add_turn(session, user_text, result.text)

        return make(
            result.text,
            False,
            provider=result.provider,
            model=result.model,
            used_fallback=result.used_fallback,
            attempts=result.attempts,
            stt=stt_info,
            image=image_info,
        )

    return router

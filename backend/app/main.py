import time

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.imaging import ImageError, prepare_image
from app.prompts import LANGUAGE_NAMES, build_system_prompt
from app.providers import ProviderError, get_provider

app = FastAPI(
    title="Voice Vision Assistant API",
    description="Voice-first image description assistant for visually impaired users.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_DETAILS = {"brief", "detailed"}


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
    }


@app.post("/api/describe", tags=["vision"])
async def describe(
    image: UploadFile = File(...),
    question: str = Form(""),
    lang: str = Form("en"),
    detail: str = Form("brief"),
) -> dict:
    """Describe an uploaded image (or answer a question about it) in the chosen language."""
    if lang not in LANGUAGE_NAMES:
        raise HTTPException(400, f"lang must be one of: {', '.join(LANGUAGE_NAMES)}")
    if detail not in VALID_DETAILS:
        raise HTTPException(400, f"detail must be one of: {', '.join(sorted(VALID_DETAILS))}")

    t_start = time.perf_counter()

    raw = await image.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image is larger than {settings.max_upload_mb} MB.")

    try:
        prepared = await run_in_threadpool(prepare_image, raw)
    except ImageError as exc:
        raise HTTPException(400, str(exc)) from exc
    t_prepared = time.perf_counter()

    try:
        provider = get_provider()
        result = await provider.generate(
            system_prompt=build_system_prompt(lang, detail),
            user_text=question.strip() or "Describe this image.",
            image_bytes=prepared.data,
            mime_type=prepared.mime_type,
        )
    except ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc
    t_end = time.perf_counter()

    return {
        "text": result.text,
        "provider": result.provider,
        "model": result.model,
        "used_fallback": result.used_fallback,
        "attempts": result.attempts,
        "image": {
            "width": prepared.width,
            "height": prepared.height,
            "original_bytes": prepared.original_bytes,
            "sent_bytes": len(prepared.data),
        },
        "timings_ms": {
            "preprocess": round((t_prepared - t_start) * 1000),
            "vlm": round(result.latency_ms),
            "total": round((t_end - t_start) * 1000),
        },
    }

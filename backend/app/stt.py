import logging
import os
import tempfile
import threading
import time
from dataclasses import dataclass

from app.config import settings

log = logging.getLogger("uvicorn.error")

ALLOWED_LANGUAGES = ("ar", "fr", "en")
DEVICE = "cpu"
BEAM_SIZE = 3  # 1 = fastest, 5 = most accurate. We will tune this with measurements.

_model = None
_model_lock = threading.Lock()


class SttError(Exception):
    """The audio could not be decoded or transcribed."""


@dataclass
class SttResult:
    text: str
    language: str
    language_probability: float
    duration_s: float
    transcribe_ms: float
    model_loaded_now: bool


def get_model():
    """Load the Whisper model once (first call can take a while: download + load)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from faster_whisper import WhisperModel  # imported lazily: keeps startup fast

                started = time.perf_counter()
                log.info(
                    "Loading Whisper model '%s' (%s, %s)...",
                    settings.whisper_model_size,
                    DEVICE,
                    settings.whisper_compute_type,
                )
                _model = WhisperModel(
                    settings.whisper_model_size,
                    device=DEVICE,
                    compute_type=settings.whisper_compute_type,
                )
                log.info("Whisper model loaded in %.1f s", time.perf_counter() - started)
    return _model


def _run(model, path: str, language: str | None):
    segments, info = model.transcribe(
        path,
        language=language,
        beam_size=BEAM_SIZE,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
    )
    # `segments` is a generator: the real work happens while we consume it.
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return text, info


def transcribe_audio(raw: bytes, suffix: str = ".webm", language_hint: str | None = None) -> SttResult:
    """Transcribe audio bytes. Auto-detects the language unless a hint is given."""
    already_loaded = _model is not None
    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)

        model = get_model()
        started = time.perf_counter()
        text, info = _run(model, path, language_hint)
        language = language_hint or info.language
        probability = 1.0 if language_hint else float(info.language_probability)

        # Whisper knows ~100 languages; our app supports 3. If it detects something else,
        # it is almost always a mis-detection, so retry as English.
        if language_hint is None and language not in ALLOWED_LANGUAGES:
            log.info("Detected '%s' (not supported); retrying as English.", language)
            text, info = _run(model, path, "en")
            language = "en"
            probability = 0.0

        return SttResult(
            text=text,
            language=language,
            language_probability=round(probability, 3),
            duration_s=round(float(info.duration), 2),
            transcribe_ms=(time.perf_counter() - started) * 1000,
            model_loaded_now=not already_loaded,
        )
    except SttError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise SttError(f"Could not decode or transcribe the audio: {exc}") from exc
    finally:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

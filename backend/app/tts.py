import asyncio
import re
import time
from dataclasses import dataclass

from app.config import settings


class TtsError(Exception):
    """Speech synthesis failed (no internet, bad voice name, or empty text)."""


@dataclass
class TtsResult:
    audio: bytes
    voice: str
    lang: str
    synth_ms: float
    chars: int


_EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")


def clean_for_speech(text: str) -> str:
    """Remove markdown, bullets and emojis so the voice does not read symbols aloud."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", text, flags=re.M)
    text = _EMOJI.sub(" ", text)
    text = re.sub(r"[*_#`>~|]+", " ", text)
    return " ".join(text.split())


def voice_for(lang: str) -> str:
    voices = {
        "en": settings.tts_voice_en,
        "fr": settings.tts_voice_fr,
        "ar": settings.tts_voice_ar,
    }
    return voices.get(lang, settings.tts_voice_en)


async def synthesize(text: str, lang: str = "en", speed: float = 1.0) -> TtsResult:
    """Turn text into MP3 bytes with edge-tts. Requires an internet connection."""
    import edge_tts  # lazy import keeps startup fast

    cleaned = clean_for_speech(text)
    if not cleaned:
        raise TtsError("There is nothing to speak after removing symbols.")

    voice = voice_for(lang)
    rate = f"{round((speed - 1.0) * 100):+d}%"
    started = time.perf_counter()

    async def _collect() -> bytes:
        communicate = edge_tts.Communicate(cleaned, voice, rate=rate)
        buffer = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.extend(chunk["data"])
        return bytes(buffer)

    try:
        audio = await asyncio.wait_for(_collect(), timeout=settings.tts_timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise TtsError(f"Speech synthesis timed out after {settings.tts_timeout_seconds:.0f} s.") from exc
    except Exception as exc:  # noqa: BLE001
        raise TtsError(f"Speech synthesis failed ({type(exc).__name__}): {exc}") from exc

    if not audio:
        raise TtsError(f"The voice '{voice}' returned no audio. Check the voice name in .env.")

    return TtsResult(
        audio=audio,
        voice=voice,
        lang=lang,
        synth_ms=(time.perf_counter() - started) * 1000,
        chars=len(cleaned),
    )

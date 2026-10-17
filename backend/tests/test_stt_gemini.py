import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.stt import SttError, SttResult
from app.stt_gemini import extract_text

client = TestClient(app)


def test_extract_text_joins_parts_and_skips_thoughts():
    data = {
        "candidates": [
            {"content": {"parts": [{"text": "hidden", "thought": True}, {"text": " what is this "}]}}
        ]
    }
    assert extract_text(data) == "what is this"


def test_extract_text_empty_means_no_speech():
    assert extract_text({"candidates": [{"content": {"parts": []}}]}) == ""


def test_extract_text_no_candidates_raises():
    with pytest.raises(SttError):
        extract_text({"promptFeedback": {"blockReason": "OTHER"}})


async def _fake_gemini(raw, suffix=".webm"):
    return SttResult(
        text="what is in front of me",
        language="",
        language_probability=0.0,
        duration_s=2.0,
        transcribe_ms=5.0,
        model_loaded_now=False,
        engine="gemini",
    )


async def _failing_gemini(raw, suffix=".webm"):
    raise SttError("boom")


def _fake_whisper(raw, suffix=".webm", language_hint=None):
    return SttResult(
        text="fallback text",
        language=language_hint or "en",
        language_probability=1.0,
        duration_s=1.0,
        transcribe_ms=3.0,
        model_loaded_now=False,
    )


def test_stt_uses_gemini_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "stt_engine", "gemini")
    monkeypatch.setattr("app.main.transcribe_gemini", _fake_gemini)
    r = client.post("/api/stt", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "gemini"
    assert body["text"] == "what is in front of me"


def test_stt_falls_back_to_whisper_when_gemini_fails(monkeypatch):
    monkeypatch.setattr(settings, "stt_engine", "gemini")
    monkeypatch.setattr("app.main.transcribe_gemini", _failing_gemini)
    monkeypatch.setattr("app.main.transcribe_audio", _fake_whisper)
    r = client.post(
        "/api/stt",
        files={"audio": ("a.webm", b"x", "audio/webm")},
        data={"lang": "fr"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "whisper"
    assert body["text"] == "fallback text"
    assert body["language"] == "fr"

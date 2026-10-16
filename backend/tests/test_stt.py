from fastapi.testclient import TestClient

from app.main import app
from app.stt import SttResult

client = TestClient(app)


def _fake_transcribe(raw, suffix=".webm", language_hint=None):
    return SttResult(
        text="what is in front of me",
        language=language_hint or "en",
        language_probability=0.99,
        duration_s=2.0,
        transcribe_ms=12.0,
        model_loaded_now=False,
    )


def test_stt_success(monkeypatch):
    monkeypatch.setattr("app.main.transcribe_audio", _fake_transcribe)
    r = client.post("/api/stt", files={"audio": ("a.webm", b"fake-audio", "audio/webm")})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "what is in front of me"
    assert body["no_speech"] is False
    assert body["language"] == "en"


def test_stt_language_hint_is_used(monkeypatch):
    monkeypatch.setattr("app.main.transcribe_audio", _fake_transcribe)
    r = client.post(
        "/api/stt",
        files={"audio": ("a.m4a", b"fake-audio", "audio/mp4")},
        data={"lang": "fr"},
    )
    assert r.status_code == 200
    assert r.json()["language"] == "fr"


def test_stt_empty_file_rejected():
    r = client.post("/api/stt", files={"audio": ("a.webm", b"", "audio/webm")})
    assert r.status_code == 400


def test_stt_bad_language_rejected():
    r = client.post(
        "/api/stt",
        files={"audio": ("a.webm", b"x", "audio/webm")},
        data={"lang": "klingon"},
    )
    assert r.status_code == 400

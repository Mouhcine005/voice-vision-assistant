from fastapi.testclient import TestClient

from app.main import app
from app.tts import TtsError, TtsResult, clean_for_speech

client = TestClient(app)


def test_clean_for_speech_removes_markdown_and_emojis():
    raw = "**Warning:** stairs ahead \U0001F6A8\n- first item\n- second item\n# Title"
    cleaned = clean_for_speech(raw)
    assert "*" not in cleaned
    assert "#" not in cleaned
    assert "\U0001F6A8" not in cleaned
    assert "stairs ahead" in cleaned
    assert "first item" in cleaned


def test_clean_for_speech_keeps_arabic():
    assert clean_for_speech("**\u0645\u0631\u062d\u0628\u0627**") == "\u0645\u0631\u062d\u0628\u0627"


def test_tts_returns_audio(monkeypatch):
    async def fake_synthesize(text, lang="en", speed=1.0):
        return TtsResult(audio=b"ID3fakemp3", voice="fake-voice", lang=lang, synth_ms=5.0, chars=len(text))

    monkeypatch.setattr("app.main.synthesize", fake_synthesize)
    r = client.post("/api/tts", json={"text": "Hello there", "lang": "fr"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"ID3fakemp3"
    assert r.headers["x-tts-voice"] == "fake-voice"


def test_tts_failure_returns_502(monkeypatch):
    async def failing_synthesize(text, lang="en", speed=1.0):
        raise TtsError("no internet")

    monkeypatch.setattr("app.main.synthesize", failing_synthesize)
    r = client.post("/api/tts", json={"text": "Hello", "lang": "en"})
    assert r.status_code == 502


def test_tts_rejects_bad_input():
    assert client.post("/api/tts", json={"text": "", "lang": "en"}).status_code == 422
    assert client.post("/api/tts", json={"text": "hi", "lang": "xx"}).status_code == 422
    assert client.post("/api/tts", json={"text": "hi", "speed": 5}).status_code == 422

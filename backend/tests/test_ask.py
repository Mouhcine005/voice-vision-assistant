import io

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.ask import build_ask_router
from app.main import _read_and_prepare
from app.providers import ProviderError, VLMResult
from app.ratelimit import RateLimiter
from app.sessions import SessionStore
from app.stt import SttResult


class FakeProvider:
    name = "fake"

    def __init__(self):
        self.calls = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        return VLMResult(
            text=f"answer {len(self.calls)}", provider="fake", model="fake-1", latency_ms=1.0
        )


class BrokenProvider:
    name = "broken"

    async def generate(self, **kwargs):
        raise ProviderError("service down")


def _good_png() -> bytes:
    buf = io.BytesIO()
    Image.effect_noise((128, 128), 64).convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _black_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "black").save(buf, format="PNG")
    return buf.getvalue()


def _heard(text: str):
    async def fake(raw, suffix, lang):
        return SttResult(
            text=text,
            language=lang or "",
            language_probability=0.0,
            duration_s=1.5,
            transcribe_ms=5.0,
            model_loaded_now=False,
            engine="gemini",
        )

    return fake


def make_client(provider=None, transcribe=None, limiter=None):
    provider = provider or FakeProvider()
    api = FastAPI()
    api.include_router(
        build_ask_router(
            read_and_prepare=_read_and_prepare,
            transcribe=transcribe or _heard("what color is it"),
            get_provider=lambda: provider,
            store=SessionStore(),
            limiter=limiter or RateLimiter(1000),
        )
    )
    return TestClient(api), provider


def _session(client) -> str:
    return client.post("/api/session").json()["session_id"]


def _photo(client, sid, **data):
    return client.post(
        "/api/ask",
        data={"session_id": sid, **data},
        files={"image": ("a.png", _good_png(), "image/png")},
    )


def test_unknown_session_is_404():
    client, _ = make_client()
    r = client.post("/api/ask", data={"session_id": "nope", "text": "hi"})
    assert r.status_code == 404


def test_photo_then_follow_up_reuses_image_and_history():
    client, provider = make_client()
    sid = _session(client)
    r1 = _photo(client, sid)
    assert r1.status_code == 200
    assert r1.json()["text"] == "answer 1"
    assert r1.json()["turns"] == 1
    r2 = client.post("/api/ask", data={"session_id": sid, "text": "what color is it?"})
    assert r2.status_code == 200
    assert r2.json()["turns"] == 2
    first, second = provider.calls
    assert first["history"] == []
    assert second["image_bytes"] == first["image_bytes"]
    assert [turn.role for turn in second["history"]] == ["user", "assistant"]
    assert second["user_text"] == "what color is it?"


def test_follow_up_without_any_photo_is_400():
    client, _ = make_client()
    sid = _session(client)
    r = client.post("/api/ask", data={"session_id": sid, "text": "what is this?"})
    assert r.status_code == 400


def test_new_photo_clears_the_history():
    client, provider = make_client()
    sid = _session(client)
    _photo(client, sid)
    client.post("/api/ask", data={"session_id": sid, "text": "and now?"})
    r = _photo(client, sid, text="what is this one?")
    assert r.status_code == 200
    assert r.json()["turns"] == 1
    assert provider.calls[-1]["history"] == []


def test_bad_photo_skips_the_model_and_is_not_stored():
    client, provider = make_client()
    sid = _session(client)
    r = client.post(
        "/api/ask",
        data={"session_id": sid},
        files={"image": ("dark.png", _black_png(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["skipped_model"] is True
    assert body["text"]
    assert provider.calls == []
    assert client.get(f"/api/session/{sid}").json()["has_image"] is False


def test_audio_question_is_transcribed_and_asked():
    client, provider = make_client()
    sid = _session(client)
    _photo(client, sid)
    r = client.post(
        "/api/ask",
        data={"session_id": sid},
        files={"audio": ("q.webm", b"fake-audio", "audio/webm")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"] == "what color is it"
    assert body["stt"]["engine"] == "gemini"
    assert provider.calls[-1]["user_text"] == "what color is it"


def test_no_speech_asks_to_repeat_without_calling_the_model():
    client, provider = make_client(transcribe=_heard(""))
    sid = _session(client)
    _photo(client, sid)
    before = len(provider.calls)
    r = client.post(
        "/api/ask",
        data={"session_id": sid},
        files={"audio": ("q.webm", b"fake-audio", "audio/webm")},
    )
    body = r.json()
    assert r.status_code == 200
    assert body["no_speech"] is True
    assert body["skipped_model"] is True
    assert len(provider.calls) == before


def test_text_and_audio_together_is_400():
    client, _ = make_client()
    sid = _session(client)
    r = client.post(
        "/api/ask",
        data={"session_id": sid, "text": "hello"},
        files={"audio": ("q.webm", b"fake-audio", "audio/webm")},
    )
    assert r.status_code == 400


def test_rate_limit_returns_429_with_retry_after():
    client, _ = make_client(limiter=RateLimiter(1))
    sid = _session(client)
    assert _photo(client, sid).status_code == 200
    r = client.post("/api/ask", data={"session_id": sid, "text": "again?"})
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1


def test_provider_error_returns_502_and_leaves_the_session_empty():
    client, _ = make_client(provider=BrokenProvider())
    sid = _session(client)
    r = _photo(client, sid)
    assert r.status_code == 502
    assert client.get(f"/api/session/{sid}").json()["has_image"] is False

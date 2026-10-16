import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.providers import VLMResult

client = TestClient(app)


class FakeProvider:
    name = "fake"

    async def generate(self, **kwargs) -> VLMResult:
        return VLMResult(text="A test description.", provider="fake", model="fake-1", latency_ms=1.0)


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "blue").save(buf, format="PNG")
    return buf.getvalue()


def test_describe_rejects_invalid_image():
    r = client.post(
        "/api/describe",
        files={"image": ("x.png", b"not an image", "image/png")},
        data={"lang": "en"},
    )
    assert r.status_code == 400


def test_describe_rejects_bad_language():
    r = client.post(
        "/api/describe",
        files={"image": ("x.png", _png(), "image/png")},
        data={"lang": "xx"},
    )
    assert r.status_code == 400


def test_describe_success_with_fake_provider(monkeypatch):
    monkeypatch.setattr("app.main.get_provider", lambda: FakeProvider())
    r = client.post(
        "/api/describe",
        files={"image": ("x.png", _png(), "image/png")},
        data={"lang": "fr", "detail": "brief"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "A test description."
    assert body["provider"] == "fake"
    assert "timings_ms" in body


def test_describe_rejects_bad_mode():
    r = client.post(
        "/api/describe",
        files={"image": ("x.png", _png(), "image/png")},
        data={"mode": "banana"},
    )
    assert r.status_code == 400


def test_describe_passes_mode_to_response(monkeypatch):
    monkeypatch.setattr("app.main.get_provider", lambda: FakeProvider())
    r = client.post(
        "/api/describe",
        files={"image": ("x.png", _png(), "image/png")},
        data={"mode": "read", "lang": "ar", "detail": "detailed"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "read"
    assert body["lang"] == "ar"
    assert body["detail"] == "detailed"


def test_modes_endpoint():
    r = client.get("/api/modes")
    assert r.status_code == 200
    assert "find" in r.json()["modes"]

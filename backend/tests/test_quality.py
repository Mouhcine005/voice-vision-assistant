import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter

from app.main import app
from app.providers import VLMResult
from app.quality import MESSAGES, analyze_quality

client = TestClient(app)


def _jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _scene() -> Image.Image:
    """A synthetic 'photo' with plenty of detail (shapes + text)."""
    rng = np.random.default_rng(0)
    img = Image.new("RGB", (1024, 768), (200, 190, 170))
    draw = ImageDraw.Draw(img)
    for _ in range(60):
        x, y = int(rng.integers(0, 900)), int(rng.integers(0, 650))
        w, h = int(rng.integers(20, 120)), int(rng.integers(20, 120))
        color = tuple(int(v) for v in rng.integers(20, 235, 3))
        draw.rectangle((x, y, x + w, y + h), fill=color)
    draw.text((100, 100), "SOME TEXT HERE 12345", fill="black")
    return img


def test_black_image_is_too_dark():
    report = analyze_quality(_jpeg(Image.new("RGB", (640, 480), "black")))
    assert report.severity == "bad"
    assert report.issues[0]["code"] == "too_dark"


def test_white_image_is_too_bright():
    report = analyze_quality(_jpeg(Image.new("RGB", (640, 480), "white")))
    assert report.severity == "bad"
    assert report.issues[0]["code"] == "too_bright"


def test_flat_gray_image_has_low_contrast():
    report = analyze_quality(_jpeg(Image.new("RGB", (640, 480), (128, 128, 128))))
    assert report.severity == "bad"
    assert report.issues[0]["code"] == "low_contrast"


def test_sharp_scene_is_ok():
    report = analyze_quality(_jpeg(_scene()))
    assert report.severity == "ok"
    assert report.issues == []


def test_heavily_blurred_scene_is_bad_blurry():
    report = analyze_quality(_jpeg(_scene().filter(ImageFilter.GaussianBlur(6))))
    assert report.severity == "bad"
    assert report.issues[0]["code"] == "blurry"


def test_slightly_blurred_scene_is_only_a_warning():
    report = analyze_quality(_jpeg(_scene().filter(ImageFilter.GaussianBlur(2))))
    assert report.severity == "warn"


def test_every_message_exists_in_every_language():
    codes = {"too_dark", "too_bright", "blurry", "low_contrast"}
    for lang in ("en", "fr", "ar"):
        assert set(MESSAGES[lang]) == codes
        assert all(MESSAGES[lang][c].strip() for c in codes)


def test_arabic_advice_is_arabic_script():
    report = analyze_quality(_jpeg(Image.new("RGB", (640, 480), "black")))
    text = report.to_dict("ar")["advice"]
    assert any("\u0600" <= ch <= "\u06ff" for ch in text)


class FakeProvider:
    name = "fake"

    def __init__(self):
        self.calls = 0

    async def generate(self, **kwargs) -> VLMResult:
        self.calls += 1
        return VLMResult(text="A description.", provider="fake", model="fake-1", latency_ms=1.0)


def test_quality_endpoint():
    r = client.post(
        "/api/quality",
        files={"image": ("x.jpg", _jpeg(Image.new("RGB", (320, 240), "black")), "image/jpeg")},
        data={"lang": "fr"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["issues"] == ["too_dark"]
    assert "sombre" in body["advice"]


def test_describe_skips_model_on_bad_photo(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr("app.main.get_provider", lambda: provider)
    r = client.post(
        "/api/describe",
        files={"image": ("x.jpg", _jpeg(Image.new("RGB", (320, 240), "black")), "image/jpeg")},
        data={"lang": "en"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["skipped_model"] is True
    assert "too dark" in body["text"]
    assert provider.calls == 0


def test_describe_force_calls_model_even_on_bad_photo(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr("app.main.get_provider", lambda: provider)
    r = client.post(
        "/api/describe",
        files={"image": ("x.jpg", _jpeg(Image.new("RGB", (320, 240), "black")), "image/jpeg")},
        data={"lang": "en", "force": "true"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["skipped_model"] is False
    assert body["text"] == "A description."
    assert body["quality"]["severity"] == "bad"
    assert provider.calls == 1


def test_describe_good_photo_calls_model(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr("app.main.get_provider", lambda: provider)
    r = client.post(
        "/api/describe",
        files={"image": ("x.jpg", _jpeg(_scene()), "image/jpeg")},
        data={"lang": "en"},
    )
    assert r.status_code == 200
    assert r.json()["skipped_model"] is False
    assert provider.calls == 1


def test_old_style_blue_test_image_still_reaches_the_model(monkeypatch):
    """The solid blue 64x64 image used by the older tests is only a 'warn', so it must pass."""
    provider = FakeProvider()
    monkeypatch.setattr("app.main.get_provider", lambda: provider)
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "blue").save(buf, format="PNG")
    r = client.post(
        "/api/describe",
        files={"image": ("x.png", buf.getvalue(), "image/png")},
        data={"lang": "fr", "detail": "brief"},
    )
    assert r.status_code == 200
    assert r.json()["text"] == "A description."

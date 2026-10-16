"""Check the Gemini key: list usable models, then test a text call and an image call.

Usage (from backend/):
    python scripts/check_gemini.py                 # list models
    python scripts/check_gemini.py <model-name>    # list + test that model
Example model name: the part after "models/" in the list output.
"""
import base64
import io
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings  # noqa: E402

BASE = "https://generativelanguage.googleapis.com/v1beta"
HEADERS = {"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"}


def fail(resp: httpx.Response) -> None:
    print(f"\nHTTP {resp.status_code}")
    print(resp.text[:800])
    if resp.status_code in (400, 403):
        print("-> Check the key in backend/.env (no spaces/quotes) and that the key is active.")
    elif resp.status_code == 404:
        print("-> Model name not found. Use a name from the list above.")
    elif resp.status_code == 429:
        print("-> Rate limit/quota hit. Wait a minute, or check your limits in AI Studio.")
    sys.exit(1)


def list_models() -> list[str]:
    r = httpx.get(f"{BASE}/models", headers=HEADERS, params={"pageSize": 200}, timeout=30)
    if r.status_code != 200:
        fail(r)
    names = []
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            names.append(m["name"].removeprefix("models/"))
    print(f"Models that support generateContent ({len(names)}):")
    for n in sorted(names):
        print("  ", n)
    return names


def make_test_image() -> str:
    img = Image.new("RGB", (640, 480), "white")
    d = ImageDraw.Draw(img)
    d.rectangle((80, 120, 280, 320), fill="red")
    d.ellipse((380, 120, 580, 320), fill="blue")
    d.text((220, 400), "HELLO 2026", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def call(model: str, parts: list[dict]) -> tuple[str, float]:
    t0 = time.perf_counter()
    r = httpx.post(
        f"{BASE}/models/{model}:generateContent",
        headers=HEADERS,
        json={"contents": [{"parts": parts}]},
        timeout=60,
    )
    dt = time.perf_counter() - t0
    if r.status_code != 200:
        fail(r)
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        text = f"(no text in response) {str(data)[:500]}"
    return text.strip(), dt


def main() -> None:
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is empty. Fill it in backend/.env first.")
        sys.exit(1)

    list_models()
    if len(sys.argv) < 2:
        print("\nNow run again with a model name to test it.")
        return

    model = sys.argv[1]
    print(f"\n--- Text test with {model} ---")
    text, dt = call(model, [{"text": "Reply with exactly: OK"}])
    print(f"{text!r}  ({dt:.2f}s)")

    print(f"\n--- Image test with {model} ---")
    parts = [
        {"text": "Describe this image in one short sentence and read any text in it."},
        {"inline_data": {"mime_type": "image/jpeg", "data": make_test_image()}},
    ]
    text, dt = call(model, parts)
    print(f"{text}\n({dt:.2f}s)")


if __name__ == "__main__":
    main()

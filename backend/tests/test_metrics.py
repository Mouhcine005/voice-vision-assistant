import io

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.ask import build_ask_router
from app.main import _read_and_prepare
from app.metrics import MetricsStore
from app.providers import ProviderError, VLMResult
from app.ratelimit import RateLimiter
from app.sessions import SessionStore


def _rec(store, total, vlm=0, stt=0, status=200, skipped=False):
    store.record(
        endpoint="ask",
        status=status,
        mode="describe",
        lang="en",
        detail="brief",
        provider="gemini",
        model="m",
        attempts=1,
        skipped_model=skipped,
        timings={"preprocess": 10, "rate_wait": 0, "stt": stt, "vlm": vlm, "total": total},
    )


def test_summary_of_an_empty_store():
    s = MetricsStore().summary()
    assert s["requests"] == 0
    assert s["within_target_pct"] is None
    assert s["stages"]["total"]["p50"] is None


def test_percentiles_and_target_share():
    store = MetricsStore()
    for total in (1000, 2000, 3000, 4000, 5000):
        _rec(store, total)
    s = store.summary()
    assert s["stages"]["total"]["p50"] == 3000
    assert s["stages"]["total"]["p95"] == 5000
    assert s["within_target_pct"] == 80.0


def test_errors_and_skipped_calls_do_not_count_as_latency():
    store = MetricsStore()
    _rec(store, 3000)
    _rec(store, 99999, status=502)
    _rec(store, 5, skipped=True)
    s = store.summary()
    assert s["requests"] == 3
    assert s["errors"] == 1
    assert s["skipped_model"] == 1
    assert s["stages"]["total"]["n"] == 1


def test_stt_stage_ignores_turns_without_speech():
    store = MetricsStore()
    _rec(store, 5000, stt=2000)
    _rec(store, 3000, stt=0)
    _rec(store, 3000, stt=0)
    stt = store.summary()["stages"]["stt"]
    assert stt["n"] == 1
    assert stt["p50"] == 2000


def test_recent_is_newest_first_and_limited():
    store = MetricsStore()
    for total in (1, 2, 3):
        _rec(store, total)
    assert [row["ms_total"] for row in store.recent(2)] == [3, 2]


class FakeProvider:
    name = "fake"

    async def generate(self, **kwargs):
        return VLMResult(text="a description", provider="fake", model="fake-1", latency_ms=7.0)


class BrokenProvider:
    name = "broken"

    async def generate(self, **kwargs):
        raise ProviderError("service down")


async def _no_stt(raw, suffix, lang):
    raise AssertionError("STT should not be called")


def _png() -> bytes:
    buf = io.BytesIO()
    Image.effect_noise((128, 128), 64).convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _ask_with_photo(provider, metrics):
    api = FastAPI()
    api.include_router(
        build_ask_router(
            read_and_prepare=_read_and_prepare,
            transcribe=_no_stt,
            get_provider=lambda: provider,
            store=SessionStore(),
            limiter=RateLimiter(1000),
            metrics=metrics,
        )
    )
    client = TestClient(api)
    sid = client.post("/api/session").json()["session_id"]
    return client.post(
        "/api/ask", data={"session_id": sid}, files={"image": ("a.png", _png(), "image/png")}
    )


def test_successful_ask_is_recorded():
    metrics = MetricsStore()
    r = _ask_with_photo(FakeProvider(), metrics)
    assert r.status_code == 200
    [row] = metrics.recent()
    assert row["endpoint"] == "ask"
    assert row["status"] == 200
    assert row["model"] == "fake-1"
    assert row["ms_vlm"] == 7


def test_provider_failure_is_recorded_as_502():
    metrics = MetricsStore()
    r = _ask_with_photo(BrokenProvider(), metrics)
    assert r.status_code == 502
    [row] = metrics.recent()
    assert row["status"] == 502

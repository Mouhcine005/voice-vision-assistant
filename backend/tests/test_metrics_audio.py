import sqlite3

from app.metrics import MetricsStore


def test_audio_columns_are_stored():
    store = MetricsStore()
    store.record(
        endpoint="ask",
        status=200,
        audio_seconds=3.5,
        convert_ms=120.4,
        api_ms=2500.2,
        timings={"total": 4000},
    )
    [row] = store.recent()
    assert row["audio_s"] == 3.5
    assert row["ms_convert"] == 120
    assert row["ms_api"] == 2500


def test_an_old_database_gets_the_new_columns(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE requests (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
        "endpoint TEXT NOT NULL, status INTEGER NOT NULL, mode TEXT, lang TEXT, detail TEXT, "
        "provider TEXT, model TEXT, used_fallback INTEGER NOT NULL DEFAULT 0, "
        "attempts INTEGER NOT NULL DEFAULT 0, skipped_model INTEGER NOT NULL DEFAULT 0, "
        "stt_engine TEXT, ms_preprocess INTEGER, ms_rate_wait INTEGER, ms_stt INTEGER, "
        "ms_vlm INTEGER, ms_total INTEGER)"
    )
    conn.commit()
    conn.close()
    store = MetricsStore(path)
    store.record(endpoint="ask", status=200, audio_seconds=1.0)
    assert store.recent()[0]["audio_s"] == 1.0


def test_summary_splits_voice_and_text():
    store = MetricsStore()
    store.record(endpoint="ask", status=200, timings={"stt": 3000, "vlm": 2000, "total": 5000})
    store.record(endpoint="ask", status=200, timings={"vlm": 1500, "total": 1600})
    by = store.summary()["by_input"]
    assert by["voice"]["n"] == 1
    assert by["voice"]["within_target_pct"] == 0.0
    assert by["text"]["n"] == 1
    assert by["text"]["within_target_pct"] == 100.0

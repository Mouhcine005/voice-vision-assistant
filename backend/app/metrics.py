"""Per-request timing metrics in SQLite (feeds the Jury panel and the report)."""
import logging
import math
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("uvicorn.error")

TARGET_MS = 4000
STAGES = ("preprocess", "rate_wait", "stt", "vlm", "total")
ONLY_WHEN_RAN = {"preprocess", "stt"}  # these stages are skipped on some turns: ignore the zeros

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    status INTEGER NOT NULL,
    mode TEXT,
    lang TEXT,
    detail TEXT,
    provider TEXT,
    model TEXT,
    used_fallback INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    skipped_model INTEGER NOT NULL DEFAULT 0,
    stt_engine TEXT,
    ms_preprocess INTEGER,
    ms_rate_wait INTEGER,
    ms_stt INTEGER,
    ms_vlm INTEGER,
    ms_total INTEGER
)
"""


def _percentile(values: list[int], pct: float) -> int | None:
    """Nearest-rank percentile."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(pct / 100 * len(ordered)) - 1)
    return ordered[index]


def _ms(value) -> int | None:
    return None if value is None else int(round(value))


class MetricsStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(SCHEMA)
            self._conn.commit()

    def record(
        self,
        *,
        endpoint: str,
        status: int,
        mode: str | None = None,
        lang: str | None = None,
        detail: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        used_fallback: bool = False,
        attempts: int = 0,
        skipped_model: bool = False,
        stt_engine: str | None = None,
        timings: dict | None = None,
    ) -> None:
        """Store one request. Never raises: metrics must not break a real request."""
        timings = timings or {}
        row = (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            endpoint,
            status,
            mode,
            lang,
            detail,
            provider,
            model,
            int(used_fallback),
            attempts,
            int(skipped_model),
            stt_engine,
            _ms(timings.get("preprocess")),
            _ms(timings.get("rate_wait")),
            _ms(timings.get("stt")),
            _ms(timings.get("vlm")),
            _ms(timings.get("total")),
        )
        try:
            with self._lock:
                self._conn.execute(
                    "INSERT INTO requests (ts, endpoint, status, mode, lang, detail, provider, model, "
                    "used_fallback, attempts, skipped_model, stt_engine, ms_preprocess, ms_rate_wait, "
                    "ms_stt, ms_vlm, ms_total) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    row,
                )
                self._conn.commit()
        except sqlite3.Error as exc:
            log.warning("Could not record metrics: %s", exc)

    def _latest(self, limit: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def recent(self, limit: int = 20) -> list[dict]:
        return self._latest(max(1, min(int(limit), 500)))

    def summary(self, window: int = 200) -> dict:
        window = max(1, min(int(window), 2000))
        rows = self._latest(window)
        ok = [r for r in rows if r["status"] < 400 and not r["skipped_model"]]

        stages = {}
        for stage in STAGES:
            values = [r["ms_" + stage] for r in ok if r["ms_" + stage] is not None]
            if stage in ONLY_WHEN_RAN:
                values = [v for v in values if v > 0]
            stages[stage] = {
                "n": len(values),
                "p50": _percentile(values, 50),
                "p95": _percentile(values, 95),
            }

        totals = [r["ms_total"] for r in ok if r["ms_total"] is not None]
        within = (
            round(100 * sum(1 for v in totals if v <= TARGET_MS) / len(totals), 1) if totals else None
        )
        return {
            "window": window,
            "requests": len(rows),
            "errors": sum(1 for r in rows if r["status"] >= 400),
            "skipped_model": sum(1 for r in rows if r["skipped_model"]),
            "fallback_used": sum(1 for r in rows if r["used_fallback"]),
            "target_ms": TARGET_MS,
            "within_target_pct": within,
            "stages": stages,
        }

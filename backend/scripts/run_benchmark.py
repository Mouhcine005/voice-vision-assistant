"""Benchmark the vision models on benchmark/images/manifest.csv.

Usage (from backend/, venv active, key in .env):
    python scripts/run_benchmark.py --dry-run
    python scripts/run_benchmark.py --per-category 1        (smoke test)
    python scripts/run_benchmark.py
    python scripts/run_benchmark.py --models gemini-3.5-flash-lite --lang fr --detail detailed

Every answer is cached in benchmark/cache/ (hash of image + prompt + model), so re-running
costs no quota. Results go to benchmark/results/run_<timestamp>.csv.
Bad-quality photos are still sent to the model here (like force=true); the quality verdict is recorded.
"""
import argparse
import asyncio
import csv
import hashlib
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402
from app.imaging import prepare_image  # noqa: E402
from app.prompts import build_system_prompt, default_question  # noqa: E402
from app.providers.base import ProviderError  # noqa: E402
from app.providers.gemini import GeminiProvider  # noqa: E402
from app.quality import analyze_quality  # noqa: E402
from app.textmetrics import forbidden_hits, mention_score, text_cer  # noqa: E402

IMAGES = BACKEND / "benchmark" / "images"
CACHE = BACKEND / "benchmark" / "cache"
RESULTS = BACKEND / "benchmark" / "results"
DEFAULT_MODELS = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
FIELDS = [
    "id", "category", "mode", "model", "status", "error", "cached", "latency_ms", "attempts", "quality",
    "mention_hit", "mention_total", "coverage", "forbidden_hits", "cer", "usefulness", "manual_hallucination",
    "answer",
]


def load_rows(per_category: int, only: str | None) -> list[dict]:
    with (IMAGES / "manifest.csv").open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    seen: dict[str, int] = defaultdict(int)
    out = []
    for row in rows:
        cat = row["category"]
        if only and cat != only:
            continue
        if per_category and seen[cat] >= per_category:
            continue
        seen[cat] += 1
        out.append(row)
    return out


def prepare(row: dict, lang: str, detail: str):
    """Return ((prepared image, system prompt, question), error text)."""
    path = IMAGES / row["file"]
    if not path.exists():
        return None, "photo missing"
    try:
        prepared = prepare_image(path.read_bytes())
        system_prompt = build_system_prompt(lang, detail, row["mode"])
        question = (row.get("question") or "").strip() or default_question(row["mode"])
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    return (prepared, system_prompt, question), ""


def cache_file(prep, model: str) -> Path:
    prepared, system_prompt, question = prep
    digest = hashlib.sha256()
    for part in (prepared.data, system_prompt.encode(), question.encode(), model.encode()):
        digest.update(part)
        digest.update(b"\0")
    return CACHE / f"{digest.hexdigest()}.json"


def make_result(row: dict, model: str, **extra) -> dict:
    result = {k: "" for k in FIELDS}
    result.update(id=row["id"], category=row["category"], mode=row["mode"], model=model, status="ok", **extra)
    return result


def score(result: dict, row: dict, text: str) -> None:
    hits, total = mention_score(text, row.get("must_mention", ""))
    cer = text_cer(row.get("exact_text", ""), text)
    result.update(
        answer=text.replace("\r", " ").strip(),
        mention_hit=hits,
        mention_total=total,
        coverage=round(hits / total, 3) if total else "",
        forbidden_hits=";".join(forbidden_hits(text, row.get("must_not_mention", ""))),
        cer=round(cer, 3) if cer is not None else "",
    )


def summarize(results: list[dict]) -> None:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in results:
        groups[(r["model"], r["category"])].append(r)

    def mean(values):
        return f"{sum(values) / len(values):.2f}" if values else "-"

    print("\nmodel                    category   ok     latency_med  coverage  cer   forbidden")
    for (model, cat), items in sorted(groups.items()):
        ok = [i for i in items if i["status"] == "ok"]
        lat = [i["latency_ms"] for i in ok if i["latency_ms"] != ""]
        cov = [i["coverage"] for i in ok if i["coverage"] != ""]
        cer = [i["cer"] for i in ok if i["cer"] != ""]
        bad = sum(1 for i in ok if i["forbidden_hits"])
        med = f"{statistics.median(lat) / 1000:.1f} s" if lat else "-"
        print(f"{model:24} {cat:10} {len(ok)}/{len(items):<4} {med:12} {mean(cov):9} {mean(cer):5} {bad}")


async def run(args: argparse.Namespace) -> None:
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    rows = load_rows(args.per_category, args.only)
    prepared_rows = [(row, *prepare(row, args.lang, args.detail)) for row in rows]

    present = [(r, p) for r, p, _ in prepared_rows if p]
    missing = sum(1 for _, _, e in prepared_rows if e == "photo missing")
    broken = [(r["id"], e) for r, _, e in prepared_rows if e and e != "photo missing"]
    to_call = sum(1 for _, p in present for m in models if not cache_file(p, m).exists())
    cached = len(present) * len(models) - to_call

    print(f"rows selected: {len(rows)}   photos found: {len(present)}   photos missing: {missing}   unreadable: {len(broken)}")
    for rid, err in broken:
        print(f"  {rid}: {err}")
    print(f"models: {', '.join(models)}   new requests: {to_call}   already cached: {cached}")
    print(f"estimated time for new requests: {to_call * args.interval / 60:.1f} min (daily limit is 500, shared with the app)")

    if args.dry_run:
        stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
        for row, prep, _ in prepared_rows:
            s = stats[row["category"]]
            s[0] += 1
            s[1] += 1 if prep else 0
            s[2] += 1 if (row.get("must_mention") or row.get("exact_text") or "").strip() else 0
        print(f"\n{'category':10} {'rows':>5} {'photos':>7} {'truth':>6}")
        for cat, (n, ph, tr) in stats.items():
            print(f"{cat:10} {n:>5} {ph:>7} {tr:>6}")
        return

    if not present:
        sys.exit("No photos found in benchmark/images/. Add photos first (see --dry-run).")
    if to_call and not settings.gemini_api_key:
        sys.exit("GEMINI_API_KEY is empty in backend/.env.")
    if to_call > 200 and not args.yes:
        sys.exit(f"{to_call} new requests is a lot of your daily quota. Add --yes to continue.")

    results: list[dict] = []
    try:
        for model in models:
            settings.gemini_model = model
            settings.gemini_fallback_model = ""
            provider = GeminiProvider()
            last_call = 0.0
            for number, (row, prep, err) in enumerate(prepared_rows, 1):
                if err == "photo missing":
                    continue
                if not prep:
                    results.append(make_result(row, model, status="error", error=err))
                    continue
                prepared, system_prompt, question = prep
                quality = analyze_quality(prepared.data).severity
                file = cache_file(prep, model)
                if file.exists():
                    rec = json.loads(file.read_text(encoding="utf-8"))
                    cached_flag = True
                else:
                    wait = args.interval - (time.monotonic() - last_call)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    try:
                        result = await provider.generate(
                            system_prompt=system_prompt,
                            user_text=question,
                            image_bytes=prepared.data,
                            mime_type=prepared.mime_type,
                        )
                    except ProviderError as exc:
                        last_call = time.monotonic()
                        results.append(make_result(row, model, status="error", error=str(exc)[:200], quality=quality))
                        print(f"[{model}] {row['id']}: ERROR {str(exc)[:80]}")
                        continue
                    last_call = time.monotonic()
                    if result.model != model or result.used_fallback:
                        results.append(
                            make_result(row, model, status="error", quality=quality,
                                        error=f"answered by {result.model} (fallback={result.used_fallback})")
                        )
                        print(f"[{model}] {row['id']}: wrong model answered ({result.model})")
                        continue
                    rec = {
                        "text": result.text,
                        "latency_ms": round(result.latency_ms),
                        "attempts": result.attempts,
                    }
                    file.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
                    cached_flag = False
                res = make_result(
                    row, model, cached=int(cached_flag), latency_ms=rec["latency_ms"],
                    attempts=rec["attempts"], quality=quality,
                )
                score(res, row, rec["text"])
                results.append(res)
                print(f"[{model}] {number}/{len(prepared_rows)} {row['id']}: {rec['latency_ms']} ms"
                      f" coverage={res['coverage'] or '-'}{' (cached)' if cached_flag else ''}")
    finally:
        if results:
            RESULTS.mkdir(parents=True, exist_ok=True)
            out = RESULTS / f"run_{datetime.now():%Y%m%d_%H%M%S}.csv"
            with out.open("w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(results)
            print(f"\nresults written to {out}")
            summarize(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=DEFAULT_MODELS)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--detail", default="brief")
    parser.add_argument("--per-category", type=int, default=0, help="only the first N rows of each category")
    parser.add_argument("--only", default=None, help="only this category")
    parser.add_argument("--interval", type=float, default=4.5, help="seconds between new requests per model")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    asyncio.run(run(parser.parse_args()))

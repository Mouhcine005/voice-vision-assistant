"""Summarize a benchmark results CSV into markdown tables for the report.

Usage (from backend/, venv active):
    python scripts/analyze.py                         (latest run in benchmark/results/)
    python scripts/analyze.py benchmark/results/run_20261018_220322.csv

Writes benchmark/results/summary_<run name>.md next to the CSV and prints it.
Median is the usual median (average of the two middle values for an even count); p95 uses nearest-rank (only meaningful with 20 or more rows).
Rows with status other than ok count as errors and are left out of the other columns.
Manual columns (usefulness, manual_hallucination) are summarized only when filled in.
"""
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "benchmark" / "results"
YES = {"1", "true", "yes", "y"}


def num(value):
    try:
        text = str(value).strip()
        return float(text) if text else None
    except ValueError:
        return None


def pct(values, p):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def mean(values):
    return statistics.mean(values) if values else None


def fmt(value, digits=2, suffix=""):
    return "-" if value is None else f"{value:.{digits}f}{suffix}"


def summarize(rows):
    ok = [r for r in rows if r["status"] == "ok"]
    lat = [num(r["latency_ms"]) / 1000 for r in ok if num(r["latency_ms"]) is not None]
    cov = [num(r["coverage"]) for r in ok if num(r["coverage"]) is not None]
    cer = [num(r["cer"]) for r in ok if num(r["cer"]) is not None]
    use = [num(r["usefulness"]) for r in ok if num(r["usefulness"]) is not None]
    flagged = sum(
        1 for r in ok if r["forbidden_hits"] or str(r["manual_hallucination"]).strip().lower() in YES
    )
    return {
        "rows": len(rows),
        "errors": len(rows) - len(ok),
        "p50": statistics.median(lat) if lat else None,
        "p95": pct(lat, 95),
        "cov": mean(cov),
        "full": (sum(1 for c in cov if c >= 0.999) / len(cov) * 100) if cov else None,
        "cer": mean(cer),
        "hall": (flagged / len(ok) * 100) if ok else None,
        "use": mean(use),
    }


def line(model, category, s):
    return (
        f"| {model} | {category} | {s['rows']} | {s['errors']} | {fmt(s['p50'], 1)} | {fmt(s['p95'], 1)} "
        f"| {fmt(s['cov'])} | {fmt(s['full'], 0, '%')} | {fmt(s['cer'])} | {fmt(s['hall'], 0, '%')} | {fmt(s['use'], 1)} |"
    )


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        files = sorted(RESULTS.glob("run_*.csv"))
        if not files:
            sys.exit("No run_*.csv in benchmark/results/. Run run_benchmark.py first.")
        path = files[-1]
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    out = [
        f"Source: {path.name} ({len(rows)} rows)",
        "",
        "| Model | Category | Rows | Errors | Median s | p95 s | Coverage | Fully covered | CER | Hallucination | Usefulness |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for model in sorted(by_model):
        items = by_model[model]
        out.append(line(model, "all", summarize(items)))
        by_cat = defaultdict(list)
        for r in items:
            by_cat[r["category"]].append(r)
        for cat in sorted(by_cat):
            out.append(line(model, cat, summarize(by_cat[cat])))
    out += [
        "",
        "Coverage = share of expected word groups found (mean). Fully covered = answers with coverage 1.0.",
        "CER = character error rate of the expected text inside the answer (mean, text and product rows only).",
        "Hallucination = answers containing a forbidden word or manually flagged. Usefulness = manual 1-5 score (mean).",
    ]
    text = "\n".join(out)
    target = path.parent / f"summary_{path.stem}.md"
    target.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nwritten to {target}")


if __name__ == "__main__":
    main()

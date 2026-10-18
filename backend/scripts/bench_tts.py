r"""Where does the time go between an answer and the first sound? (server must be running)

Usage (from backend/, venv active):
    python scripts/bench_tts.py --runs 3
"""
import argparse
import statistics
import time

import httpx

TEXTS = [
    ("en short", "en", "Stairs ahead."),
    (
        "en 2 sentences",
        "en",
        "There is a large wooden cabinet directly ahead with a television and tall speakers on top. "
        "A long gun hangs on the wall to the right of the television.",
    ),
    ("fr 1 sentence", "fr", "Attention, un escalier devant vous, sur la gauche."),
    (
        "ar 1 sentence",
        "ar",
        "\u0644\u0645 \u0623\u0633\u0645\u0639 \u0633\u0624\u0627\u0644\u0643\u060c "
        "\u0645\u0646 \u0641\u0636\u0644\u0643 \u0623\u0639\u062f "
        "\u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629.",
    ),
]

parser = argparse.ArgumentParser()
parser.add_argument("--runs", type=int, default=3)
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()


def to_float(value: str | None) -> float:
    try:
        return float(value) if value is not None else float("nan")
    except ValueError:
        return float("nan")


rows = []
with httpx.Client(timeout=60) as client:
    for label, lang, text in TEXTS:
        synth, wall, size = [], [], []
        print(f"\n== {label} ({len(text)} chars) ==")
        for run in range(1, args.runs + 1):
            t0 = time.perf_counter()
            r = client.post(f"{args.url}/api/tts", json={"text": text, "lang": lang})
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code != 200:
                print(f"run {run}: HTTP {r.status_code}: {r.text[:200]}")
                continue
            s = to_float(r.headers.get("x-tts-ms"))
            print(f"run {run}: synth={s:.0f} ms  request={ms:.0f} ms  audio={len(r.content) / 1024:.0f} KB  voice={r.headers.get('x-tts-voice')}")
            synth.append(s)
            wall.append(ms)
            size.append(len(r.content) / 1024)
        if wall:
            rows.append((label, len(text), statistics.median(synth), statistics.median(wall), statistics.median(size)))

print("\nMedians")
print(f"{'text':<18}{'chars':>6}{'synth ms':>10}{'request ms':>12}{'audio KB':>10}")
for label, chars, s, w, k in rows:
    print(f"{label:<18}{chars:>6}{s:>10.0f}{w:>12.0f}{k:>10.0f}")

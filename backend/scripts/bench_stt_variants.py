r"""Controlled STT experiment: the same speech in different lengths and formats.

The server must be running. It does not call the vision model.

Usage (from backend/, venv active):
    python scripts/bench_stt_variants.py "benchmark\audio\en.m4a" --runs 4
"""
import argparse
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("audio")
parser.add_argument("--runs", type=int, default=4)
parser.add_argument("--lang", default="")
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()

src = Path(args.audio)
if not src.exists():
    sys.exit(f"File not found: {src}")


def ffmpeg(*cmd: str) -> bool:
    proc = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *cmd], capture_output=True, text=True)
    if proc.returncode != 0:
        print("  (variant skipped:", proc.stderr.strip()[:120], ")")
    return proc.returncode == 0


with tempfile.TemporaryDirectory() as tmp:
    tmp_dir = Path(tmp)
    variants: dict[str, Path] = {"original": src}

    out = tmp_dir / "lead3.wav"
    if ffmpeg("-i", str(src), "-af", "adelay=3000:all=1", str(out)):
        variants["3s_silence_first"] = out

    out = tmp_dir / "double.wav"
    if ffmpeg("-i", str(src), "-i", str(src), "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", str(out)):
        variants["twice_as_long"] = out

    out = tmp_dir / "browser_like.webm"
    if ffmpeg("-i", str(src), "-c:a", "libopus", "-b:a", "32k", str(out)):
        variants["webm_opus"] = out

    summary = []
    with httpx.Client(timeout=90) as client:
        for name, path in variants.items():
            audio_s, convert, api, total = [], [], [], []
            print(f"\n== {name} ==")
            for run in range(1, args.runs + 1):
                with path.open("rb") as fh:
                    r = client.post(
                        f"{args.url}/api/stt",
                        files={"audio": (path.name, fh)},
                        data={"lang": args.lang} if args.lang else None,
                    )
                if r.status_code != 200:
                    print(f"run {run}: HTTP {r.status_code}: {r.text[:200]}")
                    time.sleep(4.5)
                    continue
                b = r.json()
                line = (
                    f"run {run}: audio={b['audio_seconds']} s  convert={b['convert_ms']} ms  "
                    f"api={b['api_ms']} ms  server total={b['timings_ms']['total']} ms  engine={b['engine']}"
                )
                print(line)
                if run == 1:
                    print("   text:", b["text"][:80])
                if b["engine"] == "gemini":
                    audio_s.append(b["audio_seconds"])
                    convert.append(b["convert_ms"])
                    api.append(b["api_ms"])
                    total.append(b["timings_ms"]["total"])
                time.sleep(4.5)
            if total:
                summary.append(
                    (
                        name,
                        statistics.median(audio_s),
                        statistics.median(convert),
                        statistics.median(api),
                        statistics.median(total),
                    )
                )

print("\nMedians per variant")
print(f"{'variant':<20}{'audio s':>9}{'convert ms':>12}{'api ms':>9}{'total ms':>10}")
for name, a, c, p, tt in summary:
    print(f"{name:<20}{a:>9.1f}{c:>12.0f}{p:>9.0f}{tt:>10.0f}")

r"""Compare Whisper model sizes on your own clips (server NOT needed).

Usage (from backend/, venv active):
    python scripts/bench_stt.py "benchmark\audio\a.m4a" "benchmark\audio\b.m4a" --sizes tiny base small
    python scripts/bench_stt.py clip.m4a --lang ar --runs 3
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faster_whisper import WhisperModel  # noqa: E402

from app.config import settings  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("files", nargs="+")
parser.add_argument("--sizes", nargs="+", default=["tiny", "base", "small"])
parser.add_argument("--lang", default="")
parser.add_argument("--runs", type=int, default=2)
args = parser.parse_args()

files = [Path(f) for f in args.files]
for f in files:
    if not f.exists():
        sys.exit(f"File not found: {f}")

print(
    f"compute={settings.whisper_compute_type} beam={settings.whisper_beam_size} "
    f"threads={settings.whisper_cpu_threads} lang={args.lang or 'auto'}"
)

for size in args.sizes:
    t0 = time.perf_counter()
    model = WhisperModel(
        size,
        device="cpu",
        compute_type=settings.whisper_compute_type,
        cpu_threads=settings.whisper_cpu_threads,
    )
    print(f"\n== {size} (load {time.perf_counter() - t0:.1f} s) ==")
    for f in files:
        times = []
        text = ""
        language = ""
        for _ in range(args.runs):
            t1 = time.perf_counter()
            segments, info = model.transcribe(
                str(f),
                language=args.lang or None,
                beam_size=settings.whisper_beam_size,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            language = info.language
            times.append(time.perf_counter() - t1)
        shown = " / ".join(f"{t:.1f}" for t in times)
        print(f"{f.name[:28]:<28} {language:>3}  {shown} s  |  {text}")

"""Download and load the Whisper model once, so the first API call is fast."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.stt import get_model  # noqa: E402

t0 = time.perf_counter()
get_model()
print(f"Whisper model ready in {time.perf_counter() - t0:.1f} s")

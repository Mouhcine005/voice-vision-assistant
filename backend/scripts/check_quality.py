r"""Print quality metrics for your own photos, to calibrate the thresholds in app/quality.py.

Usage (from backend/, no server needed):
    python scripts/check_quality.py "C:\path\photo1.jpg" "C:\path\photo2.jpg"
    python scripts/check_quality.py "C:\path\folder_with_photos"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.imaging import ImageError, prepare_image  # noqa: E402
from app.quality import analyze_quality  # noqa: E402

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def collect(args: list[str]) -> list[Path]:
    files: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in EXTENSIONS)
        elif p.exists():
            files.append(p)
        else:
            print(f"Not found: {p}")
    return files


def main() -> None:
    files = collect(sys.argv[1:])
    if not files:
        sys.exit("Give at least one image file or a folder of images.")
    print(f"{'file':<38} {'bright':>7} {'contrast':>9} {'sharp':>8}  verdict")
    for f in files:
        try:
            prepared = prepare_image(f.read_bytes())
            report = analyze_quality(prepared.data)
        except ImageError as exc:
            print(f"{f.name[:38]:<38} (skipped: {exc})")
            continue
        m = report.metrics
        verdict = report.severity + (" " + ",".join(i["code"] for i in report.issues) if report.issues else "")
        print(f"{f.name[:38]:<38} {m['brightness']:>7} {m['contrast']:>9} {m['sharpness']:>8}  {verdict}")


if __name__ == "__main__":
    main()

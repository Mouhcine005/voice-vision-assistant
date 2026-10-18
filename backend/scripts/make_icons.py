"""Generate PWA icons into frontend/public (eye glyph, accent on dark)."""
from pathlib import Path

from PIL import Image, ImageDraw

BG = (10, 10, 10, 255)
ACCENT = (255, 214, 10, 255)
SIZE = 1024
OUT = Path(__file__).resolve().parents[2] / "frontend" / "public"


def draw_icon(scale: float) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    c = SIZE // 2
    w, h = int(620 * scale), int(360 * scale)
    d.ellipse((c - w // 2, c - h // 2, c + w // 2, c + h // 2), outline=ACCENT, width=int(46 * scale))
    r = int(95 * scale)
    d.ellipse((c - r, c - r, c + r, c + r), fill=ACCENT)
    return img


def save(img: Image.Image, name: str, size: int) -> None:
    path = OUT / name
    img.resize((size, size), Image.Resampling.LANCZOS).save(path)
    print("wrote", path)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    regular = draw_icon(1.1)
    maskable = draw_icon(0.9)  # glyph kept inside the maskable safe zone
    save(regular, "pwa-192.png", 192)
    save(regular, "pwa-512.png", 512)
    save(maskable, "pwa-maskable-512.png", 512)
    save(regular, "apple-touch-icon.png", 180)

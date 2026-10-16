import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings


class ImageError(ValueError):
    """The uploaded file is empty or is not a usable image."""


@dataclass
class PreparedImage:
    data: bytes
    mime_type: str
    width: int
    height: int
    original_bytes: int


def prepare_image(raw: bytes, max_side: int | None = None) -> PreparedImage:
    """Decode, fix EXIF rotation, flatten transparency, resize, re-encode as JPEG."""
    max_side = max_side or settings.max_image_side
    if not raw:
        raise ImageError("The uploaded file is empty.")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageError("The uploaded file is not a valid image.") from exc

    img = ImageOps.exif_transpose(img)

    if img.mode != "RGB":
        if img.mode in ("RGBA", "LA") or "transparency" in img.info:
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        else:
            img = img.convert("RGB")

    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return PreparedImage(
        data=buffer.getvalue(),
        mime_type="image/jpeg",
        width=img.width,
        height=img.height,
        original_bytes=len(raw),
    )

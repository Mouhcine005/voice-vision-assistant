import io

import pytest
from PIL import Image

from app.imaging import ImageError, prepare_image


def _png_bytes(size, mode="RGB", color="red") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_large_image_is_resized():
    prepared = prepare_image(_png_bytes((3000, 2000)))
    assert max(prepared.width, prepared.height) <= 1024
    assert prepared.mime_type == "image/jpeg"
    assert prepared.original_bytes > 0


def test_rgba_image_is_converted():
    prepared = prepare_image(_png_bytes((200, 100), mode="RGBA", color=(255, 0, 0, 128)))
    assert prepared.width == 200
    assert prepared.height == 100


def test_invalid_image_raises():
    with pytest.raises(ImageError):
        prepare_image(b"this is not an image")

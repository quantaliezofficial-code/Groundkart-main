"""
Image optimisation for uploads.

Every venue photo and banner goes through here before it is stored:

* The bytes are decoded with Pillow. If they are not really an image the
  upload is refused, whatever the Content-Type header claimed.
* EXIF orientation is applied, then all metadata (including GPS position
  from a phone camera) is dropped.
* The long edge is capped and the result is written as WebP.

A 6 MB phone photo typically becomes 150-350 KB with no visible loss at
the sizes the site shows it. That is the single biggest page-speed win
available on listing and search pages.
"""
from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.storage.base import UnsupportedFileError

# Largest size any layout shows a photo (full-width lightbox on a large
# monitor), with headroom for 1.5x density.
MAX_LONG_EDGE = 2000
BANNER_MAX_LONG_EDGE = 2400
WEBP_QUALITY = 80
# Decompression-bomb guard: refuse absurd pixel counts before decoding.
MAX_PIXELS = 60_000_000

IMAGE_INPUT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def optimize_image(content: bytes, *, max_long_edge: int = MAX_LONG_EDGE) -> tuple[bytes, str, tuple[int, int]]:
    """Returns (webp_bytes, "image/webp", (width, height)).

    Raises UnsupportedFileError if the bytes cannot be decoded as an image
    or the image is unreasonably large — callers turn that into a 422."""
    if not content:
        raise UnsupportedFileError("Empty file")
    try:
        probe = Image.open(io.BytesIO(content))
        if probe.width * probe.height > MAX_PIXELS:
            raise UnsupportedFileError("Image dimensions are too large")
        probe.verify()
        img = Image.open(io.BytesIO(content))
        img.load()
    except UnsupportedFileError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise UnsupportedFileError("This file is not a valid image")

    if getattr(img, "is_animated", False):
        img.seek(0)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("P", "LA"):
        img = img.convert("RGBA")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    if max(img.size) > max_long_edge:
        img.thumbnail((max_long_edge, max_long_edge), Image.LANCZOS)

    out = io.BytesIO()
    # Re-encoding into a fresh buffer is what strips EXIF/ICC/XMP: nothing
    # from the source container is carried over unless passed explicitly.
    img.save(out, format="WEBP", quality=WEBP_QUALITY, method=5)
    return out.getvalue(), "image/webp", img.size

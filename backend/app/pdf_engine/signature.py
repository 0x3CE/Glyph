"""Placing a signature onto a page at a given rectangle.

The signature source is always a file: an uploaded PDF (typically a
signature exported/scanned as its own one-page document -- placed via
`show_pdf_page` so it stays vector-crisp instead of being rasterized), an
uploaded PNG/JPEG, or a PNG the frontend's drawing canvas exported. All
three arrive here as raw bytes with no reliable extension, so the type is
sniffed from the bytes themselves (magic numbers) rather than trusted from
a client-supplied content-type -- the same reasoning as
`worker_validate_pdf` for the main document: this is untrusted input, and
runs inside the same isolated subprocess (see `app.isolation`).
"""

from __future__ import annotations

import pymupdf


class UnsupportedSignatureFileError(Exception):
    """Raised when the uploaded bytes are not a PDF/PNG/JPEG we can place,
    or a PDF we can't use as one (password-protected, empty)."""


def _looks_like_pdf(data: bytes) -> bool:
    return data.lstrip()[:5] == b"%PDF-"


def _looks_like_png(data: bytes) -> bool:
    return data[:8] == b"\x89PNG\r\n\x1a\n"


def _looks_like_jpeg(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff"


def apply_signature(
    doc: pymupdf.Document,
    page: pymupdf.Page,
    signature_bytes: bytes,
    bbox: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Stamps `signature_bytes` into `bbox` (PDF points, [x0, y0, x1, y1])
    on `page`, stretched to exactly fill it -- the frontend's placement box
    already reflects whatever aspect ratio the user chose by dragging its
    corner, so there's no separate aspect-ratio concern to preserve here.
    """
    rect = pymupdf.Rect(*bbox)
    if _looks_like_pdf(signature_bytes):
        src = pymupdf.open(stream=signature_bytes, filetype="pdf")
        if src.needs_pass:
            raise UnsupportedSignatureFileError("password-protected PDFs are not supported")
        if src.page_count < 1:
            raise UnsupportedSignatureFileError("the PDF has no pages")
        page.show_pdf_page(rect, src, 0)
    elif _looks_like_png(signature_bytes) or _looks_like_jpeg(signature_bytes):
        page.insert_image(rect, stream=signature_bytes)
    else:
        raise UnsupportedSignatureFileError("unsupported file -- expected a PDF, PNG, or JPEG")
    return (rect.x0, rect.y0, rect.x1, rect.y1)

"""Entry points called from inside the isolated subprocess (see
`app.isolation.run_isolated`) -- the only functions of this package that
main.py calls directly.

Each returns `(meta, blob)`: JSON-serializable metadata plus raw bytes (a
re-saved PDF) or None. Never Python objects: the parent doesn't unpickle
anything coming out of a process that just parsed an untrusted PDF.
"""

from __future__ import annotations

import io
from typing import Any

import pymupdf

from .editor import apply_block_edit
from .signature import apply_signature
from .structure import extract_structure
from .types import Block, EncryptedPdfError

Meta = dict[str, Any]


def _block_to_json(block: Block) -> Meta:
    return {
        "id": block.id,
        "bbox": block.bbox,
        "text": block.text,
        "lines": [
            {
                "bbox": line.bbox,
                "spans": [
                    {"text": s.text, "bbox": s.bbox, "font": s.font, "size": s.size, "color": s.color, "flags": s.flags}
                    for s in line.spans
                ],
            }
            for line in block.lines
        ],
    }


def worker_validate_pdf(raw: bytes) -> tuple[Meta, None]:
    """Isolation worker (see isolation.run_isolated): opening bytes nobody
    here produced is the single highest-risk operation in this app."""
    doc = pymupdf.open(stream=raw, filetype="pdf")
    if doc.needs_pass:
        raise EncryptedPdfError("password-protected PDFs are not supported -- please remove the password first")
    return {"page_count": doc.page_count}, None


def worker_extract_structure(pdf_bytes: bytes, page_index: int) -> tuple[Meta, None]:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    if not (0 <= page_index < doc.page_count):
        raise IndexError("page not found")
    page = doc[page_index]
    return {
        "width": page.rect.width,
        "height": page.rect.height,
        "blocks": [_block_to_json(b) for b in extract_structure(page)],
    }, None


def worker_apply_edit(
    pdf_bytes: bytes, page_index: int, block_id: str, new_text: str
) -> tuple[Meta, bytes]:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    if not (0 <= page_index < doc.page_count):
        raise IndexError("page not found")
    page = doc[page_index]
    blocks = extract_structure(page)
    block = next((b for b in blocks if b.id == block_id), None)
    if block is None:
        raise LookupError("block not found")

    substituted, new_bbox = apply_block_edit(doc, page, block, new_text, all_blocks=blocks)
    buf = io.BytesIO()
    doc.save(buf)
    return {"font_substituted": substituted, "new_bbox": new_bbox}, buf.getvalue()


def worker_add_signature(
    pdf_bytes: bytes, page_index: int, signature_bytes: bytes, bbox: tuple[float, float, float, float]
) -> tuple[Meta, bytes]:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    if not (0 <= page_index < doc.page_count):
        raise IndexError("page not found")
    page = doc[page_index]
    new_bbox = apply_signature(doc, page, signature_bytes, bbox)
    buf = io.BytesIO()
    doc.save(buf)
    return {"bbox": new_bbox}, buf.getvalue()

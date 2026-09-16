"""Entry points called from inside the isolated subprocess (see
`app.isolation.run_isolated`) -- the only functions of this package that
main.py calls directly.
"""

from __future__ import annotations

import io

import pymupdf

from .editor import apply_block_edit
from .structure import extract_structure
from .types import EncryptedPdfError, StructureResult


def worker_validate_pdf(raw: bytes) -> int:
    """Isolation worker (see isolation.run_isolated): opening bytes nobody
    here produced is the single highest-risk operation in this app."""
    doc = pymupdf.open(stream=raw, filetype="pdf")
    if doc.needs_pass:
        raise EncryptedPdfError("password-protected PDFs are not supported -- please remove the password first")
    return doc.page_count


def worker_extract_structure(pdf_bytes: bytes, page_index: int) -> StructureResult:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    if not (0 <= page_index < doc.page_count):
        raise IndexError("page not found")
    page = doc[page_index]
    return StructureResult(width=page.rect.width, height=page.rect.height, blocks=extract_structure(page))


def worker_apply_edit(
    pdf_bytes: bytes, page_index: int, block_id: str, new_text: str
) -> tuple[bytes, bool, tuple[float, float, float, float]]:
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
    return buf.getvalue(), substituted, new_bbox

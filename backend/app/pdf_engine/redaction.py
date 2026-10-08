"""Real redaction, metadata clean-up, and inspection of what a PDF still hides.

Three operations around the same promise as text editing: content that is
removed must really be gone from the file, not just covered.

- `redact_areas`: deletes everything under the given rectangles (text,
  image pixels, vector shapes fully inside) and paints them black.
- `sanitize_document`: strips what identifies a document or its author
  (info dictionary, XMP metadata, attachments, JavaScript, invisible text,
  thumbnails...) -- the payslip a user "anonymized" with black boxes still
  had their name and employee number in its keywords.
- `inspect_document`: reports, without changing anything, what a PDF hides:
  text covered by an opaque shape or image drawn after it (a white-box
  "edit" or a black-box "redaction"), redactions marked but never applied, invisible
  text, metadata, earlier versions kept by incremental saves, attachments.
"""

from __future__ import annotations

import pymupdf

# Inspection limits: enough for real documents, bounded for hostile ones
# (the sandbox caps CPU time anyway).
MAX_INSPECTED_PAGES = 300
MAX_FINDINGS = 50
SNIPPET_CHARS = 120
# A text run counts as hidden when a later opaque shape covers this much of it.
COVERED_RATIO = 0.6
# An image this large is a scanned page: text drawn under it is its OCR
# layer (some tools hide it that way rather than as invisible text).
SCAN_PAGE_RATIO = 0.8

METADATA_KEYS = ("title", "author", "subject", "keywords", "creator", "producer", "creationDate", "modDate")


def redact_areas(page: pymupdf.Page, rects: list[tuple[float, float, float, float]]) -> int:
    """Removes everything under `rects` (PDF points) and fills them black.
    Returns how many areas were applied."""
    page_rect = page.rect
    applied = 0
    for coords in rects:
        rect = pymupdf.Rect(coords) & page_rect
        if rect.is_empty or rect.width < 1 or rect.height < 1:
            continue
        page.add_redact_annot(rect, fill=(0, 0, 0))
        applied += 1
    if applied:
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_PIXELS,  # blank the pixels under the area, keep the rest of the image
            graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,  # shapes fully inside; table borders crossing it stay
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
    return applied


def _metadata(doc: pymupdf.Document) -> dict[str, str]:
    meta = doc.metadata or {}
    return {key: str(meta[key])[:SNIPPET_CHARS] for key in METADATA_KEYS if meta.get(key)}


def sanitize_document(doc: pymupdf.Document) -> list[str]:
    """Strips identifying data in place. Returns what was found and removed,
    as stable keys the frontend translates."""
    removed = [f"metadata.{key}" for key in _metadata(doc)]
    if doc.get_xml_metadata().strip():
        removed.append("xmp")
    if doc.embfile_count():
        removed.append("attachments")
    doc.scrub(
        attached_files=True,
        clean_pages=True,
        embedded_files=True,
        hidden_text=True,
        javascript=True,
        metadata=True,
        redactions=True,  # a redaction marked but never applied still hides nothing
        redact_images=0,
        remove_links=False,  # links are content, not metadata
        reset_fields=False,  # never wipe what the user typed in form fields
        reset_responses=True,
        thumbnails=True,
        xml_metadata=True,
    )
    doc.set_metadata({})
    return removed


def _opaque_cover_rects(page: pymupdf.Page) -> tuple[list[tuple[int, pymupdf.Rect]], list[tuple[int, pymupdf.Rect]]]:
    """(drawing order, rect) of every opaque filled shape, image without
    transparency, and filled rectangle-like annotation on the page; and,
    separately, of the page-sized images (scans)."""
    covers = []
    scans = []
    scan_area = SCAN_PAGE_RATIO * page.rect.get_area()
    for drawing in page.get_drawings():
        if drawing.get("fill") is not None and (drawing.get("fill_opacity") or 1) >= 0.99:
            covers.append((drawing.get("seqno", 0), pymupdf.Rect(drawing["rect"])))
    # A pasted black (or white) image hides text as well as a shape. The
    # bbox log lists everything in drawing order, so its index is the same
    # `seqno` as text spans. Images with a transparency mask (a stamp, a
    # logo) can let the text show through: left out.
    masked = [pymupdf.Rect(info["bbox"]) for info in page.get_image_info() if info.get("has-mask")]
    for order, (kind, bbox) in enumerate(page.get_bboxlog()):
        if kind != "fill-image":
            continue
        rect = pymupdf.Rect(bbox)
        if any(abs(rect.x0 - m.x0) + abs(rect.y0 - m.y0) + abs(rect.x1 - m.x1) + abs(rect.y1 - m.y1) < 1 for m in masked):
            continue
        (scans if (rect & page.rect).get_area() >= scan_area else covers).append((order, rect))
    # Annotations are drawn on top of the page content, whatever its order.
    for annot in page.annots() or []:
        if annot.type[1] in ("Square", "FreeText", "Ink", "Polygon") and annot.colors.get("fill"):
            covers.append((10**9, pymupdf.Rect(annot.rect)))
    return covers, scans


def inspect_document(doc: pymupdf.Document) -> dict:
    hidden: list[dict] = []
    invisible_chars = 0
    invisible_samples: list[dict] = []
    unapplied_redactions = 0
    annotations: dict[str, int] = {}

    for page_index in range(min(doc.page_count, MAX_INSPECTED_PAGES)):
        page = doc[page_index]
        covers, scans = _opaque_cover_rects(page)
        for annot in page.annots() or []:
            kind = annot.type[1]
            annotations[kind] = annotations.get(kind, 0) + 1
            if kind == "Redact":
                unapplied_redactions += 1
        for span in page.get_texttrace():
            text = "".join(chr(c[0]) for c in span["chars"]).strip()
            if not text:
                continue
            bbox = pymupdf.Rect(span["bbox"])
            seqno = span.get("seqno", 0)
            under_scan = any(order > seqno and bbox.intersects(rect) for order, rect in scans)
            if span.get("type") == 3 or span.get("opacity", 1) == 0 or under_scan:
                invisible_chars += len(text)
                if len(invisible_samples) < MAX_FINDINGS:
                    invisible_samples.append({"page": page_index + 1, "text": text[:SNIPPET_CHARS]})
                continue
            area = bbox.get_area()
            if area <= 0:
                continue
            if any(order > seqno and (bbox & rect).get_area() >= COVERED_RATIO * area for order, rect in covers):
                if len(hidden) < MAX_FINDINGS:
                    hidden.append({"page": page_index + 1, "text": text[:SNIPPET_CHARS]})

    return {
        "page_count": doc.page_count,
        "pages_inspected": min(doc.page_count, MAX_INSPECTED_PAGES),
        "hidden_text": hidden,
        "unapplied_redactions": unapplied_redactions,
        "invisible_text_chars": invisible_chars,
        "invisible_text_samples": invisible_samples[:5],
        "metadata": _metadata(doc),
        "has_xmp": bool(doc.get_xml_metadata().strip()),
        "versions": max(1, doc.version_count),
        "attachments": [doc.embfile_info(i)["name"] for i in range(doc.embfile_count())][:MAX_FINDINGS],
        "annotations": annotations,
    }

"""Turning a PyMuPDF page into the engine's own Block model."""

from __future__ import annotations

import pymupdf

from .types import Block, _line_from_raw


def extract_structure(page: pymupdf.Page) -> list[Block]:
    """One PyMuPDF text line = one editable block, always -- no attempt to
    merge multiple lines into a reflow-capable paragraph. See
    docs/DECISIONS.md ("Édition strictement ligne par ligne") for why: a
    merge heuristic based on shared edges/alignment kept finding new real
    documents where independent lines (a title stacked on a subtitle, a
    right-aligned column of unrelated values) coincidentally look just like
    a wrapped paragraph, and merging them let one edit corrupt an unrelated
    line. Per-line editing is immune to that entire bug class by
    construction, at the cost of needing several clicks for a field that
    visually spans multiple lines (e.g. an address).

    This also gets "two runs on the same visual line but far apart
    horizontally should be separate fields" for free: PyMuPDF's own line
    segmentation already starts a new line for a gap around one font-size
    or more (verified empirically), well below anything meant to look like
    deliberate separate fields (e.g. a form's "Label :        VALUE").
    """
    raw = page.get_text("dict")
    blocks: list[Block] = []
    for i, b in enumerate(raw["blocks"]):
        if b.get("type") != 0:
            continue  # skip image blocks
        lines = [_line_from_raw(line) for line in b["lines"]]
        for j, line in enumerate(lines):
            if line.spans:
                blocks.append(Block(id=f"b{i}l{j}", bbox=line.bbox, lines=[line]))
    return blocks

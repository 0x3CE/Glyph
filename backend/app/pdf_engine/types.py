"""Shared data types for the PDF editing engine: the structural model
`extract_structure` produces (Span/Line/Block) and the two small exceptions/
result types the FastAPI layer talks to.
"""

from __future__ import annotations

from dataclasses import dataclass

FLAG_ITALIC = 1 << 1
FLAG_SERIF = 1 << 2
FLAG_MONOSPACE = 1 << 3
FLAG_BOLD = 1 << 4


def rgb_int_to_tuple(color: int) -> tuple[float, float, float]:
    r = ((color >> 16) & 255) / 255
    g = ((color >> 8) & 255) / 255
    b = (color & 255) / 255
    return (r, g, b)


@dataclass
class Span:
    text: str
    bbox: tuple[float, float, float, float]
    font: str
    size: float
    color: int
    flags: int
    origin: tuple[float, float]  # exact baseline start point, as PyMuPDF recorded it


@dataclass
class Line:
    bbox: tuple[float, float, float, float]
    spans: list[Span]


@dataclass
class Block:
    id: str
    bbox: tuple[float, float, float, float]
    lines: list[Line]

    @property
    def text(self) -> str:
        return "\n".join("".join(s.text for s in line.spans) for line in self.lines)

    @property
    def dominant_span(self) -> Span:
        # The span covering the most characters "represents" the block's
        # typography (font/size/color) for reinsertion purposes.
        spans = [s for line in self.lines for s in line.spans]
        return max(spans, key=lambda s: len(s.text))


def _line_from_raw(line: dict) -> Line:
    return Line(
        bbox=tuple(line["bbox"]),
        spans=[
            Span(
                text=s["text"],
                bbox=tuple(s["bbox"]),
                font=s["font"],
                size=s["size"],
                color=s["color"],
                flags=s["flags"],
                origin=tuple(s["origin"]),
            )
            for s in line["spans"]
        ],
    )


@dataclass
class StructureResult:
    width: float
    height: float
    blocks: list[Block]


class EncryptedPdfError(Exception):
    """Raised at upload time for a password-protected PDF. PyMuPDF happily
    opens one and reports a page count without a password, but every real
    operation on it (get_text, redaction, ...) then fails with an opaque
    "document closed or encrypted" error -- catching it here instead gives
    the user an actionable message right away instead of a confusing
    failure the first time they try to click a field."""

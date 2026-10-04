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
    def text_reliable(self) -> bool:
        """False when the PDF's text layer for this line can't be trusted to
        say which characters are drawn. Some generators (payslips, notably)
        ship fonts with no character map and a deliberately scrambled
        ToUnicode table, so "Emploi : INGENIEUR SYSTEME" extracts as
        "6T:SVR... 1 :!86!:6EB CHCD6 6": the page looks fine, but the text
        we'd put in the edit field (and diff the user's edit against) is
        garbage. Control characters (spaces come out as U+0001 there) and
        U+FFFD (no mapping at all) give it away."""
        return not any((ord(c) < 32 and c not in "\t\n") or c == "\ufffd" for c in self.text)

    @property
    def dominant_span(self) -> Span:
        # The span covering the most characters "represents" the block's
        # typography (font/size/color) for reinsertion purposes.
        spans = [s for line in self.lines for s in line.spans]
        return max(spans, key=lambda s: len(s.text))


def _is_monospaced(chars: list[dict]) -> bool:
    """Every character advances by the same amount (spaces included): a
    fixed-width font, whatever its name or descriptor flags say. Measured on
    the page itself because neither is reliable -- a payslip seen in the wild
    had four different fonts (two proportional, two Courier-like) all under
    the same scrambled name, all flagged "serif"."""
    if len(chars) < 4:
        return False
    xs = [c["origin"][0] for c in chars]
    steps = [b - a for a, b in zip(xs, xs[1:])]
    first = steps[0]
    return first > 0 and all(abs(step - first) <= first * 0.02 for step in steps)


def _line_from_raw(line: dict) -> Line:
    """`line` from page.get_text("rawdict"): spans carry per-character data
    ("chars") instead of a "text" string."""
    spans = []
    for s in line["spans"]:
        chars = s.get("chars", [])
        flags = s["flags"]
        if _is_monospaced(chars):
            flags |= FLAG_MONOSPACE
        spans.append(
            Span(
                text="".join(c["c"] for c in chars) if chars else s.get("text", ""),
                bbox=tuple(s["bbox"]),
                font=s["font"],
                size=s["size"],
                color=s["color"],
                flags=flags,
                origin=tuple(s["origin"]),
            )
        )
    return Line(bbox=tuple(line["bbox"]), spans=spans)


class EncryptedPdfError(Exception):
    """Raised at upload time for a password-protected PDF. PyMuPDF happily
    opens one and reports a page count without a password, but every real
    operation on it (get_text, redaction, ...) then fails with an opaque
    "document closed or encrypted" error -- catching it here instead gives
    the user an actionable message right away instead of a confusing
    failure the first time they try to click a field."""

"""Core PDF editing engine, built on PyMuPDF.

Key fact validated empirically (see project notes): PyMuPDF can genuinely
remove existing glyph-drawing operators (via redaction) and reinsert new
text, which is real non-overlay editing. But most real-world PDFs (anything
produced by Word / a print-to-PDF driver) embed their fonts as Identity-H
CID-keyed subsets with NO usable cmap table -- extracting those font bytes
and reusing them for arbitrary new text silently produces garbage glyphs.
We only reuse an original embedded font when we can verify (via fontTools)
that it has a cmap covering every character of the new text; otherwise we
fall back to a metrically-matched Base14 font and report the substitution.
"""

from __future__ import annotations

import io
import re
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from fontTools.ttLib import TTFont, TTLibError

FLAG_ITALIC = 1 << 1
FLAG_SERIF = 1 << 2
FLAG_MONOSPACE = 1 << 3
FLAG_BOLD = 1 << 4

_BASE14 = {
    ("sans", False, False): "helv",
    ("sans", False, True): "heit",
    ("sans", True, False): "hebo",
    ("sans", True, True): "hebi",
    ("serif", False, False): "tiro",
    ("serif", False, True): "tiit",
    ("serif", True, False): "tibo",
    ("serif", True, True): "tibi",
    ("mono", False, False): "cour",
    ("mono", False, True): "coit",
    ("mono", True, False): "cobo",
    ("mono", True, True): "cobi",
}


def _base14_for(flags: int) -> str:
    bold = bool(flags & FLAG_BOLD)
    italic = bool(flags & FLAG_ITALIC)
    family = "mono" if flags & FLAG_MONOSPACE else "serif" if flags & FLAG_SERIF else "sans"
    return _BASE14[(family, bold, italic)]


# PyMuPDF's built-in Base-14 fonts are a last resort only: they lack basic
# glyphs a lot of real documents actually need (the Euro sign among them --
# a substituted amount silently rendered as "?"). Real system font files
# (present on any Mac) cover far more of Unicode, including Euro, and often
# let us match the ORIGINAL font family by name (e.g. "ArialNarrow" in the
# PDF -> the real Arial Narrow.ttf) instead of a generic Helvetica -- much
# closer to the original than a Base-14 alias would ever be.
_SYSTEM_FONT_DIR = Path("/System/Library/Fonts/Supplemental")

_SYSTEM_FAMILIES: dict[str, dict[tuple[bool, bool], str]] = {
    "arial narrow": {
        (False, False): "Arial Narrow.ttf",
        (True, False): "Arial Narrow Bold.ttf",
        (False, True): "Arial Narrow Italic.ttf",
        (True, True): "Arial Narrow Bold Italic.ttf",
    },
    "arial": {
        (False, False): "Arial.ttf",
        (True, False): "Arial Bold.ttf",
        (False, True): "Arial Italic.ttf",
        (True, True): "Arial Bold Italic.ttf",
    },
    "times new roman": {
        (False, False): "Times New Roman.ttf",
        (True, False): "Times New Roman Bold.ttf",
        (False, True): "Times New Roman Italic.ttf",
        (True, True): "Times New Roman Bold Italic.ttf",
    },
    "courier new": {
        (False, False): "Courier New.ttf",
        (True, False): "Courier New Bold.ttf",
        (False, True): "Courier New Italic.ttf",
        (True, True): "Courier New Bold Italic.ttf",
    },
    "georgia": {
        (False, False): "Georgia.ttf",
        (True, False): "Georgia Bold.ttf",
        (False, True): "Georgia Italic.ttf",
        (True, True): "Georgia Bold Italic.ttf",
    },
    "verdana": {
        (False, False): "Verdana.ttf",
        (True, False): "Verdana Bold.ttf",
        (False, True): "Verdana Italic.ttf",
        (True, True): "Verdana Bold Italic.ttf",
    },
    "tahoma": {
        (False, False): "Tahoma.ttf",
        (True, False): "Tahoma Bold.ttf",
        (False, True): "Tahoma.ttf",
        (True, True): "Tahoma Bold.ttf",
    },
}

# Fonts that don't exist as a real file on this system get mapped to the
# closest widely-available family instead of falling all the way back to
# Base-14. Ordered by specificity: narrower/more distinctive names first.
_FAMILY_ALIASES: list[tuple[str, str]] = [
    ("arialnarrow", "arial narrow"),
    ("arial", "arial"),
    ("helvetica", "arial"),
    ("calibri", "arial"),
    ("segoe", "verdana"),
    ("tahoma", "tahoma"),
    ("verdana", "verdana"),
    ("timesnewroman", "times new roman"),
    ("times", "times new roman"),
    ("cambria", "times new roman"),
    ("georgia", "georgia"),
    ("garamond", "georgia"),
    ("courier", "courier new"),
    ("consolas", "courier new"),
    ("lucidaconsole", "courier new"),
]


def _normalize_font_name(name: str) -> str:
    # Strip a subset tag ("EAAAAB+ArialNarrow" -> "ArialNarrow"), any
    # style suffix words, and non-alphanumerics, then lowercase.
    name = name.split("+")[-1]
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _family_for_original(font_name: str) -> str | None:
    normalized = _normalize_font_name(font_name)
    for needle, family in _FAMILY_ALIASES:
        if needle in normalized:
            return family
    return None


def _generic_family_for_flags(flags: int) -> str:
    if flags & FLAG_MONOSPACE:
        return "courier new"
    if flags & FLAG_SERIF:
        return "times new roman"
    return "arial"


def _system_font_path(family: str, bold: bool, italic: bool) -> str | None:
    variants = _SYSTEM_FAMILIES.get(family)
    if not variants:
        return None
    filename = variants.get((bold, italic)) or variants.get((False, False))
    if not filename:
        return None
    path = _SYSTEM_FONT_DIR / filename
    return str(path) if path.is_file() else None


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


def _spread(values: list[float]) -> float:
    return max(values) - min(values) if values else 0.0


def _is_coherent_paragraph(lines: list[Line]) -> bool:
    """PyMuPDF's block detector clusters purely by vertical proximity, with
    no notion of table columns -- a table row (or a whole table body) can
    end up as a single "block" whose lines are actually unrelated cells
    sitting at wildly different x-positions. A genuine wrapped paragraph's
    lines all start near the same left edge (or, for right/justified text,
    end near the same right edge); a merged table doesn't. One line is
    trivially coherent (nothing to confuse it with).
    """
    if len(lines) <= 1:
        return True
    sizes = [s.size for line in lines for s in line.spans] or [10.0]
    threshold = max(15.0, (sum(sizes) / len(sizes)) * 1.5)
    x0s = [line.bbox[0] for line in lines]
    x1s = [line.bbox[2] for line in lines]
    return _spread(x0s) <= threshold or _spread(x1s) <= threshold


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


def extract_structure(page: pymupdf.Page) -> list[Block]:
    raw = page.get_text("dict")
    blocks: list[Block] = []
    for i, b in enumerate(raw["blocks"]):
        if b.get("type") != 0:
            continue  # skip image blocks
        lines = [_line_from_raw(line) for line in b["lines"]]
        lines = [line for line in lines if line.spans]
        if not lines:
            continue

        if _is_coherent_paragraph(lines):
            blocks.append(Block(id=f"b{i}", bbox=tuple(b["bbox"]), lines=lines))
        else:
            # Not a paragraph (most likely several table cells/columns that
            # MuPDF merged because they're vertically close) -- edit each
            # line independently instead of the whole merged region.
            for j, line in enumerate(lines):
                blocks.append(Block(id=f"b{i}l{j}", bbox=line.bbox, lines=[line]))
    return blocks


def _font_xref_for_name(page: pymupdf.Page, font_name: str) -> int | None:
    for f in page.get_fonts(full=True):
        xref, base_name = f[0], f[3]
        if base_name == font_name or base_name.endswith("+" + font_name):
            return xref
    return None


def _font_covers_text(font_source: str | bytes, text: str) -> bool:
    try:
        tt = TTFont(io.BytesIO(font_source) if isinstance(font_source, bytes) else font_source, lazy=True)
        cmap = tt.getBestCmap()
    except Exception:
        return False
    if not cmap:
        return False
    needed = {ord(c) for c in text if not c.isspace()}
    return needed.issubset(cmap.keys())


@dataclass
class FontChoice:
    fontname: str
    fontfile: str | None  # always a real path on disk -- PyMuPDF's insert_textbox needs one, not bytes
    substituted: bool
    _temp_path: str | None = None  # set when fontfile is a temp file we own and must clean up

    def cleanup(self) -> None:
        if self._temp_path:
            Path(self._temp_path).unlink(missing_ok=True)


def pick_font(doc: pymupdf.Document, page: pymupdf.Page, span: Span, new_text: str) -> FontChoice:
    # Every call gets its own resource tag. Two edits that happen to pick the
    # same font family (e.g. both fall back to "Arial Narrow") must NOT
    # share a PDF font resource name: PyMuPDF reuses an existing page
    # resource whenever the fontname tag already exists, silently keeping
    # whatever encoding (simple vs not -- see set_simple below) that first
    # resource was created with. We hit this for real: a Euro sign worked
    # fine as the only edit, then started rendering as "?" once a *different*
    # prior edit had already registered the same tag as a Euro-incapable
    # simple font. A short unique suffix per call makes that impossible.
    unique = uuid.uuid4().hex[:8]

    xref = _font_xref_for_name(page, span.font)
    if xref is not None:
        try:
            _name, _ext, _ftype, font_bytes = doc.extract_font(xref)
        except Exception:
            font_bytes = None
        if font_bytes and _font_covers_text(font_bytes, new_text):
            fd, tmp_path = tempfile.mkstemp(suffix=f".{_ext or 'ttf'}")
            with open(fd, "wb") as f:
                f.write(font_bytes)
            return FontChoice(fontname=f"f{unique}", fontfile=tmp_path, substituted=False, _temp_path=tmp_path)

    bold = bool(span.flags & FLAG_BOLD)
    italic = bool(span.flags & FLAG_ITALIC)

    # Prefer a real system font matching the original family by name (e.g.
    # "ArialNarrow" -> actual Arial Narrow.ttf) -- much closer than a
    # generic Base-14 alias, and it covers characters (Euro, accents, …)
    # Base-14 doesn't.
    named_family = _family_for_original(span.font)
    if named_family:
        path = _system_font_path(named_family, bold, italic)
        if path and _font_covers_text(path, new_text):
            return FontChoice(fontname=f"f{unique}", fontfile=path, substituted=True)

    generic_family = _generic_family_for_flags(span.flags)
    path = _system_font_path(generic_family, bold, italic)
    if path and _font_covers_text(path, new_text):
        return FontChoice(fontname=f"f{unique}", fontfile=path, substituted=True)

    # Last resort: no system font files available on this machine at all.
    return FontChoice(fontname=_base14_for(span.flags), fontfile=None, substituted=True)


def _measure(text: str, font_choice: FontChoice, fontsize: float) -> float:
    if font_choice.fontfile:
        return pymupdf.Font(fontfile=font_choice.fontfile).text_length(text, fontsize=fontsize)
    return pymupdf.get_text_length(text, fontname=font_choice.fontname, fontsize=fontsize)


def _metric_match_scale(span: Span, font_choice: FontChoice) -> float:
    """How much to horizontally compress/stretch a substituted font so it
    occupies roughly the same width as the original text did, instead of
    visibly "widening" (or narrowing) the line. Compares the ORIGINAL span
    text rendered in the substitute font against its actual original width
    -- independent of what the new text says.
    """
    original_width = span.bbox[2] - span.bbox[0]
    if original_width <= 0 or not span.text.strip():
        return 1.0
    substitute_width = _measure(span.text, font_choice, span.size)
    if substitute_width <= 0:
        return 1.0
    scale = original_width / substitute_width
    return min(1.4, max(0.6, scale))


def apply_block_edit(
    doc: pymupdf.Document,
    page: pymupdf.Page,
    block: Block,
    new_text: str,
) -> tuple[bool, tuple[float, float, float, float]]:
    """Redacts the block's original glyphs and reinserts new_text.

    Lines are placed explicitly (one insert_text call per line, at the
    original line spacing) instead of handing the whole string to
    insert_textbox's own word-wrapper: that wrapper needs far more vertical
    room than the tight original line height (grown boxes silently ate into
    whatever sat right below -- a real bug we hit with table rows), and it
    marks its internal wrap candidates by replacing regular spaces/hyphens
    with non-breaking-space / soft-hyphen characters even when they end up
    unused -- silently breaking search/copy-paste on the exact text a user
    just typed. Since the user's own newlines already say where lines
    break, we don't need MuPDF to decide that for us.

    Returns (font_substituted, final_bbox).
    """
    span = block.dominant_span
    color = rgb_int_to_tuple(span.color)
    font_choice = pick_font(doc, page, span, new_text)
    scale_x = _metric_match_scale(span, font_choice) if font_choice.substituted else 1.0

    x0, y0, x1, y1 = block.bbox
    block_width = max(x1 - x0, 10.0)
    lines = new_text.split("\n")

    # Anchor on the ORIGINAL first line's exact baseline (PyMuPDF gives us
    # this directly as `origin`) rather than estimating one from the bbox
    # top -- an estimate that was consistently a couple points off, enough
    # to visibly lift short table-cell text off its row. Line spacing is
    # likewise measured baseline-to-baseline between the original lines,
    # the correct typographic distance (bbox-top-to-bbox-top isn't, because
    # ascender height varies).
    first_origin = block.lines[0].spans[0].origin
    if len(block.lines) > 1:
        origins_y = [line.spans[0].origin[1] for line in block.lines if line.spans]
        diffs = [b - a for a, b in zip(origins_y, origins_y[1:]) if b > a]
        line_height = (sum(diffs) / len(diffs)) if diffs else span.size * 1.2
    else:
        line_height = max(y1 - y0, span.size * 1.2)

    try:
        fontsize = span.size
        # Shrink to fit width instead of growing the box: growing sideways
        # risks spilling into the next table column.
        for _attempt in range(6):
            widest = max((_measure(line, font_choice, fontsize) for line in lines), default=0.0)
            if widest * scale_x <= block_width * 1.05 or fontsize < span.size * 0.5:
                break
            fontsize *= 0.9

        needed_height = max(y1 - y0, line_height * len(lines))
        page.add_redact_annot(pymupdf.Rect(x0, y0, x0 + block_width, y0 + needed_height), fill=None)
        page.apply_redactions()

        morph = (pymupdf.Point(x0, y0), pymupdf.Matrix(scale_x, 1)) if scale_x != 1.0 else None
        # set_simple=1 stops MuPDF's ToUnicode generation for freshly
        # embedded fonts from mangling plain space/hyphen into NBSP/soft
        # hyphen (a real bug we hit -- purely a search/copy-paste fidelity
        # issue, the glyphs themselves render fine either way), but its
        # simple-font encoding only covers Latin-1 (code points <= 255) --
        # €, curly quotes, em-dashes, etc. need the default encoding.
        use_simple = font_choice.fontfile is not None and all(ord(c) <= 255 for c in new_text)
        # If we had to shrink the font to fit, keep the same baseline the
        # original text sat on rather than re-deriving it from the smaller
        # size, so it doesn't drift off the row's alignment either.
        baseline_y = first_origin[1]
        for line in lines:
            page.insert_text(
                (first_origin[0], baseline_y),
                line,
                fontsize=fontsize,
                fontname=font_choice.fontname,
                fontfile=font_choice.fontfile,
                color=color,
                morph=morph,
                set_simple=1 if use_simple else 0,
            )
            baseline_y += line_height

        max_width = max((_measure(line, font_choice, fontsize) for line in lines), default=0.0) * scale_x
        return font_choice.substituted, (x0, y0, x0 + max(max_width, block_width), y0 + needed_height)
    finally:
        font_choice.cleanup()

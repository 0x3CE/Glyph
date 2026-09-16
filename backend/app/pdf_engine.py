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
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from fontTools.ttLib import TTFont, TTLibError
from fontTools.varLib.instancer import instantiateVariableFont

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
# a substituted amount silently rendered as "?"). Real font files cover far
# more of Unicode, including Euro, and often let us match the ORIGINAL font
# family by name (e.g. "ArialNarrow" in the PDF -> a real Arial Narrow) --
# much closer to the original than a Base-14 alias would ever be.
#
# Two tiers, tried in order (see `_system_font_path`): the exact
# proprietary font if this happens to be running on macOS (which ships
# Arial/Times/Courier/etc. -- never true on the Linux server this also
# deploys to), then the bundled Liberation Fonts (SIL OFL, `fonts/liberation/`)
# as a family that's ALWAYS present regardless of OS. Liberation Sans/
# Serif/Mono are metrically identical, glyph-for-glyph advance width, to
# Arial/Times New Roman/Courier New respectively -- that's their whole
# purpose -- so even the fallback tier reflows text the same way the real
# font would have. There's no bundled substitute for Arial Narrow's actual
# condensed metrics, or for Georgia/Verdana/Tahoma's specific designs, so
# those degrade to the closest bundled family (still strictly better than
# jumping straight to Base-14 Helvetica/Times).
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

_BUNDLED_FONT_DIR = Path(__file__).resolve().parent / "fonts" / "liberation"

_LIBERATION_SANS = {
    (False, False): "LiberationSans-Regular.ttf",
    (True, False): "LiberationSans-Bold.ttf",
    (False, True): "LiberationSans-Italic.ttf",
    (True, True): "LiberationSans-BoldItalic.ttf",
}
_LIBERATION_SERIF = {
    (False, False): "LiberationSerif-Regular.ttf",
    (True, False): "LiberationSerif-Bold.ttf",
    (False, True): "LiberationSerif-Italic.ttf",
    (True, True): "LiberationSerif-BoldItalic.ttf",
}
_LIBERATION_MONO = {
    (False, False): "LiberationMono-Regular.ttf",
    (True, False): "LiberationMono-Bold.ttf",
    (False, True): "LiberationMono-Italic.ttf",
    (True, True): "LiberationMono-BoldItalic.ttf",
}

_BUNDLED_FAMILIES: dict[str, dict[tuple[bool, bool], str]] = {
    "arial": _LIBERATION_SANS,
    "arial narrow": _LIBERATION_SANS,  # no condensed metrics bundled, but still Unicode-complete
    "verdana": _LIBERATION_SANS,
    "tahoma": _LIBERATION_SANS,
    "times new roman": _LIBERATION_SERIF,
    "georgia": _LIBERATION_SERIF,
    "courier new": _LIBERATION_MONO,
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
    for font_dir, families in ((_SYSTEM_FONT_DIR, _SYSTEM_FAMILIES), (_BUNDLED_FONT_DIR, _BUNDLED_FAMILIES)):
        variants = families.get(family)
        if not variants:
            continue
        filename = variants.get((bold, italic)) or variants.get((False, False))
        if not filename:
            continue
        path = font_dir / filename
        if path.is_file():
            return str(path)
    return None


# A Type3 font (glyphs are arbitrary vector-drawing programs, no OS/2/name
# table at all) gives `flags` no real weight information to read -- PyMuPDF
# just reports 0, which looks identical to a genuinely non-bold font. Since
# the glyphs ARE actually drawn on the page, we can measure their real
# visual weight instead of guessing: render the original span, and render
# the same text in each of these three weights of the same open-source
# family (instanced from Google's variable-font release with
# `fontTools.varLib.instancer`, SIL OFL, `fonts/opensans/`), then pick
# whichever candidate's "ink ratio" (fraction of pixels that differ from
# the surrounding background) is closest to the original's. Real bug this
# fixes: a Type3-sourced light/thin custom typeface was silently replaced
# by a much heavier default weight (see docs/DECISIONS.md).
_OPENSANS_FONT_DIR = Path(__file__).resolve().parent / "fonts" / "opensans"
_OPENSANS_WEIGHTS: dict[str, Path] = {
    "light": _OPENSANS_FONT_DIR / "OpenSans-Light.ttf",
    "regular": _OPENSANS_FONT_DIR / "OpenSans-Regular.ttf",
    "bold": _OPENSANS_FONT_DIR / "OpenSans-Bold.ttf",
}
_OPENSANS_VARIABLE_PATH = _OPENSANS_FONT_DIR / "OpenSans-Variable.ttf"
_OPENSANS_SAMPLE_WEIGHTS: dict[str, float] = {"light": 300.0, "regular": 400.0, "bold": 700.0}

# Under active manual bisection on a real document (see docs/DECISIONS.md,
# "Après calibration, toujours trop gras"): 300 (Light) came back "too
# thin", the ink-ratio-calibrated ~450 came back "too thick". Change ONLY
# this value to try another point -- `pick_font` and the tests below both
# read it, so they never drift out of sync with each other while this is
# still being narrowed down by hand.
_TYPE3_DEFAULT_WEIGHT = 375.0


def _is_type3_font(font_name: str) -> bool:
    return font_name.startswith("Type3")


_INK_RATIO_ZOOM = 12  # see docs/DECISIONS.md -- 4x wasn't enough to tell thin strokes apart


def _ink_ratio(page: pymupdf.Page, bbox: tuple[float, float, float, float]) -> float:
    """Fraction of pixels in bbox that differ noticeably from the area's
    own dominant (background) color -- self-calibrating to whatever
    text/background color combination is actually there (white text on a
    colored fill included), rather than assuming dark text on a light
    page.

    Rendered at `_INK_RATIO_ZOOM`: real bug, measured at the previous 4x --
    a genuinely regular-weight Type3 original came out as a coin-flip
    between "regular" and "bold" (diffs 0.0316 vs 0.0312, a 1.3% margin,
    pure measurement noise), because 4x isn't enough resolution to
    faithfully capture thin strokes -- they either round up to a minimum
    rendered width or get lost, inflating or destabilizing the ratio. The
    exact same original and candidates, re-measured at 8x and above,
    consistently and decisively picked "regular" every time.
    """
    rect = pymupdf.Rect(*bbox)
    if rect.width <= 0 or rect.height <= 0:
        return 0.0
    pix = page.get_pixmap(clip=rect, matrix=pymupdf.Matrix(_INK_RATIO_ZOOM, _INK_RATIO_ZOOM))
    stride = pix.n
    samples = pix.samples
    colors = [tuple(samples[i : i + 3]) for i in range(0, len(samples), stride)]
    if not colors:
        return 0.0
    background = Counter(colors).most_common(1)[0][0]
    ink = sum(1 for c in colors if sum((a - b) ** 2 for a, b in zip(c, background)) ** 0.5 > 40)
    return ink / len(colors)


def _ink_ratio_for_candidate(fontfile: Path, text: str, size: float) -> float:
    doc = pymupdf.open()
    page = doc.new_page(width=max(size * len(text), 100.0) + 20, height=size * 3)
    baseline_y = size * 2.0
    # Same fix as `pick_font`'s `unique` tag: MuPDF's font-resource cache is
    # process-wide, not per-Document, so reusing a fixed name here across
    # calls (even across separate throwaway Documents, and even across
    # separate calls to `_closest_weight_by_ink` for the same edit) can
    # silently reuse a PREVIOUSLY loaded candidate's font data instead of
    # this one -- real bug: the Bold candidate's ink ratio got measured
    # using a stale Light font, corrupting the whole comparison.
    fontname = f"fref{uuid.uuid4().hex[:8]}"
    page.insert_text((10, baseline_y), text, fontsize=size, fontname=fontname, fontfile=str(fontfile))
    # Read PyMuPDF's own tight bbox back rather than estimating one from
    # `font.text_length()` plus fixed ascent/descent multipliers -- real
    # bug: that hand-rolled box was measurably looser than the original's
    # PyMuPDF-extracted bbox (extra blank margin dilutes the ink ratio),
    # which alone was enough to make every candidate read "lighter" than
    # the original by a roughly constant amount, silently biasing the
    # whole comparison towards heavier weights regardless of the true
    # match. Both sides of the comparison must be measured the same way.
    candidate_span = extract_structure(page)[0].dominant_span
    return _ink_ratio(page, candidate_span.bbox)


def _closest_weight_by_ink(
    page: pymupdf.Page, bbox: tuple[float, float, float, float], text: str, size: float
) -> float | None:
    """Measured over the WHOLE block, not just its dominant span: a Type3
    font can render individual glyphs with slightly inconsistent stroke
    weight (a real document had "Clair" measurably denser than "Gris"
    right next to it, same font resource, likely just an artifact of how
    each glyph's vector program was drawn) -- averaging over the full
    field smooths that out instead of possibly locking onto one
    unrepresentative word.

    Returns a `wght` axis value (300-800), not just one of the three
    sampled weights: those three are cheap to check (no on-the-fly font
    instancing needed for the three pre-baked files) and anchor the
    interpolation below, but the real original rarely sits exactly on one
    of them -- a real original measured consistently ~15-25% of the way
    from regular towards bold (once measured at high enough resolution,
    see `_ink_ratio`), and snapping to whichever of the three is merely
    closest would have used plain regular there, still visibly lighter
    than intended. There's no separate "is this decisively non-regular"
    gate anymore: interpolation is continuous, so a small, noisy deviation
    near a sample point already lands close to that sample's own weight
    without needing a special case -- the discrete bucket+margin logic
    this replaced was compensating for 4x-resolution noise, not for a
    property of the interpolation itself.
    """
    sample_text = text.strip() or "Aa"
    original_ratio = _ink_ratio(page, bbox)
    ratios: dict[str, float] = {}
    for name, path in _OPENSANS_WEIGHTS.items():
        if not path.is_file():
            continue
        ratios[name] = _ink_ratio_for_candidate(path, sample_text, size)
    if not ratios:
        return None
    return _interpolate_weight(original_ratio, ratios)


def _find_calibration_text(
    page: pymupdf.Page, font_name: str, exclude_bboxes: set[tuple[float, float, float, float]]
) -> tuple[str, tuple[float, float, float, float]] | None:
    """The longest other run of text on the page sharing the exact same
    Type3 font resource as the block being edited -- used to calibrate the
    ink-ratio comparison instead of measuring the (possibly short, possibly
    per-glyph-noisy) edited text alone.

    Real bug this fixes, found by comparing two runs that share the
    literal same font resource on the same real document: "Vélo route
    Cyclotourisme RC120 Disque" (38 chars) and "Gris Clair" (10 chars)
    measured within 0.6% of each other's ink ratio -- both clearly the
    document's normal body weight -- yet comparing either one directly
    against the bundled OpenSans candidates landed 5-12% closer to Bold
    than to Regular. Type3 rendering reads measurably "heavier" than an
    equivalently-designed TrueType font at the same nominal weight -- a
    rendering-technology gap, not a font-weight fact. Calibrating against
    a longer same-resource, same-technology sample first (here: the 38-char
    product name, not the 10-char field being edited) is both more
    statistically stable (less exposed to one word's per-glyph quirks) and
    entirely sidesteps that cross-technology bias, without needing to
    quantify or hard-code it.
    """
    best_text = ""
    best_bbox: tuple[float, float, float, float] | None = None
    for line in page.get_text("dict")["blocks"]:
        if line.get("type") != 0:
            continue
        for raw_line in line["lines"]:
            for s in raw_line["spans"]:
                if s["font"] != font_name:
                    continue
                bbox = tuple(s["bbox"])
                if bbox in exclude_bboxes:
                    continue
                if len(s["text"]) > len(best_text):
                    best_text, best_bbox = s["text"], bbox
    if best_bbox is None:
        return None
    return best_text, best_bbox


def _interpolate_weight(original_ratio: float, ratios: dict[str, float]) -> float:
    """Piecewise-linear interpolation across the sampled (weight, ink_ratio)
    points -- e.g. if the original's ink ratio sits 40% of the way from the
    regular sample to the bold sample, estimate the weight 40% of the way
    from 400 to 700, rather than snapping to one or the other.
    """
    points = sorted((_OPENSANS_SAMPLE_WEIGHTS[name], ratio) for name, ratio in ratios.items())
    if original_ratio <= points[0][1]:
        return points[0][0]
    if original_ratio >= points[-1][1]:
        return points[-1][0]
    for (w0, r0), (w1, r1) in zip(points, points[1:]):
        if r0 <= original_ratio <= r1:
            t = (original_ratio - r0) / (r1 - r0) if r1 != r0 else 0.0
            return w0 + t * (w1 - w0)
    return points[-1][0]


def _instantiate_weight(wght: float) -> bytes:
    """A one-off static instance of the bundled variable font at an
    arbitrary weight -- the refinement step after `_interpolate_weight`
    has estimated roughly where on the axis the original sits. Skips
    `updateFontNames` (it only knows the font's few pre-named instances,
    not arbitrary weights) since this file is used once and discarded, not
    inspected by name; re-applies the same sans-serif PANOSE/family-class
    fix as the pre-baked static weights, which the variable source lacks
    (see docs/DECISIONS.md) and instancing doesn't add on its own.
    """
    font = TTFont(str(_OPENSANS_VARIABLE_PATH))
    instantiateVariableFont(font, {"wght": max(300.0, min(800.0, wght)), "wdth": 100}, inplace=True, updateFontNames=False)
    os2 = font["OS/2"]
    os2.sFamilyClass = 2053
    os2.panose.bFamilyType = 2
    os2.panose.bSerifStyle = 11
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()




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


def pick_font(doc: pymupdf.Document, page: pymupdf.Page, block: Block, new_text: str) -> FontChoice:
    span = block.dominant_span
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

    # `flags` is meaningless for a Type3 source (see `_closest_weight_by_ink`).
    # The ink-ratio measurement + cross-technology calibration below it
    # (`_closest_weight_by_ink`, `_find_calibration_text`, kept in this file
    # for the diagnostic value even though it's not called here right now)
    # is real, tested, and internally consistent -- verified against a real
    # document down to "two runs sharing the literal same font resource
    # measure within 0.6% of each other" -- and yet the resulting weight
    # (e.g. 450, barely above Regular) still rendered visibly too heavy in
    # three independent viewers (pdf.js, this project's own PyMuPDF-based
    # checks, and macOS Preview/Quartz) compared to the real document. No
    # stray bold flag, no metadata inconsistency, no interpolation bug was
    # found to explain the gap after extensive investigation (see
    # docs/DECISIONS.md) -- still unclear whether it's a per-viewer
    # hinting/rendering difference at these specific weights or something
    # about this variable font's own design space. Bracketed empirically on
    # the same real document: flat Light (300) reported "too thin", the
    # calibrated ~450 reported "too thick" -- bisecting that range rather
    # than jumping straight to a named sample (300/400/700).
    if _is_type3_font(span.font) and generic_family == "arial":
        font_bytes = _instantiate_weight(_TYPE3_DEFAULT_WEIGHT)
        if _font_covers_text(font_bytes, new_text):
            fd, tmp_path = tempfile.mkstemp(suffix=".ttf")
            with open(fd, "wb") as f:
                f.write(font_bytes)
            return FontChoice(fontname=f"f{unique}", fontfile=tmp_path, substituted=True, _temp_path=tmp_path)

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


def _sibling_bound(block: Block, all_blocks: list[Block], edge: str) -> float | None:
    """The nearest boundary imposed by a sibling block that overlaps this
    one along the perpendicular axis -- how far this block's redaction (or
    downward growth) may extend on the given `edge` ("top"/"bottom"/
    "left"/"right") before it would start eating a neighbor's content.

    Needed because two adjacent blocks' own tight bboxes can already
    overlap by a couple points in real documents -- tight line leading
    vertically, tightly-packed table columns horizontally -- even though
    the actual rendered ink doesn't visually overlap. Since redaction
    removes an entire intersecting glyph run, not just the overlapping
    pixels, even that small an overlap is enough to erase a neighbor
    entirely. Two real bugs came from the vertical case alone: editing a
    title line erased the line below it, and (mirrored) editing a subtitle
    line erased the title stacked above it. The horizontal case is the
    same risk applied to a row of side-by-side table cells.

    A candidate only counts as "the next one over" on `edge` if it starts
    within a small tolerance of this block's own opposite edge -- not
    merely "somewhere further along that axis". Without that distinction,
    a short line stacked with tight leading between two others (real case:
    a lone "2" between a long reference number and a date, in a 3-row
    value column) perpendicularly overlaps EVERY line near it and would
    wrongly count as a horizontal neighbor of the date line below it, even
    though almost its entire width sits nested inside the date's own span,
    not beside it. The tolerance scales with the smaller of the two
    blocks' own extent on this axis, since the overlaps this guards
    against (tight leading/kerning) are a small fraction of a line's own
    size, not a large one.
    """
    x0, y0, x1, y1 = block.bbox

    def not_too_nested(this_extent: float, other_extent: float, gap: float) -> bool:
        # gap is the signed distance from this block's edge to the
        # candidate's near edge: positive means a real separating space
        # (always fine, however large -- e.g. genuine whitespace before
        # the next paragraph), negative means overlap. Only reject when
        # the OVERLAP is more than half of the smaller block's own extent
        # on this axis -- i.e. when the "neighbor" is mostly nested inside
        # this block's own span rather than merely touching its edge.
        tolerance = 0.5 * min(this_extent, other_extent)
        return gap >= -tolerance

    if edge == "bottom":
        height = max(y1 - y0, 1.0)
        candidates = [
            o.bbox[1]
            for o in all_blocks
            if o is not block
            and o.bbox[1] > y0
            and min(x1, o.bbox[2]) - max(x0, o.bbox[0]) > 0
            and not_too_nested(height, max(o.bbox[3] - o.bbox[1], 1.0), o.bbox[1] - y1)
        ]
        return min(candidates) if candidates else None
    if edge == "top":
        height = max(y1 - y0, 1.0)
        candidates = [
            o.bbox[3]
            for o in all_blocks
            if o is not block
            and o.bbox[3] < y1
            and min(x1, o.bbox[2]) - max(x0, o.bbox[0]) > 0
            and not_too_nested(height, max(o.bbox[3] - o.bbox[1], 1.0), y0 - o.bbox[3])
        ]
        return max(candidates) if candidates else None
    if edge == "right":
        width = max(x1 - x0, 1.0)
        candidates = [
            o.bbox[0]
            for o in all_blocks
            if o is not block
            and o.bbox[0] > x0
            and min(y1, o.bbox[3]) - max(y0, o.bbox[1]) > 0
            and not_too_nested(width, max(o.bbox[2] - o.bbox[0], 1.0), o.bbox[0] - x1)
        ]
        return min(candidates) if candidates else None
    if edge == "left":
        width = max(x1 - x0, 1.0)
        candidates = [
            o.bbox[2]
            for o in all_blocks
            if o is not block
            and o.bbox[2] < x1
            and min(y1, o.bbox[3]) - max(y0, o.bbox[1]) > 0
            and not_too_nested(width, max(o.bbox[2] - o.bbox[0], 1.0), x0 - o.bbox[2])
        ]
        return max(candidates) if candidates else None
    raise ValueError(edge)


def apply_block_edit(
    doc: pymupdf.Document,
    page: pymupdf.Page,
    block: Block,
    new_text: str,
    all_blocks: list[Block] | None = None,
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
    font_choice = pick_font(doc, page, block, new_text)
    scale_x = _metric_match_scale(span, font_choice) if font_choice.substituted else 1.0

    x0, y0, x1, y1 = block.bbox
    block_width = max(x1 - x0, 10.0)
    lines = new_text.split("\n")

    # Anchor on the ORIGINAL line's exact baseline (PyMuPDF gives us this
    # directly as `origin`) rather than estimating one from the bbox top --
    # an estimate that was consistently a couple points off, enough to
    # visibly lift short table-cell text off its row. A block is always
    # exactly one original PyMuPDF line (see extract_structure): the
    # per-line spacing below is only for the case where the user's OWN new
    # text has more lines than that -- e.g. typing a manual line break into
    # a field that was originally one line -- and is otherwise a
    # deliberately rough estimate since there's no original spacing to
    # measure it from.
    first_origin = block.lines[0].spans[0].origin
    line_height = max(y1 - y0, span.size * 1.2)

    try:
        # Neighbor bounds on all four sides -- computed once, up front, so
        # both the shrink-to-fit width and the redaction rectangle respect
        # the same safe area. Without a sibling on a given side, the bound
        # is None and that side is left at the block's own natural edge.
        next_top = _sibling_bound(block, all_blocks, "bottom") if all_blocks else None
        prev_bottom = _sibling_bound(block, all_blocks, "top") if all_blocks else None
        next_left = _sibling_bound(block, all_blocks, "right") if all_blocks else None
        prev_right = _sibling_bound(block, all_blocks, "left") if all_blocks else None

        redact_left = x0
        if prev_right is not None and prev_right > redact_left:
            redact_left = min(prev_right + 0.25, x0 + block_width - 1.0)

        # The block's own original width is not a hard ceiling for the new
        # text -- unlike height (where growing a paragraph into the one
        # below would look like unwanted reflow), a single-line field
        # extending a bit further sideways is harmless as long as it
        # doesn't reach a REAL neighboring column. Only `next_left` (an
        # actual sibling block) is a hard limit; without one, allow
        # generous room instead of shrinking the font just because a
        # substitute font (metrically wider than the original) or a longer
        # replacement word needs a bit more space than the original text
        # did. Real case: "Clair" -> "foncée" in a bundled sans-serif font
        # needed 58pt where the Type3 original only used 46.6pt, with nothing
        # to the right for ~250pt -- shrunk the font by 19% for no reason.
        max_reasonable_width = block_width * 3.0
        if next_left is not None:
            redact_right = min(x0 + max_reasonable_width, max(next_left - 0.25, redact_left + 1.0))
        else:
            redact_right = x0 + max_reasonable_width
        safe_width = max(redact_right - redact_left, 1.0)

        fontsize = span.size
        # Shrinking only kicks in once even the generous safe_width above
        # isn't enough -- growing sideways is preferred first, and this is
        # the last resort for when there's truly no room (a real neighbor
        # close by, or an unusually long replacement).
        for _attempt in range(6):
            widest = max((_measure(line, font_choice, fontsize) for line in lines), default=0.0)
            if widest * scale_x <= safe_width * 1.05 or fontsize < span.size * 0.5:
                break
            fontsize *= 0.9

        needed_height = max(y1 - y0, line_height * len(lines))
        if next_top is not None:
            needed_height = min(needed_height, max(next_top - y0 - 0.25, 1.0))

        redact_top = y0
        if prev_bottom is not None and prev_bottom > redact_top:
            redact_top = min(prev_bottom + 0.25, y0 + needed_height - 1.0)

        page.add_redact_annot(pymupdf.Rect(redact_left, redact_top, redact_right, y0 + needed_height), fill=None)
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

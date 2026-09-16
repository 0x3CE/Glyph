"""Font selection: choosing what to render new/edited text in.

Three tiers, tried in order by `pick_font`: reuse the original embedded
font if we can verify (via fontTools) it covers every character of the
new text; otherwise match the original font's family by name against a
real font file (system Arial/Times/etc. on macOS, or the bundled
Liberation Fonts everywhere); otherwise fall back to a generic family by
flags, and if all else fails, a PyMuPDF Base-14 font.
"""

from __future__ import annotations

import io
import re
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from fontTools.ttLib import TTFont

from .type3_weight import _TYPE3_DEFAULT_WEIGHT, _instantiate_weight, _is_type3_font
from .types import FLAG_BOLD, FLAG_ITALIC, FLAG_MONOSPACE, FLAG_SERIF, Block, Span

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

_BUNDLED_FONT_DIR = Path(__file__).resolve().parent.parent / "fonts" / "liberation"

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


def _extract_span_font(doc: pymupdf.Document, page: pymupdf.Page, span: Span) -> FontChoice | None:
    """Extract the actual embedded font bytes backing `span`, if PyMuPDF can
    locate and read them -- `None` if the resource can't be found or read.
    Used both by `pick_font`'s "reuse the whole original font" fast path
    and by per-run formatting preservation in `apply_block_edit` (see
    `_build_formatted_segments`): there, the text being reused is always a
    verbatim substring of what this exact font already rendered, so unlike
    `pick_font`'s use, no `_font_covers_text` check is needed on that path.
    """
    xref = _font_xref_for_name(page, span.font)
    if xref is None:
        return None
    try:
        _name, _ext, _ftype, font_bytes = doc.extract_font(xref)
    except Exception:
        return None
    if not font_bytes:
        return None
    fd, tmp_path = tempfile.mkstemp(suffix=f".{_ext or 'ttf'}")
    with open(fd, "wb") as f:
        f.write(font_bytes)
    return FontChoice(fontname=f"f{uuid.uuid4().hex[:8]}", fontfile=tmp_path, substituted=False, _temp_path=tmp_path)


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

    reused = _extract_span_font(doc, page, span)
    if reused is not None:
        if _font_covers_text(reused.fontfile, new_text):
            return reused
        reused.cleanup()

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

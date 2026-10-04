"""Font selection: choosing what to render new/edited text in.

Tiers, tried in order by `pick_font`: reuse the original embedded font
if we can verify (via fontTools) it covers every character of the new
text; otherwise match the original font's family by name against a real
font file (system Arial/Times/etc. on macOS, or the bundled catalog of
free fonts everywhere, see `font_catalog`); otherwise a generic family by
category; then a wide-coverage family (DejaVu) for scripts the closer
matches lack; and if all else fails, a PyMuPDF Base-14 font.
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

from .font_catalog import BY_KEY, COVERAGE_FALLBACK, Style, match_family
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
# Two sources, tried in order for a given family (see `_family_font`): the
# exact proprietary file if this happens to be running on macOS (which
# ships Arial/Times/Courier/etc. -- never true on the Linux server this
# also deploys to), then the bundled catalog (`font_catalog.CATALOG`,
# `app/fonts/`), present regardless of OS: the real typeface for free
# families (Roboto, Montserrat, ...) and metric-compatible clones for
# proprietary ones (Liberation Sans for Arial, Carlito for Calibri, Nimbus
# Sans Narrow for Arial Narrow, ...), so even the fallback reflows text
# the same way the real font would have.
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

_BUNDLED_FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"


def _normalize_font_name(name: str) -> str:
    # Strip a subset tag ("EAAAAB+ArialNarrow" -> "ArialNarrow"), any
    # style suffix words, and non-alphanumerics, then lowercase.
    name = name.split("+")[-1]
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _family_for_original(font_name: str) -> str | None:
    return match_family(_normalize_font_name(font_name))


def _category_for(family: str | None, flags: int) -> str:
    # The catalog knows a named family's category even when the PDF's
    # descriptor flags don't say "serif" (common: many producers never set it).
    if family in BY_KEY:
        return BY_KEY[family].category
    if flags & FLAG_MONOSPACE:
        return "mono"
    if flags & FLAG_SERIF:
        return "serif"
    return "sans"


_GENERIC_FAMILY = {"sans": "arial", "serif": "times new roman", "mono": "courier new", "display": "arial"}


def _style_candidates(bold: bool, italic: bool) -> list[Style]:
    # Closest style first: a family without italics still keeps the bold.
    return list(dict.fromkeys([(bold, italic), (bold, False), (False, italic), (False, False)]))


def _family_font(family: str, bold: bool, italic: bool, *, system: bool = True) -> tuple[str, bool] | None:
    """(path, same_typeface) of the best file for `family`, or None.

    The real proprietary file wins when this happens to run on macOS
    (always the same typeface, by definition); otherwise the bundled
    catalog entry. A bundled style missing on disk (family without
    italics, or a `scripts/fetch_fonts.py` run that never happened) degrades
    to the closest style that is there.
    """
    system_files = _SYSTEM_FAMILIES.get(family) if system else None
    if system_files:
        for style in _style_candidates(bold, italic):
            filename = system_files.get(style)
            if filename and (_SYSTEM_FONT_DIR / filename).is_file():
                return str(_SYSTEM_FONT_DIR / filename), True
    bundled = BY_KEY.get(family)
    if bundled:
        for style in _style_candidates(bold, italic):
            filename = bundled.files.get(style)
            if filename and (_BUNDLED_FONT_DIR / bundled.directory / filename).is_file():
                return str(_BUNDLED_FONT_DIR / bundled.directory / filename), bundled.same_typeface
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
    # A bundled/system copy of the very typeface the PDF used (e.g. the real
    # Montserrat): still `substituted` for metric compensation purposes,
    # but nothing worth warning the user about.
    same_typeface: bool = False
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

    def from_family(family: str, *, system: bool = True, named: bool = False) -> FontChoice | None:
        found = _family_font(family, bold, italic, system=system)
        if found and _font_covers_text(found[0], new_text):
            # Only a family matched by the original's own name can be "the
            # same typeface"; a generic pick (Courier New for an unnamed
            # fixed-width font) is a substitution even when it's a real
            # system file.
            same = found[1] and named
            return FontChoice(fontname=f"f{unique}", fontfile=found[0], substituted=True, same_typeface=same)
        return None

    # Prefer the original family matched by name (see `font_catalog`):
    # the real typeface when it's bundled (Roboto -> Roboto), or its
    # metric-compatible free clone (Calibri -> Carlito). Real font files
    # also cover characters (Euro, accents, ...) Base-14 doesn't.
    named_family = _family_for_original(span.font)
    if named_family and (choice := from_family(named_family, named=True)):
        return choice

    category = _category_for(named_family, span.flags)
    generic_family = _GENERIC_FAMILY[category]

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

    if choice := from_family(generic_family):
        return choice

    # Text the closer families can't render (Greek, Cyrillic, symbols...):
    # DejaVu covers far more of Unicode than any of them. Bundled files
    # only: the "verdana" key would otherwise resolve to macOS's real
    # Verdana, which lacks those very characters (real bug: one "✓" sent
    # the whole line to Base-14, losing its "€" too).
    if choice := from_family(COVERAGE_FALLBACK.get(category, COVERAGE_FALLBACK["sans"]), system=False):
        return choice

    # Last resort: no font file covers this text at all.
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
    text = span.text
    if any((ord(c) < 32 and c not in "\t\n") or c == "\ufffd" for c in text):
        # Unreadable text layer (Block.text_reliable): the characters are
        # wrong but there is still one per drawn glyph, so a stand-in of the
        # same length measures the same width -- exactly for a fixed-width
        # font, roughly otherwise. Measuring the garbage itself (control
        # characters with no width) stretched a retyped payslip line by ~40 %.
        text = "n" * len(text)
    substitute_width = _measure(text, font_choice, span.size)
    if substitute_width <= 0:
        return 1.0
    scale = original_width / substitute_width
    return min(1.4, max(0.6, scale))

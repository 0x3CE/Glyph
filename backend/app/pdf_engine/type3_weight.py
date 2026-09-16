"""Type3-font weight estimation.

A Type3 font (glyphs are arbitrary vector-drawing programs, no OS/2/name
table at all) gives `flags` no real weight information to read -- PyMuPDF
just reports 0, which looks identical to a genuinely non-bold font. Since
the glyphs ARE actually drawn on the page, we can measure their real
visual weight instead of guessing: render the original span, and render
the same text in each of these three weights of the same open-source
family (instanced from Google's variable-font release with
`fontTools.varLib.instancer`, SIL OFL, `fonts/opensans/`), then pick
whichever candidate's "ink ratio" (fraction of pixels that differ from
the surrounding background) is closest to the original's. Real bug this
fixes: a Type3-sourced light/thin custom typeface was silently replaced
by a much heavier default weight (see docs/DECISIONS.md).
"""

from __future__ import annotations

import io
import uuid
from collections import Counter
from pathlib import Path

import pymupdf
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from .structure import extract_structure

_OPENSANS_FONT_DIR = Path(__file__).resolve().parent.parent / "fonts" / "opensans"
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

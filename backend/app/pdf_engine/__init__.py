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

This is a package, not a single module, split by concern for easier
pickup/debugging (see docs/DECISIONS.md):
- `types`: the Span/Line/Block structural model and small shared types.
- `structure`: turning a PyMuPDF page into that model.
- `fonts`: font selection (`pick_font`) and metric matching.
- `type3_weight`: ink-ratio-based weight estimation for Type3 sources.
- `geometry`: sibling-aware bounds for redaction/growth.
- `formatting_diff`: diff-based per-run formatting preservation.
- `editor`: `apply_block_edit`, the orchestrator tying the above together.
- `workers`: the isolated-subprocess entry points `main.py` calls.

Everything below is re-exported here, including private names, so existing
call sites (`app.main`, `tests/test_pdf_engine.py`) that reach into
`pdf_engine.<name>` keep working unchanged after the split.
"""

from __future__ import annotations

from .fonts import (
    _BASE14,
    _BUNDLED_FAMILIES,
    _BUNDLED_FONT_DIR,
    _FAMILY_ALIASES,
    _LIBERATION_MONO,
    _LIBERATION_SANS,
    _LIBERATION_SERIF,
    _SYSTEM_FAMILIES,
    _SYSTEM_FONT_DIR,
    FontChoice,
    _base14_for,
    _extract_span_font,
    _family_for_original,
    _font_covers_text,
    _font_xref_for_name,
    _generic_family_for_flags,
    _measure,
    _metric_match_scale,
    _normalize_font_name,
    _system_font_path,
    pick_font,
)
from .formatting_diff import _build_formatted_segments, _char_span_map, _span_for_change
from .geometry import _sibling_bound
from .structure import extract_structure
from .type3_weight import (
    _INK_RATIO_ZOOM,
    _OPENSANS_FONT_DIR,
    _OPENSANS_SAMPLE_WEIGHTS,
    _OPENSANS_VARIABLE_PATH,
    _OPENSANS_WEIGHTS,
    _TYPE3_DEFAULT_WEIGHT,
    _closest_weight_by_ink,
    _find_calibration_text,
    _ink_ratio,
    _ink_ratio_for_candidate,
    _instantiate_weight,
    _interpolate_weight,
    _is_type3_font,
)
from .types import (
    FLAG_BOLD,
    FLAG_ITALIC,
    FLAG_MONOSPACE,
    FLAG_SERIF,
    Block,
    EncryptedPdfError,
    Line,
    Span,
    StructureResult,
    _line_from_raw,
    rgb_int_to_tuple,
)
from .editor import apply_block_edit
from .workers import worker_apply_edit, worker_extract_structure, worker_validate_pdf

__all__ = [
    "FLAG_BOLD",
    "FLAG_ITALIC",
    "FLAG_MONOSPACE",
    "FLAG_SERIF",
    "Block",
    "EncryptedPdfError",
    "FontChoice",
    "Line",
    "Span",
    "StructureResult",
    "apply_block_edit",
    "extract_structure",
    "pick_font",
    "rgb_int_to_tuple",
    "worker_apply_edit",
    "worker_extract_structure",
    "worker_validate_pdf",
]

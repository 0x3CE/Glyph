"""Applying an edit to a single block: redact the original glyphs, reinsert
the new text, and choose fonts/positions/scaling accordingly.
"""

from __future__ import annotations

import pymupdf

from .fonts import FontChoice, _extract_span_font, _font_covers_text, _measure, _metric_match_scale, pick_font
from .formatting_diff import _build_formatted_segments
from .geometry import _sibling_bound
from .types import Block, rgb_int_to_tuple


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
    fallback_color = rgb_int_to_tuple(span.color)
    fallback_font = pick_font(doc, page, block, new_text)
    fallback_scale = _metric_match_scale(span, fallback_font) if fallback_font.substituted else 1.0

    x0, y0, x1, y1 = block.bbox
    block_width = max(x1 - x0, 10.0)

    # Diff against the original to find which runs of the new text the user
    # left untouched -- those keep their own original span's exact font and
    # color instead of collapsing to the block's one fallback font (see
    # `_build_formatted_segments`; real bug: a bold acronym embedded in an
    # otherwise plain sentence lost its bold on every edit, even ones that
    # never touched it).
    cleanup_choices = [fallback_font]
    resolved: list[tuple[str, FontChoice, tuple[float, float, float], float]] = []
    # An unreadable text layer (see Block.text_reliable) can't be diffed
    # against: the user retyped the whole line, so it is all new text.
    segments = _build_formatted_segments(block, new_text) if block.text_reliable else [(new_text, None, False)]
    for text, source_span, verified in segments:
        if source_span is not None:
            reused = _extract_span_font(doc, page, source_span)
            if reused is not None:
                # An INFERRED span (a replace/insert `_span_for_change`
                # attributed by position, e.g. "TEMF" -> "GDPR" landing on
                # "TEMF"'s own bold span) has never actually rendered this
                # text -- unlike a VERIFIED "equal" run, which is by
                # construction a substring of what this span already
                # rendered successfully, so re-checking would be redundant.
                if verified or _font_covers_text(reused.fontfile, text):
                    cleanup_choices.append(reused)
                    resolved.append((text, reused, rgb_int_to_tuple(source_span.color), 1.0))
                    continue
                reused.cleanup()
        resolved.append((text, fallback_font, fallback_color, fallback_scale))

    # Split into per-rendering-line segment lists at the user's own "\n" --
    # `_build_formatted_segments` operates on the flat text, unaware of line
    # breaks.
    lines_segments: list[list[tuple[str, FontChoice, tuple[float, float, float], float]]] = [[]]
    for text, fc, color, scale in resolved:
        parts = text.split("\n")
        for k, part in enumerate(parts):
            if k > 0:
                lines_segments.append([])
            if part:
                lines_segments[-1].append((part, fc, color, scale))

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

    def _line_width(line_segs: list[tuple[str, FontChoice, tuple[float, float, float], float]], fontsize: float) -> float:
        return sum(_measure(t, fc, fontsize) * scale for t, fc, _c, scale in line_segs)

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
            widest = max((_line_width(seg, fontsize) for seg in lines_segments), default=0.0)
            if widest <= safe_width * 1.05 or fontsize < span.size * 0.5:
                break
            fontsize *= 0.9

        needed_height = max(y1 - y0, line_height * len(lines_segments))
        if next_top is not None:
            needed_height = min(needed_height, max(next_top - y0 - 0.25, 1.0))

        redact_top = y0
        if prev_bottom is not None and prev_bottom > redact_top:
            redact_top = min(prev_bottom + 0.25, y0 + needed_height - 1.0)

        page.add_redact_annot(pymupdf.Rect(redact_left, redact_top, redact_right, y0 + needed_height), fill=None)
        page.apply_redactions()

        # If we had to shrink the font to fit, keep the same baseline the
        # original text sat on rather than re-deriving it from the smaller
        # size, so it doesn't drift off the row's alignment either. Each
        # run is placed right after the previous one on the same line
        # (baseline_x advances by its own measured*scaled width), and gets
        # its own `morph` fixpoint at its own start -- a run using a
        # reused original font never needs compensation (scale 1.0, no
        # morph), only fallback-font runs do (see `_metric_match_scale`).
        # set_simple=1 stops MuPDF's ToUnicode generation for freshly
        # embedded fonts from mangling plain space/hyphen into NBSP/soft
        # hyphen (a real bug we hit -- purely a search/copy-paste fidelity
        # issue, the glyphs themselves render fine either way), but its
        # simple-font encoding only covers Latin-1 (code points <= 255) --
        # €, curly quotes, em-dashes, etc. need the default encoding. Decided
        # ONCE for the whole fallback run, not per segment: multiple segments
        # can share `fallback_font`'s single PDF resource name, and MuPDF
        # locks in whichever encoding the FIRST insert_text call under that
        # name used -- computing this per segment let an all-Latin-1 segment
        # (e.g. "Montant : ") register the shared name as simple, silently
        # corrupting a later €/— segment that reused the same name (the
        # exact resource-sharing bug already hit once before, see
        # docs/DECISIONS.md, now possible again with multiple runs per
        # edit). A reused original span's font is never shared this way --
        # `_extract_span_font` mints a fresh unique name every call.
        fallback_use_simple = fallback_font.fontfile is not None and all(ord(c) <= 255 for c in new_text)

        baseline_y = first_origin[1]
        max_line_width = 0.0
        for line_segs in lines_segments:
            baseline_x = first_origin[0]
            for text, fc, color, scale in line_segs:
                morph = (pymupdf.Point(baseline_x, y0), pymupdf.Matrix(scale, 1)) if scale != 1.0 else None
                if fc is fallback_font:
                    use_simple = fallback_use_simple
                else:
                    use_simple = fc.fontfile is not None and all(ord(c) <= 255 for c in text)
                page.insert_text(
                    (baseline_x, baseline_y),
                    text,
                    fontsize=fontsize,
                    fontname=fc.fontname,
                    fontfile=fc.fontfile,
                    color=color,
                    morph=morph,
                    set_simple=1 if use_simple else 0,
                )
                baseline_x += _measure(text, fc, fontsize) * scale
            max_line_width = max(max_line_width, baseline_x - first_origin[0])
            baseline_y += line_height

        # "Substituted" (drives the frontend's font-substitution notice)
        # means: some run actually used the fallback font, and that
        # fallback itself required substitution -- not just that a
        # fallback was computed but never needed (e.g. every run resolved
        # to a reused original span).
        # A bundled copy of the original typeface itself (`same_typeface`)
        # isn't a substitution the user needs to hear about.
        substituted = (
            fallback_font.substituted
            and not fallback_font.same_typeface
            and any(fc is fallback_font for _t, fc, _c, _s in resolved)
        )
        return substituted, (x0, y0, x0 + max(max_line_width, block_width), y0 + needed_height)
    finally:
        for fc in cleanup_choices:
            fc.cleanup()

"""Diff-based formatting preservation: figuring out which original Span's
font/color a run of the user's edited text should keep, by diffing the new
text against the old.
"""

from __future__ import annotations

import difflib

from .types import Block, Span


def _char_span_map(block: Block) -> list[Span | None]:
    """Maps each character index of `block.text` back to the Span that
    produced it (`None` for the "\\n" separators `Block.text` joins lines
    with) -- the ground truth `_build_formatted_segments` diffs against to
    know which original formatting, if any, survives unchanged into the
    user's edited text.
    """
    mapping: list[Span | None] = []
    for i, line in enumerate(block.lines):
        if i > 0:
            mapping.append(None)
        for span in line.spans:
            mapping.extend([span] * len(span.text))
    return mapping


def _span_for_change(char_map: list[Span | None], i1: int, i2: int) -> Span | None:
    """For a diff opcode's OLD range [i1, i2) -- i1 == i2 for a pure
    insertion, positioned exactly there -- returns the single original
    Span whose formatting the REPLACEMENT text should probably keep.

    Real case this covers: replacing "TEMF" with "GDPR" inside "...ou «
    TEMF »..." (only "TEMF" in Calibri-Bold) is a `replace` opcode, not an
    `equal` one -- the old bold word's exact characters are gone, so
    nothing here is "unchanged". But the change is entirely CONTAINED
    within that one bold span's own characters (doesn't spill into the
    surrounding plain text), which is a strong signal the user is
    replacing the content of that specific styled slot, not writing new
    unstyled text -- unlike an unrelated `_build_formatted_segments`
    `None` fallback, deliberately not extended to genuinely ambiguous
    cases: a change spanning multiple original spans, or an insertion
    sitting exactly on a style boundary, returns `None` (fall back to the
    block's overall font) rather than guess which side it belongs to.
    """
    if i1 == i2:
        before = char_map[i1 - 1] if i1 > 0 else None
        after = char_map[i1] if i1 < len(char_map) else None
        return before if before is not None and before is after else None
    candidate = char_map[i1]
    if candidate is None:
        return None
    for k in range(i1 + 1, i2):
        if char_map[k] is not candidate:
            return None
    return candidate


def _build_formatted_segments(block: Block, new_text: str) -> list[tuple[str, Span | None, bool]]:
    """Splits `new_text` into runs, each tagged with the original Span
    whose formatting it should keep -- `None` for a run that falls back to
    the block's one overall font -- and whether that span is VERIFIED to
    already cover this exact text (an unchanged "equal" run: it's a
    substring of what this span already rendered, so it certainly can) or
    merely INFERRED (a `replace`/insertion `_span_for_change` attributed to
    one span by position, but whose new characters that span has never
    actually rendered -- `apply_block_edit` still needs to check
    `_font_covers_text` before trusting it, the same way `pick_font` does
    for a whole block).

    Real bugs this fixes: a line mixing plain and bold text (only "TEMF"
    in Calibri-Bold within an otherwise plain sentence) collapsed entirely
    to the font of whichever original span had the most characters --
    here, the surrounding plain text -- silently dropping the bold on
    every edit, even one that never touched "TEMF" itself (fixed by the
    VERIFIED/equal case); and replacing "TEMF" itself with a different
    acronym still lost the bold, since the new word is never "unchanged"
    (fixed by the INFERRED/`_span_for_change` case).
    """
    old_text = block.text
    char_map = _char_span_map(block)
    matcher = difflib.SequenceMatcher(None, old_text, new_text, autojunk=False)
    segments: list[tuple[str, Span | None, bool]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            if j2 > j1:
                segments.append((new_text[j1:j2], _span_for_change(char_map, i1, i2), False))
            continue
        # An "equal" run can itself straddle an original span boundary
        # (e.g. unchanged text flows from plain into bold and back) --
        # walk it and re-split at each boundary. i and j advance in
        # lockstep here (equal-length, same characters), so a fixed
        # `offset` maps every i-position back to its j-position.
        offset = j1 - i1
        start = i1
        while start < i2:
            source_span = char_map[start]
            end = start + 1
            while end < i2 and char_map[end] is source_span:
                end += 1
            chunk = new_text[start + offset : end + offset]
            if chunk:
                segments.append((chunk, source_span, True))
            start = end
    # Merge adjacent runs sharing the same span and verification status so
    # the render loop in `apply_block_edit` makes as few insert_text calls
    # as necessary -- a tidiness pass, not a correctness requirement.
    merged: list[tuple[str, Span | None, bool]] = []
    for text, source_span, verified in segments:
        if merged and merged[-1][1] is source_span and merged[-1][2] == verified:
            merged[-1] = (merged[-1][0] + text, source_span, verified)
        else:
            merged.append((text, source_span, verified))
    return merged

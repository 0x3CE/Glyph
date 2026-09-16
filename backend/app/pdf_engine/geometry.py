"""Sibling-aware bounds: how far a block's redaction/growth may extend
before it starts eating a neighboring block's content.
"""

from __future__ import annotations

from .types import Block


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

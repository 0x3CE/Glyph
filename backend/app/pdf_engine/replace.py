"""Find and replace across a document, as a series of ordinary line edits.

Each line holding the searched text is edited exactly as if the user had
retyped it (`apply_block_edit`): the old glyphs are really removed and the
untouched parts of the line keep their original fonts. Same limits as a
manual edit, plus one: a phrase broken across two lines isn't found, since
the engine edits line by line (see structure.extract_structure).
"""

from __future__ import annotations

import re
import unicodedata

import pymupdf

from .editor import apply_block_edit
from .structure import extract_structure
from .types import Block

# A line whose text matches but whose position moved by more than this
# (points) between two extractions is not the same line.
SAME_LINE_TOLERANCE = 2.0


def _clusters(text: str) -> list[tuple[int, int]]:
    """(start, end) of each base character with the combining marks that
    follow it: an "e" followed by a combining grave accent is one "è"."""
    clusters: list[tuple[int, int]] = []
    for i, char in enumerate(text):
        if clusters and unicodedata.combining(char):
            clusters[-1] = (clusters[-1][0], i + 1)
        else:
            clusters.append((i, i + 1))
    return clusters


def _folded(text: str, match_case: bool) -> tuple[str, list[int], list[tuple[int, int]]]:
    """`text` with ligatures, special spaces and accents folded to one
    canonical form ("ﬁ" -> "fi", no-break space -> space, "e" + combining
    accent -> "è"), plus, for each folded character, which cluster of the
    original text it comes from, and those clusters' (start, end): PDFs
    often store "fichier" with an "ﬁ" ligature, which a search for
    "fichier" must still find."""
    clusters = _clusters(text)
    out: list[str] = []
    owner: list[int] = []
    for k, (start, end) in enumerate(clusters):
        folded = unicodedata.normalize("NFKC", text[start:end])
        if not match_case:
            folded = folded.casefold()
        out.append(folded)
        owner.extend([k] * len(folded))
    return "".join(out), owner, clusters


def compile_search(find: str, match_case: bool, whole_word: bool) -> re.Pattern[str]:
    folded, _, _ = _folded(find, match_case)
    pattern = re.escape(folded)
    if whole_word:
        pattern = rf"(?<!\w){pattern}(?!\w)"
    return re.compile(pattern)


def replace_in_text(text: str, search: re.Pattern[str], replacement: str, match_case: bool) -> tuple[str, int]:
    """(new text, number of occurrences replaced). A match that would start
    or end in the middle of a ligature ("f" inside "ﬁ") is skipped: it
    can't be cut out without changing the letters around it."""
    folded, owner, clusters = _folded(text, match_case)
    pieces: list[str] = []
    cursor = 0
    count = 0
    for m in search.finditer(folded):
        if m.start() == m.end():
            continue
        first, last = owner[m.start()], owner[m.end() - 1]
        starts_clean = m.start() == 0 or owner[m.start() - 1] != first
        ends_clean = m.end() == len(folded) or owner[m.end()] != last
        start, end = clusters[first][0], clusters[last][1]
        if not (starts_clean and ends_clean) or start < cursor:
            continue
        pieces.append(text[cursor:start])
        pieces.append(replacement)
        cursor = end
        count += 1
    pieces.append(text[cursor:])
    return "".join(pieces), count


def _matching_lines(page: pymupdf.Page, search: re.Pattern[str], replacement: str, match_case: bool):
    """(bbox, current text, new text, occurrences) of every line to edit.
    Lines whose text layer can't be read (Block.text_reliable) are skipped:
    their extracted text isn't what is drawn."""
    for block in extract_structure(page):
        if not block.text_reliable:
            continue
        new_text, count = replace_in_text(block.text, search, replacement, match_case)
        if count:
            yield block.bbox, block.text, new_text, count


def count_matches(page: pymupdf.Page, search: re.Pattern[str], match_case: bool) -> int:
    return sum(count for *_, count in _matching_lines(page, search, "", match_case))


def _same_line(blocks: list[Block], bbox: tuple[float, float, float, float], text: str) -> Block | None:
    for block in blocks:
        if block.text == text and all(abs(a - b) <= SAME_LINE_TOLERANCE for a, b in zip(block.bbox, bbox)):
            return block
    return None


def replace_on_page(
    doc: pymupdf.Document,
    page: pymupdf.Page,
    search: re.Pattern[str],
    replacement: str,
    match_case: bool,
    max_lines: int,
) -> dict:
    """Edits every matching line of the page (at most `max_lines`).

    The targets are listed once, up front, then each one is found again in a
    fresh extraction right before its edit (an edit can renumber the
    page's lines). Working from that fixed list is also what keeps a
    replacement that contains the searched text ("ab" -> "abc") from
    looping forever."""
    targets = list(_matching_lines(page, search, replacement, match_case))
    replaced = 0
    lines = 0
    substituted = False
    for bbox, old_text, new_text, count in targets[:max_lines]:
        blocks = extract_structure(page)
        block = _same_line(blocks, bbox, old_text)
        if block is None:
            continue
        font_substituted, _ = apply_block_edit(doc, page, block, new_text, all_blocks=blocks)
        substituted |= font_substituted
        replaced += count
        lines += 1
    return {
        "replaced": replaced,
        "lines": lines,
        "remaining_lines": max(0, len(targets) - max_lines),
        "font_substituted": substituted,
    }

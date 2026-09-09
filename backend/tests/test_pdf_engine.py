"""Regression tests for the block-detection and redaction-safety invariants
in pdf_engine.py -- each one pins down a real bug found by hand-testing
against real-world documents (see docs/DECISIONS.md for the full story
behind each). Run with:

    .venv/bin/python -m unittest discover -s tests -v

Deliberately stdlib-only (unittest + pymupdf, already a dependency) so this
doesn't require adding a test framework to run it.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf

import app.pdf_engine as pdf_engine
from app.pdf_engine import Block, Line, Span, apply_block_edit, extract_structure


def _page(width=595, height=200):
    doc = pymupdf.open()
    return doc, doc.new_page(width=width, height=height)


class ExtractStructureTests(unittest.TestCase):
    """`_is_coherent_paragraph`, exercised through the public extraction
    entrypoint rather than directly, so these keep testing the real code
    path a request actually takes."""

    def test_stacked_headline_and_subtitle_are_separate_blocks(self):
        # Two independent, complete sentences that happen to share a left
        # edge and font -- not a wrapped paragraph. Real bug: editing the
        # subtitle's year silently deleted the title above it.
        doc, page = _page()
        page.insert_text((40, 70), "IMPOT SUR LES REVENUS DE L'ANNEE 2025", fontsize=16, fontname="hebo")
        page.insert_text((40, 92), "AVIS DE SITUATION DECLARATIVE ETABLI EN 2026", fontsize=16, fontname="hebo")
        blocks = extract_structure(page)
        texts = [b.text for b in blocks]
        self.assertIn("IMPOT SUR LES REVENUS DE L'ANNEE 2025", texts)
        self.assertIn("AVIS DE SITUATION DECLARATIVE ETABLI EN 2026", texts)

    def test_wrapped_address_paragraph_is_split_per_line(self):
        # Deliberate design choice, not a bug: Glyph used to merge lines
        # that looked like a wrapped paragraph into one reflow-capable
        # block, but "shares an edge / alignment" kept turning out to
        # describe independent lines too (a title stacked on a subtitle, a
        # right-aligned value column) across enough real documents that the
        # merge was judged not worth the risk. Every line -- including a
        # genuine wrapped paragraph like this address -- is its own block;
        # editing a multi-line field now takes one click per line.
        doc, page = _page()
        rect = pymupdf.Rect(40, 40, 260, 100)
        page.insert_textbox(
            rect,
            "Monsieur et Madame Jean Dupont 12 Rue de la Republique Residence Les Jardins 75001 Paris",
            fontsize=11,
            fontname="helv",
        )
        blocks = extract_structure(page)
        self.assertEqual(len(blocks), 3)
        texts = [b.text for b in blocks]
        self.assertTrue(any("Dupont" in t for t in texts))
        self.assertTrue(any("Paris" in t for t in texts))

    def test_right_aligned_value_column_is_split_per_line(self):
        # Mirror of the headline case: a right-aligned column of unrelated
        # short values (a reference number, an order index, a date) shares
        # a right edge purely by layout coincidence. Real bug: editing one
        # value corrupted all three at once.
        doc, page = _page(width=300, height=100)
        page.insert_text((5, 15), "310 12 47 5907959789 3", fontsize=9, fontname="helv")
        page.insert_text((100, 25), "2", fontsize=9, fontname="helv")
        page.insert_text((60, 35), "28/04/2026", fontsize=9, fontname="helv")
        blocks = extract_structure(page)
        texts = {b.text.strip() for b in blocks}
        self.assertIn("310 12 47 5907959789 3", texts)
        self.assertIn("2", texts)
        self.assertIn("28/04/2026", texts)

    def test_label_and_far_value_on_same_baseline_are_separate_blocks(self):
        # A form field where the label and its value sit on the same
        # visual line but are far apart horizontally ("Nom :
        # DUPONT") must be two independently editable blocks, not one --
        # editing the value should never touch the label's own formatting.
        # PyMuPDF's own line segmentation already starts a new line past
        # roughly a one-character-wide gap, well under what a deliberate
        # label/value gap looks like, so this falls out of always trusting
        # its line boundaries rather than needing bespoke gap detection.
        doc, page = _page(width=400, height=100)
        page.insert_text((40, 50), "Nom :", fontsize=10, fontname="helv")
        page.insert_text((250, 50), "DUPONT", fontsize=10, fontname="helv")
        blocks = extract_structure(page)
        texts = {b.text.strip() for b in blocks}
        self.assertEqual(len(blocks), 2)
        self.assertIn("Nom :", texts)
        self.assertIn("DUPONT", texts)

    def test_table_cells_at_different_x_positions_are_split(self):
        # The original merge failure this heuristic was built for: cells
        # from different table columns clustered into one raw PyMuPDF block
        # purely by vertical proximity.
        doc, page = _page()
        page.insert_text((40, 50), "Nom", fontsize=10, fontname="helv")
        page.insert_text((300, 50), "Prenom", fontsize=10, fontname="helv")
        blocks = extract_structure(page)
        texts = {b.text for b in blocks}
        self.assertIn("Nom", texts)
        self.assertIn("Prenom", texts)


class ApplyBlockEditSafetyTests(unittest.TestCase):
    """A block's own bbox can legitimately overlap a sibling's by a couple
    points in real documents (tight line leading, tightly-packed table
    columns) even after extract_structure correctly separates them. Editing
    one must never erase or corrupt the other, regardless of which side the
    overlap is on."""

    def _make(self, block_id, bbox, text, font="Helvetica", size=10.0, flags=0):
        return Block(
            id=block_id,
            bbox=bbox,
            lines=[
                Line(
                    bbox=bbox,
                    spans=[
                        Span(
                            text=text,
                            bbox=bbox,
                            font=font,
                            size=size,
                            color=0,
                            flags=flags,
                            origin=(bbox[0], bbox[3] - size * 0.2),
                        )
                    ],
                )
            ],
        )

    def test_editing_title_preserves_overlapping_line_below(self):
        title = self._make("title", (153.0, 37.02, 456.618, 56.298), "IMPOT SUR LES REVENUS DE L'ANNEE 2025", size=14)
        avis = self._make("avis", (152.747, 53.382, 453.826, 70.566), "AVIS DE SITUATION DECLARATIVE ETABLI EN 2026", size=12)
        all_blocks = [title, avis]

        doc, page = _page(width=612)
        page.insert_text((153.0, 52.0), title.text, fontsize=14, fontname="hebo")
        page.insert_text((152.747, 66.0), avis.text, fontsize=12, fontname="hebo")

        apply_block_edit(doc, page, title, "IMPOT SUR LES REVENUS DE L'ANNEE 2024", all_blocks=all_blocks)
        text = page.get_text()
        self.assertIn("2026", text)
        self.assertIn("2024", text)
        self.assertNotIn("2025", text)

    def test_editing_subtitle_preserves_overlapping_title_above(self):
        title = self._make("title", (153.0, 37.02, 456.618, 56.298), "IMPOT SUR LES REVENUS DE L'ANNEE 2025", size=14)
        avis = self._make("avis", (152.747, 53.382, 453.826, 70.566), "AVIS DE SITUATION DECLARATIVE ETABLI EN 2026", size=12)
        all_blocks = [title, avis]

        doc, page = _page(width=612)
        page.insert_text((153.0, 52.0), title.text, fontsize=14, fontname="hebo")
        page.insert_text((152.747, 66.0), avis.text, fontsize=12, fontname="hebo")

        apply_block_edit(doc, page, avis, "AVIS DE SITUATION DECLARATIVE ETABLI EN 2025", all_blocks=all_blocks)
        text = page.get_text()
        self.assertIn("IMPOT SUR LES REVENUS DE L'ANNEE 2025", text)
        self.assertIn("AVIS DE SITUATION DECLARATIVE ETABLI EN 2025", text)

    def test_editing_left_cell_preserves_touching_right_cell(self):
        left_cell = self._make("left", (40.0, 100.0, 152.0, 114.0), "DUPONT")
        right_cell = self._make("right", (150.0, 100.0, 260.0, 114.0), "MARTIN")
        all_blocks = [left_cell, right_cell]

        doc, page = _page(width=400)
        page.insert_text((40.0, 111.0), "DUPONT", fontsize=10, fontname="helv")
        page.insert_text((150.0, 111.0), "MARTIN", fontsize=10, fontname="helv")

        apply_block_edit(doc, page, left_cell, "DURAND-LEFEBVRE", all_blocks=all_blocks)
        text = page.get_text()
        self.assertIn("MARTIN", text)
        self.assertIn("DURAND-LEFEBVRE", text)

    def test_editing_right_cell_preserves_touching_left_cell(self):
        left_cell = self._make("left", (40.0, 100.0, 152.0, 114.0), "DUPONT")
        right_cell = self._make("right", (150.0, 100.0, 260.0, 114.0), "MARTIN")
        all_blocks = [left_cell, right_cell]

        doc, page = _page(width=400)
        page.insert_text((40.0, 111.0), "DUPONT", fontsize=10, fontname="helv")
        page.insert_text((150.0, 111.0), "MARTIN", fontsize=10, fontname="helv")

        apply_block_edit(doc, page, right_cell, "DURAND-LEFEBVRE", all_blocks=all_blocks)
        text = page.get_text()
        self.assertIn("DUPONT", text)
        self.assertIn("DURAND-LEFEBVRE", text)

    def test_single_line_block_can_grow_to_multiple_lines_without_erasing_whats_below(self):
        # A block is always one original line, but the user can still type
        # their own line breaks into it (e.g. turning a one-line field into
        # a short multi-line note) -- it must grow downward without erasing
        # an unrelated field sitting right below it.
        field = self._make("field", (40.0, 40.0, 150.0, 54.0), "Reference: 12345", size=11)
        below = self._make("below", (40.0, 60.0, 150.0, 74.0), "Date: 01/01/2026", size=11)
        all_blocks = [field, below]

        doc, page = _page()
        page.insert_text((40.0, 51.0), field.text, fontsize=11, fontname="helv")
        page.insert_text((40.0, 71.0), below.text, fontsize=11, fontname="helv")

        apply_block_edit(doc, page, field, "Reference: 12345\nNote: urgent", all_blocks=all_blocks)
        text = page.get_text()
        self.assertIn("Reference: 12345", text)
        self.assertIn("Note: urgent", text)
        self.assertIn("Date: 01/01/2026", text)

    def test_editing_middle_row_of_tight_value_column_leaves_no_leftover_glyph(self):
        # Real bug: a lone "2" sits, with tight leading, between a long
        # reference number above and a date below in a 3-row right-aligned
        # value column. "2"'s bbox perpendicularly overlaps BOTH neighbors
        # (same tight-leading pattern as the title/subtitle case), but it
        # is nested almost entirely INSIDE the date's own horizontal span,
        # not beside it -- a naive "any perpendicular overlap counts as a
        # neighbor" rule wrongly treated it as a horizontal neighbor of the
        # date, clamping the date's own redaction short of its own last
        # character and leaving the old "6" (from "2026") behind, rendered
        # at the original (larger) size next to the new, shrunk text.
        doc, page = _page(width=300, height=400)
        page.insert_text((133.92, 365.0), "310 12 47 5907959789 3", fontsize=9, fontname="helv")
        page.insert_text((229.0, 375.0), "2", fontsize=9, fontname="helv")
        page.insert_text((188.96, 385.0), "28/04/2026", fontsize=9, fontname="helv")
        blocks = extract_structure(page)
        target = next(b for b in blocks if "2026" in b.text)

        apply_block_edit(doc, page, target, "28/04/2099", all_blocks=blocks)
        text = page.get_text()
        self.assertIn("28/04/2099", text)
        self.assertNotIn("2026", text)
        self.assertEqual(text.count("6"), 0, "a leftover glyph from the original text survived the edit")
        self.assertIn("310 12 47 5907959789 3", text)
        self.assertIn("2", text)


class BundledFontFallbackTests(unittest.TestCase):
    """The backend deploys to Linux (Render), which has none of the
    macOS-only system fonts `_SYSTEM_FAMILIES` names -- these pin down that
    the bundled Liberation Fonts (`app/fonts/liberation/`, SIL OFL) are used
    correctly in that case, since silently falling all the way back to
    Base-14 Helvetica/Times would lose the Euro sign and other characters
    (see docs/DECISIONS.md)."""

    def setUp(self):
        # Simulate running without macOS's system fonts, regardless of the
        # platform actually running this test.
        self._real_system_font_dir = pdf_engine._SYSTEM_FONT_DIR
        pdf_engine._SYSTEM_FONT_DIR = Path("/nonexistent-on-purpose")

    def tearDown(self):
        pdf_engine._SYSTEM_FONT_DIR = self._real_system_font_dir

    def test_bundled_fonts_exist_on_disk(self):
        for filename in {
            f
            for family in pdf_engine._BUNDLED_FAMILIES.values()
            for f in family.values()
        }:
            path = pdf_engine._BUNDLED_FONT_DIR / filename
            self.assertTrue(path.is_file(), f"missing bundled font: {path}")

    def test_named_family_falls_back_to_bundled_font(self):
        self.assertEqual(
            pdf_engine._system_font_path("arial", False, False),
            str(pdf_engine._BUNDLED_FONT_DIR / "LiberationSans-Regular.ttf"),
        )
        self.assertEqual(
            pdf_engine._system_font_path("times new roman", True, True),
            str(pdf_engine._BUNDLED_FONT_DIR / "LiberationSerif-BoldItalic.ttf"),
        )
        self.assertIsNone(pdf_engine._system_font_path("comic sans", False, False))

    def test_euro_sign_and_typographic_punctuation_survive_the_fallback(self):
        doc, page = _page(width=400)
        page.insert_text((40, 50), "Montant : 100 EUR", fontsize=11, fontname="helv")
        blocks = extract_structure(page)
        # Force a non-bundled original font name so pick_font must go
        # through the named-family alias -> bundled-font path.
        block = blocks[0]
        original_span = block.lines[0].spans[0]
        block.lines[0].spans[0] = Span(
            **{**original_span.__dict__, "font": "ArialMT"},
        )

        apply_block_edit(doc, page, block, "Montant : 1 234,56 € — «Test»", all_blocks=blocks)
        text = page.get_text()
        self.assertIn("€", text)
        self.assertIn("«Test»", text)


if __name__ == "__main__":
    unittest.main()

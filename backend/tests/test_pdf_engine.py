"""Regression tests for the block-detection and redaction-safety invariants
in pdf_engine.py -- each one pins down a real bug found by hand-testing
against real-world documents (see docs/DECISIONS.md for the full story
behind each). Run with:

    .venv/bin/python -m unittest discover -s tests -v

Deliberately stdlib-only (unittest + pymupdf, already a dependency) so this
doesn't require adding a test framework to run it.
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf
from fontTools.ttLib import TTFont

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

    def test_grows_sideways_instead_of_shrinking_when_no_neighbor_blocks_it(self):
        # Real bug: a substitute font (metrically wider than the original)
        # plus a slightly longer replacement word needed noticeably more
        # width than the original text did. With nothing to the right for
        # ~250pt, the field should grow into that empty space rather than
        # shrink its font size for no reason -- a 19% shrink was observed
        # in practice before this fix.
        field = self._make("field", (40.0, 40.0, 86.6, 54.0), "Gris Clair", size=11)
        doc, page = _page(width=400)
        page.insert_text((40.0, 51.0), field.text, fontsize=11, fontname="helv")

        apply_block_edit(doc, page, field, "Gris foncée", all_blocks=[field])
        new_span = extract_structure(page)[0].dominant_span
        self.assertGreaterEqual(new_span.size, 11.0 * 0.95, "font was shrunk despite no neighbor blocking growth")

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
        # platform actually running this test. Patched on `pdf_engine.fonts`
        # (where `_system_font_path` actually reads the global from), not on
        # the re-exporting `pdf_engine` package -- those are separate name
        # bindings once the engine is split into submodules.
        self._real_system_font_dir = pdf_engine.fonts._SYSTEM_FONT_DIR
        pdf_engine.fonts._SYSTEM_FONT_DIR = Path("/nonexistent-on-purpose")

    def tearDown(self):
        pdf_engine.fonts._SYSTEM_FONT_DIR = self._real_system_font_dir

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


class Type3WeightMatchingTests(unittest.TestCase):
    """A Type3 font (glyphs are arbitrary vector-drawing programs) has no
    OS/2/name table, so PyMuPDF's `flags` always reports 0 -- indistinguishable
    from a genuinely non-bold font. Real bug: a light/thin Type3 original got
    replaced by a much heavier default weight. These pin down that the
    rendered-ink-based weight matching (`_closest_weight_by_ink`) lands in
    the right zone of the `wght` axis (300-800) instead."""

    def _span_with_font_name(self, page, forced_font_name: str) -> Span:
        # extract_structure gives a real, tight bbox (unlike a hand-computed
        # one) -- that precision matters for the ink-ratio comparison to be
        # meaningful, so build the span from it rather than constructing one
        # by hand.
        span = extract_structure(page)[0].dominant_span
        return Span(**{**span.__dict__, "font": forced_font_name})

    def test_matches_each_bundled_weight_correctly(self):
        for true_weight, filename, expected_range in (
            ("light", "OpenSans-Light.ttf", (300.0, 380.0)),
            ("regular", "OpenSans-Regular.ttf", (400.0, 400.0)),
            ("bold", "OpenSans-Bold.ttf", (620.0, 700.0)),
        ):
            with self.subTest(true_weight=true_weight):
                doc, page = _page(width=400, height=100)
                fontfile = str(pdf_engine._OPENSANS_FONT_DIR / filename)
                page.insert_text((40, 50), "Gris Clair", fontsize=11, fontname="fref", fontfile=fontfile)
                span = self._span_with_font_name(page, "Type3 (1 0 R)")
                weight = pdf_engine._closest_weight_by_ink(page, span.bbox, span.text, span.size)
                lo, hi = expected_range
                self.assertTrue(lo <= weight <= hi, f"{true_weight}: expected {lo}-{hi}, got {weight}")

    def test_editing_type3_original_via_apply_block_edit_embeds_the_bisected_weight(self):
        # Same check as `test_type3_sans_serif_uses_the_current_bisected_default_weight`
        # but through the full `apply_block_edit` path (redaction + actual
        # PDF embedding), not just `pick_font` -- confirms the chosen font
        # file's weight really is what ends up embedded in the page, not
        # just what `pick_font` returns. Checks the embedded font's actual
        # OS/2.usWeightClass rather than its name: the dynamically-instantiated
        # font this code path always produces right now has no meaningful
        # name, since `_instantiate_weight` skips `updateFontNames` for
        # these one-off, discarded files.
        doc, page = _page(width=400, height=100)
        fontfile = str(pdf_engine._OPENSANS_FONT_DIR / "OpenSans-Light.ttf")
        page.insert_text((40, 50), "Gris Clair", fontsize=11, fontname="fref", fontfile=fontfile)
        blocks = extract_structure(page)
        block = blocks[0]
        block.lines[0].spans[0] = self._span_with_font_name(page, "Type3 (1 0 R)")

        apply_block_edit(doc, page, block, "Rouge Clair", all_blocks=blocks)

        embedded_weight = None
        for f in page.get_fonts(full=True):
            xref = f[0]
            _name, _ext, _ftype, font_bytes = doc.extract_font(xref)
            if font_bytes:
                embedded_weight = TTFont(io.BytesIO(font_bytes))["OS/2"].usWeightClass
        self.assertEqual(embedded_weight, pdf_engine._TYPE3_DEFAULT_WEIGHT)

    def test_real_document_field_interpolates_between_samples(self):
        # Exact numbers measured on the real document that exposed this,
        # at the current zoom (12x -- see docs/DECISIONS.md for why 4x
        # wasn't enough resolution): the original sits genuinely between
        # the regular and bold samples, not on top of either one. Snapping
        # to whichever bucket is merely closest ("regular", the smaller
        # diff) still looked visibly heavier than the true original in
        # practice -- interpolating a continuous point between the two
        # brackets is what actually matches it.
        weight = pdf_engine._interpolate_weight(
            0.1503, {"light": 0.0857, "regular": 0.1210, "bold": 0.1898}
        )
        self.assertTrue(450.0 <= weight <= 600.0, f"expected an intermediate weight, got {weight}")

    def test_decisive_light_signal_interpolates_near_light(self):
        weight = pdf_engine._interpolate_weight(0.091, {"light": 0.090, "regular": 0.140, "bold": 0.205})
        self.assertTrue(300.0 <= weight <= 320.0, f"expected a weight near light (300), got {weight}")

    def test_finds_longer_same_resource_calibration_text(self):
        # `_find_calibration_text` itself: still real, tested, kept in the
        # file for its diagnostic value (see docs/DECISIONS.md), even
        # though `pick_font` doesn't call it right now -- the computed
        # weight it enables turned out to still render too heavy in
        # practice across three independent viewers, for reasons the ink
        # measurement itself couldn't explain. `pick_font` currently uses
        # a flat Light default for Type3 sources instead (tested below).
        #
        # `_find_calibration_text` reads the font name straight back from
        # the page's own content stream (`page.get_text("dict")`), not
        # from any Python-side `Span` object -- so unlike other tests in
        # this file, faking `.font` on an already-extracted `Span` doesn't
        # reach it; both runs here genuinely share PyMuPDF's own resource
        # name for this embedded font.
        doc, page = _page(width=595, height=100)
        fontfile = str(pdf_engine._OPENSANS_FONT_DIR / "OpenSans-Regular.ttf")
        page.insert_text((40, 30), "Velo route Cyclotourisme RC120 Disque", fontsize=11, fontname="fref", fontfile=fontfile)
        page.insert_text((40, 55), "Gris Clair", fontsize=11, fontname="fref", fontfile=fontfile)

        target = next(b for b in extract_structure(page) if "clair" in b.text.lower())
        font_name = target.dominant_span.font
        own_bboxes = {tuple(s.bbox) for line in target.lines for s in line.spans}

        calibration = pdf_engine._find_calibration_text(page, font_name, own_bboxes)
        self.assertIsNotNone(calibration)
        cal_text, _cal_bbox = calibration
        self.assertIn("Cyclotourisme", cal_text)

    def test_type3_sans_serif_uses_the_current_bisected_default_weight(self):
        # Pragmatic current default, under active manual bisection on a
        # real document (see docs/DECISIONS.md): Light (300) came back too
        # thin, the ink-ratio-calibrated ~450 came back too thick.
        # `_TYPE3_DEFAULT_WEIGHT` is the single source of truth for
        # whatever point is being tried next -- read it here instead of
        # hardcoding a number, so this test stays in sync automatically
        # while that constant keeps changing.
        doc, page = _page(width=400, height=100)
        fontfile = str(pdf_engine._OPENSANS_FONT_DIR / "OpenSans-Bold.ttf")
        page.insert_text((40, 50), "Gris Clair", fontsize=11, fontname="fref", fontfile=fontfile)
        block = extract_structure(page)[0]
        block.lines[0].spans[0] = Span(**{**block.lines[0].spans[0].__dict__, "font": "Type3 (1 0 R)"})

        font_choice = pdf_engine.pick_font(doc, page, block, "Gris fonce")
        embedded_weight = TTFont(font_choice.fontfile)["OS/2"].usWeightClass
        self.assertEqual(embedded_weight, pdf_engine._TYPE3_DEFAULT_WEIGHT)


class MixedFormattingPreservationTests(unittest.TestCase):
    """A single PyMuPDF line can carry more than one font (e.g. a bold
    defined-term inside an otherwise plain sentence: '...ou « TEMF »').
    `Block.dominant_span` picks ONE span (by character count) to represent
    the whole block for reinsertion -- real bug: the surrounding plain text
    always outweighs a short bold acronym, so editing ANYTHING in the
    sentence, even far from "TEMF", silently dropped its bold. These pin
    down that `_build_formatted_segments` + `apply_block_edit` reuse each
    unchanged run's own original span instead."""

    def _insert_mixed_line(self, page, regular_font, bold_font):
        page.insert_text((40, 50), "Ci-apres denommee ", fontsize=10, fontname="freg", fontfile=regular_font, set_simple=1)
        x1 = pymupdf.Font(fontfile=regular_font).text_length("Ci-apres denommee ", fontsize=10)
        page.insert_text((40 + x1, 50), "TEMF", fontsize=10, fontname="fbold", fontfile=bold_font, set_simple=1)
        x2 = x1 + pymupdf.Font(fontfile=bold_font).text_length("TEMF", fontsize=10)
        page.insert_text((40 + x2, 50), " dans ce contrat", fontsize=10, fontname="freg2", fontfile=regular_font, set_simple=1)

    def test_editing_elsewhere_in_the_sentence_keeps_the_untouched_bold_word(self):
        doc, page = _page(width=595, height=100)
        regular = "/System/Library/Fonts/Supplemental/Arial.ttf"
        bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        self._insert_mixed_line(page, regular, bold)
        block = extract_structure(page)[0]
        self.assertEqual(len(block.lines[0].spans), 3, "test setup should produce 3 spans (plain/bold/plain)")

        apply_block_edit(doc, page, block, "Ci-apres nommee TEMF dans ce contrat de vente", all_blocks=[block])

        spans = extract_structure(page)[0].lines[0].spans
        bold_spans = [s for s in spans if s.flags & pdf_engine.FLAG_BOLD]
        self.assertTrue(bold_spans, "expected at least one bold span to survive")
        self.assertTrue(any(s.text.strip() == "TEMF" for s in bold_spans), "expected TEMF specifically to stay bold")
        non_bold_text = "".join(s.text for s in spans if not (s.flags & pdf_engine.FLAG_BOLD))
        self.assertNotIn("TEMF", non_bold_text)

    def test_replacing_the_bold_word_itself_keeps_it_bold(self):
        # Real bug, found right after the first fix shipped: a user
        # replaced "TEMF" with a different acronym ("GDPR") -- since the
        # new word is never "unchanged" from the original, the first
        # (equal-run-only) version of this feature still lost the bold
        # here. `_span_for_change` covers this: the changed range (old
        # "TEMF") is entirely contained within one span (the bold one), so
        # the replacement text inherits that span's formatting.
        doc, page = _page(width=595, height=100)
        regular = "/System/Library/Fonts/Supplemental/Arial.ttf"
        bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        self._insert_mixed_line(page, regular, bold)
        block = extract_structure(page)[0]

        apply_block_edit(doc, page, block, "Ci-apres denommee GDPR dans ce contrat", all_blocks=[block])
        spans = extract_structure(page)[0].lines[0].spans
        bold_spans = [s for s in spans if s.flags & pdf_engine.FLAG_BOLD]
        self.assertTrue(any(s.text.strip() == "GDPR" for s in bold_spans), "expected GDPR to inherit TEMF's bold")
        self.assertNotIn("TEMF", page.get_text())

    def test_change_spanning_multiple_original_spans_falls_back_to_overall_font(self):
        # Genuinely ambiguous case: the changed range crosses from the
        # plain prefix into the bold word, so there's no single original
        # span to attribute the replacement to -- `_span_for_change`
        # returns None and it falls back to the block's overall font, same
        # as before either fix existed. Not a regression: nothing here
        # tells us the user still wants any part of this bold. Deliberately
        # disjoint placeholder text ("AAAA"/"BBBB"/"ZZZZZZZZZ") instead of
        # prose here: real words risk sharing short common substrings that
        # let difflib match more finely than intended, obscuring the
        # single-clean-replace-opcode case this test means to exercise.
        doc, page = _page(width=595, height=100)
        regular = "/System/Library/Fonts/Supplemental/Arial.ttf"
        bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        page.insert_text((40, 50), "AAAA ", fontsize=10, fontname="freg", fontfile=regular, set_simple=1)
        x1 = pymupdf.Font(fontfile=regular).text_length("AAAA ", fontsize=10)
        page.insert_text((40 + x1, 50), "BBBB", fontsize=10, fontname="fbold", fontfile=bold, set_simple=1)
        x2 = x1 + pymupdf.Font(fontfile=bold).text_length("BBBB", fontsize=10)
        page.insert_text((40 + x2, 50), " CCCC", fontsize=10, fontname="freg2", fontfile=regular, set_simple=1)
        block = extract_structure(page)[0]
        self.assertEqual(len(block.lines[0].spans), 3, "test setup should produce 3 spans (plain/bold/plain)")

        apply_block_edit(doc, page, block, "ZZZZZZZZZ CCCC", all_blocks=[block])
        spans = extract_structure(page)[0].lines[0].spans
        self.assertFalse(
            any(s.flags & pdf_engine.FLAG_BOLD for s in spans if "ZZZZZZZZZ" in s.text),
            "an ambiguous, multi-span change should not inherit bold from either original span",
        )
        self.assertNotIn("BBBB", page.get_text())


if __name__ == "__main__":
    unittest.main()

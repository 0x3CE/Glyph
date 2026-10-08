"""Regression tests for the block-detection and redaction-safety invariants
in pdf_engine.py -- each one pins down a real bug found by hand-testing
against real-world documents (see docs/DECISIONS.md for the full story
behind each). Run with:

    .venv/bin/python -m unittest discover -s tests -v

Deliberately stdlib-only (unittest + pymupdf, already a dependency) so this
doesn't require adding a test framework to run it.
"""

from __future__ import annotations

import dataclasses
import io
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf
from fontTools.ttLib import TTFont

import app.pdf_engine as pdf_engine
from app.pdf_engine import font_catalog
from app.pdf_engine import Block, Line, Span, UnsupportedSignatureFileError, apply_block_edit, apply_signature, extract_structure


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

    def test_committed_bundled_fonts_exist_on_disk(self):
        # Liberation and Open Sans are committed (the rest of the catalog is
        # fetched by scripts/fetch_fonts.py at build time): they're the floor
        # every environment is guaranteed to have.
        for key in ("arial", "times new roman", "liberation mono", "open sans"):
            family = font_catalog.BY_KEY[key]
            for filename in family.files.values():
                path = pdf_engine._BUNDLED_FONT_DIR / family.directory / filename
                self.assertTrue(path.is_file(), f"missing bundled font: {path}")

    def test_named_family_falls_back_to_bundled_font(self):
        liberation = pdf_engine._BUNDLED_FONT_DIR / "liberation"
        self.assertEqual(
            pdf_engine._family_font("arial", False, False),
            (str(liberation / "LiberationSans-Regular.ttf"), False),
        )
        self.assertEqual(
            pdf_engine._family_font("times new roman", True, True),
            (str(liberation / "LiberationSerif-BoldItalic.ttf"), False),
        )
        self.assertIsNone(pdf_engine._family_font("not a real family", False, False))

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


def _require_bundled(key: str):
    family = font_catalog.BY_KEY[key]
    regular = pdf_engine._BUNDLED_FONT_DIR / family.directory / family.files[font_catalog.REGULAR]
    if not regular.is_file():
        raise unittest.SkipTest(f"{key} not fetched -- run scripts/fetch_fonts.py")


class FontCatalogTests(unittest.TestCase):
    """The bundled catalog (`font_catalog.CATALOG`): mapping a PDF's font
    name to the right family, and picking the closest file for it."""

    def setUp(self):
        self._real_system_font_dir = pdf_engine.fonts._SYSTEM_FONT_DIR
        pdf_engine.fonts._SYSTEM_FONT_DIR = Path("/nonexistent-on-purpose")

    def tearDown(self):
        pdf_engine.fonts._SYSTEM_FONT_DIR = self._real_system_font_dir

    def test_font_names_resolve_to_the_most_specific_family(self):
        cases = {
            "ABCDEF+Calibri-Bold": "calibri",
            "Calibri,Italic": "calibri",
            "ArialMT": "arial",
            "Arial-BoldMT": "arial",
            "ArialNarrow-Bold": "arial narrow",
            "TimesNewRomanPSMT": "times new roman",
            "HelveticaNeue-Light": "helvetica",
            "Roboto-Regular": "roboto",
            "RobotoMono-Bold": "roboto mono",
            "RobotoCondensed-Italic": "roboto condensed",
            "AdobeGaramondPro-Regular": "eb garamond",
            "CormorantGaramond-Bold": "cormorant garamond",
            "ITCFranklinGothic-Book": "libre franklin",
            "SourceSansPro-Regular": "source sans 3",
            "PlayfairDisplay-Bold": "playfair display",
            "Inter-SemiBold": "inter",
            "CMR10": "latin modern roman",
            "SegoeUI-Bold": "segoe ui",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(pdf_engine._family_for_original(name), expected)

    def test_courier_uses_nimbus_mono_then_falls_back_to_liberation_mono(self):
        # Liberation Mono's strokes are far heavier than Courier's: a retyped
        # payslip line looked bold in production. Nimbus Mono PS when it was
        # fetched, the committed Liberation Mono otherwise.
        _require_bundled("courier new")
        path, _same = pdf_engine._family_font("courier new", False, False)
        self.assertTrue(path.endswith("NimbusMonoPS-Regular.ttf"), path)
        missing = dataclasses.replace(font_catalog.BY_KEY["courier new"], directory="not-fetched")
        with mock.patch.dict(font_catalog.BY_KEY, {"courier new": missing}):
            path, same = pdf_engine._family_font("courier new", False, False)
        self.assertTrue(path.endswith("LiberationMono-Regular.ttf"), path)
        self.assertFalse(same)

    def test_short_needles_only_match_as_a_prefix(self):
        # "inter" / "cmr" must not fire inside an unrelated longer name.
        self.assertIsNone(pdf_engine._family_for_original("WinterSans-Regular"))
        self.assertIsNone(pdf_engine._family_for_original("ArcMRegular"))

    def test_every_catalog_family_has_a_regular_style_and_a_license(self):
        for family in font_catalog.CATALOG:
            with self.subTest(family=family.key):
                self.assertIn(font_catalog.REGULAR, family.files)
                directory = pdf_engine._BUNDLED_FONT_DIR / family.directory
                if (directory / family.files[font_catalog.REGULAR]).is_file():
                    self.assertTrue((directory / family.license_file).is_file())

    def test_missing_style_degrades_to_the_closest_one(self):
        _require_bundled("oswald")  # no italic at all
        path, same = pdf_engine._family_font("oswald", True, True)
        self.assertTrue(path.endswith("Oswald-Bold.ttf"), path)
        self.assertTrue(same)

    def _edit(self, font_name: str, new_text: str, flags: int = 0):
        doc, page = _page(width=400)
        page.insert_text((40, 50), "Bonjour le monde", fontsize=11, fontname="helv")
        blocks = extract_structure(page)
        block = blocks[0]
        original_span = block.lines[0].spans[0]
        block.lines[0].spans[0] = Span(**{**original_span.__dict__, "font": font_name, "flags": flags})
        substituted, _bbox = apply_block_edit(doc, page, block, new_text, all_blocks=blocks)
        return substituted, {f[3].split("+")[-1] for f in page.get_fonts(full=True)}, page

    def test_bundled_copy_of_the_original_typeface_is_not_reported_as_substituted(self):
        _require_bundled("montserrat")
        substituted, fonts, _page_ = self._edit("Montserrat-Regular", "Salut le monde")
        self.assertFalse(substituted)
        self.assertTrue(any("Montserrat" in f for f in fonts), fonts)

    def test_metric_clone_of_a_proprietary_font_is_reported_as_substituted(self):
        _require_bundled("calibri")
        substituted, fonts, _page_ = self._edit("Calibri", "Salut le monde")
        self.assertTrue(substituted)
        self.assertTrue(any("Carlito" in f for f in fonts), fonts)

    def test_characters_missing_from_closer_families_fall_back_to_dejavu(self):
        _require_bundled("verdana")
        # Liberation Sans has no check mark; DejaVu Sans does.
        self.assertFalse(pdf_engine._font_covers_text(pdf_engine._family_font("arial", False, False)[0], "\u2713"))
        _substituted, fonts, page = self._edit("ArialMT", "Validé \u2713")
        self.assertTrue(any("DejaVu" in f for f in fonts), fonts)
        self.assertIn("\u2713", page.get_text())

    def test_coverage_fallback_skips_system_fonts(self):
        # On macOS, "verdana" resolves to the real system Verdana first --
        # which has no check mark either. The coverage tier must go straight
        # to the bundled DejaVu, or the line ends up in Base-14 and loses
        # its Euro sign too.
        _require_bundled("verdana")
        with tempfile.TemporaryDirectory() as fake_system:
            shutil.copy(pdf_engine._family_font("arial", False, False)[0], Path(fake_system) / "Verdana.ttf")
            pdf_engine.fonts._SYSTEM_FONT_DIR = Path(fake_system)
            _substituted, fonts, page = self._edit("Helvetica", "1 234,56 \u20ac \u2713")
        self.assertTrue(any("DejaVu" in f for f in fonts), fonts)
        self.assertIn("\u20ac \u2713", page.get_text())


class UnreadableTextLayerTests(unittest.TestCase):
    """Some PDFs (a real payslip) draw text with fonts that have no
    character map and a ToUnicode table that doesn't match the glyph codes
    drawn: the page looks right, but "Emploi : INGENIEUR SYSTEME" extracts as
    "6T:SVR\\x01...". Editing must not diff against that garbage, and the
    replacement must keep the original's width and fixed pitch."""

    LINE = "Emploi      : INGENIEUR SYSTEME"
    # Same length, spaces read back as U+0001 -- what the payslip extracts as.
    SCRAMBLED = "6T:SVR\x01\x01\x01\x01\x01\x01\x011\x01:!86!:6EB\x01CHCD6 6"

    def _scrambled_block(self, fontname="cour"):
        doc, page = _page(width=400)
        page.insert_text((40, 50), self.LINE, fontsize=10, fontname=fontname)
        blocks = extract_structure(page)
        block = blocks[0]
        line = block.lines[0]
        line.spans[:] = [Span(**{**sp.__dict__, "text": self.SCRAMBLED[: len(sp.text)]}) for sp in line.spans]
        return doc, page, block, blocks

    def test_control_characters_mark_the_text_as_unreliable(self):
        _doc, _page_, block, _blocks = self._scrambled_block()
        self.assertFalse(block.text_reliable)
        _doc, page = _page()
        page.insert_text((40, 50), "Montant : 12,50 €", fontsize=11, fontname="helv")
        self.assertTrue(extract_structure(page)[0].text_reliable)

    def test_fixed_pitch_is_detected_from_character_positions(self):
        for fontname, mono in (("cour", True), ("helv", False)):
            with self.subTest(font=fontname):
                _doc, page = _page(width=400)
                page.insert_text((40, 50), self.LINE, fontsize=10, fontname=fontname)
                span = extract_structure(page)[0].dominant_span
                self.assertEqual(bool(span.flags & pdf_engine.FLAG_MONOSPACE), mono)

    def test_unreliable_line_is_rewritten_whole_at_the_original_width(self):
        doc, page, block, blocks = self._scrambled_block()
        mono = pdf_engine.fonts._family_font("courier new", False, False)[0]
        choice = pdf_engine.FontChoice(fontname="x", fontfile=mono, substituted=True)
        # Measuring the garbage (zero-width control characters) used to
        # stretch the retyped line by ~40 %.
        self.assertAlmostEqual(pdf_engine._metric_match_scale(block.dominant_span, choice), 1.0, delta=0.05)

        apply_block_edit(doc, page, block, "Emploi      : INGENIEUR environnement", all_blocks=blocks)
        self.assertIn("Emploi      : INGENIEUR environnement", page.get_text())

    def test_a_generic_pick_is_reported_as_a_substitution(self):
        # An unnamed fixed-width font gets Courier New: even as a real system
        # file, it is not "the original typeface", so the user is warned.
        with tempfile.TemporaryDirectory() as fake_system:
            shutil.copy(pdf_engine._family_font("courier new", False, False)[0], Path(fake_system) / "Courier New.ttf")
            real = pdf_engine.fonts._SYSTEM_FONT_DIR
            pdf_engine.fonts._SYSTEM_FONT_DIR = Path(fake_system)
            try:
                doc, page, block, _blocks = self._scrambled_block()
                block.lines[0].spans[:] = [Span(**{**sp.__dict__, "font": "font000000003072ff07"}) for sp in block.lines[0].spans]
                choice = pdf_engine.pick_font(doc, page, block, "Emploi : INGENIEUR environnement")
            finally:
                pdf_engine.fonts._SYSTEM_FONT_DIR = real
        self.assertTrue(choice.fontfile.endswith("Courier New.ttf"), choice.fontfile)
        self.assertFalse(choice.same_typeface)


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


class SignaturePlacementTests(unittest.TestCase):
    """`apply_signature` is the same code path whether the source is a
    file the user picked from disk or a PNG the frontend's drawing canvas
    exported -- both arrive as raw bytes with no reliable extension, so
    the type is sniffed from the bytes themselves rather than trusted from
    a filename/content-type."""

    def test_places_a_one_page_pdf_as_vector(self):
        doc, page = _page()
        sig_doc = pymupdf.open()
        sig_doc.new_page(width=200, height=80)
        sig_bytes = sig_doc.tobytes()

        bbox = apply_signature(doc, page, sig_bytes, (50.0, 60.0, 150.0, 90.0))

        self.assertEqual(bbox, (50.0, 60.0, 150.0, 90.0))
        # A page was actually embedded (an XObject/form for the placed PDF
        # page), not just silently a no-op.
        self.assertGreater(len(doc[0].get_xobjects()), 0)

    def test_places_a_png(self):
        doc, page = _page()
        png_doc = pymupdf.open()
        png_page = png_doc.new_page(width=200, height=80)
        png_page.draw_line((10, 60), (190, 20))
        png_bytes = png_page.get_pixmap().tobytes("png")

        bbox = apply_signature(doc, page, png_bytes, (50.0, 60.0, 150.0, 90.0))

        self.assertEqual(bbox, (50.0, 60.0, 150.0, 90.0))
        self.assertGreater(len(doc[0].get_images()), 0)

    def test_rejects_unrecognized_bytes(self):
        doc, page = _page()
        with self.assertRaises(UnsupportedSignatureFileError):
            apply_signature(doc, page, b"definitely not a pdf or image", (0.0, 0.0, 10.0, 10.0))

    def test_rejects_password_protected_pdf(self):
        doc, page = _page()
        sig_doc = pymupdf.open()
        sig_doc.new_page(width=200, height=80)
        sig_bytes = sig_doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")

        with self.assertRaises(UnsupportedSignatureFileError):
            apply_signature(doc, page, sig_bytes, (0.0, 0.0, 10.0, 10.0))


if __name__ == "__main__":
    unittest.main()


def _all_stream_bytes(pdf: bytes) -> bytes:
    """Every (decompressed) stream of a PDF, to check that removed text is
    really gone from the file, not just from the page."""
    doc = pymupdf.open(stream=pdf)
    out = []
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_is_stream(xref):
                out.append(doc.xref_stream(xref) or b"")
        except Exception:
            pass
    return b"".join(out) + pdf


class CmaplessOriginalFontTests(unittest.TestCase):
    """Real bug: a letter's "Chère Adhérente," was set in a subset font with
    no Unicode cmap (common in Word exports). Editing the end of the line
    kept the untouched start in that font, which can't map characters to
    glyphs: the whole run became a single .notdef box."""

    def _letter(self) -> bytes:
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_font(fontname="lib", fontfile=str(Path(pdf_engine._BUNDLED_FONT_DIR) / "liberation" / "LiberationSans-Regular.ttf"))
        page.insert_text((50, 80), "Chère Adhérente,", fontname="lib", fontsize=12)
        doc = pymupdf.open(stream=doc.tobytes(garbage=3))
        for xref in range(1, doc.xref_length()):
            # A subset name, as Word writes it, so the span's font is found
            # again on the page.
            if doc.xref_get_key(xref, "BaseFont")[0] == "name":
                doc.xref_set_key(xref, "BaseFont", "/EAAAAB+LiberationSans")
            if doc.xref_get_key(xref, "FontName")[0] == "name":
                doc.xref_set_key(xref, "FontName", "/EAAAAB+LiberationSans")
            if doc.xref_get_key(xref, "FontFile2")[0] == "xref":
                stream_xref = int(doc.xref_get_key(xref, "FontFile2")[1].split()[0])
                font = TTFont(io.BytesIO(doc.xref_stream(stream_xref)))
                del font["cmap"]
                font["post"].formatType = 3.0  # no glyph names either, like a real subset
                out = io.BytesIO()
                font.save(out)
                doc.update_stream(stream_xref, out.getvalue())
        return doc.tobytes()

    def test_untouched_run_in_a_cmapless_font_stays_readable(self):
        pdf = self._letter()
        doc = pymupdf.open(stream=pdf)
        self.assertIn("Chère Adhérente,", doc[0].get_text())  # the fixture extracts fine, like the real letter
        block = extract_structure(doc[0])[0]
        apply_block_edit(doc, doc[0], block, "Chère Adhérente, bonjour")
        self.assertIn("Chère Adhérente, bonjour", doc[0].get_text())
        trace = [t for t in doc[0].get_texttrace() if "Adh" in "".join(chr(c[0]) for c in t["chars"])][0]
        self.assertGreater(trace["bbox"][2] - trace["bbox"][0], 50)  # not all glyphs piled up in one box


class RealRemovalTests(unittest.TestCase):
    """Glyph's core promise: what is edited or redacted is gone from the
    FILE, not only from the screen (no copy in an orphaned object, no
    earlier version kept)."""

    def _doc(self):
        doc = pymupdf.open()
        page = doc.new_page(width=400, height=200)
        page.insert_text((40, 50), "IBAN : SECRET-4242", fontsize=11, fontname="cour")
        page.insert_text((40, 80), "Montant : 120,00 EUR", fontsize=11, fontname="cour")
        return doc

    def test_edited_text_is_gone_from_the_file(self):
        src = self._doc().tobytes()
        block = [b for b in extract_structure(pymupdf.open(stream=src)[0]) if "SECRET" in b.text][0]
        _meta, out = pdf_engine.worker_apply_edit(src, 0, block.id, "IBAN : FR76 0000")
        self.assertNotIn(b"SECRET-4242", _all_stream_bytes(out))
        self.assertIn("FR76 0000", pymupdf.open(stream=out)[0].get_text())

    def test_redaction_removes_the_text_and_keeps_the_rest(self):
        src = self._doc().tobytes()
        meta, out = pdf_engine.worker_redact(src, 0, [(35, 38, 220, 54)])
        self.assertEqual(meta["redacted"], 1)
        self.assertNotIn(b"SECRET-4242", _all_stream_bytes(out))
        self.assertIn("Montant : 120,00 EUR", pymupdf.open(stream=out)[0].get_text())

    def test_redaction_ignores_areas_outside_the_page(self):
        meta, _out = pdf_engine.worker_redact(self._doc().tobytes(), 0, [(500, 500, 600, 600)])
        self.assertEqual(meta["redacted"], 0)

    def test_sanitize_strips_metadata_and_xmp(self):
        doc = self._doc()
        doc.set_metadata({"author": "Jean Dupont", "keywords": "IDMATRIC=9410512", "title": "Bulletin"})
        doc.set_xml_metadata('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/></x:xmpmeta>')
        meta, out = pdf_engine.worker_sanitize(doc.tobytes())
        self.assertIn("metadata.author", meta["removed"])
        self.assertIn("metadata.keywords", meta["removed"])
        self.assertIn("xmp", meta["removed"])
        cleaned = pymupdf.open(stream=out)
        self.assertFalse(any(cleaned.metadata.get(k) for k in ("author", "keywords", "title")))
        self.assertFalse(cleaned.get_xml_metadata().strip())
        self.assertNotIn(b"Jean Dupont", out)


class InspectTests(unittest.TestCase):
    """The checker reports what a PDF still hides, without changing it."""

    def _report(self, doc):
        meta, blob = pdf_engine.worker_inspect(doc.tobytes())
        self.assertIsNone(blob)
        return meta

    def test_white_box_overlay_is_detected(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 80), "Ancien montant 1 200", fontsize=12)
        page.draw_rect(pymupdf.Rect(45, 65, 220, 85), color=None, fill=(1, 1, 1))  # drawn AFTER the text
        page.insert_text((50, 80), "Nouveau 900", fontsize=12)
        hidden = self._report(doc)["hidden_text"]
        self.assertTrue(any("Ancien montant" in h["text"] for h in hidden), hidden)

    def test_black_box_fake_redaction_is_detected(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 80), "Numero secret 0612345678", fontsize=12)
        page.draw_rect(pymupdf.Rect(45, 65, 260, 85), color=None, fill=(0, 0, 0))
        self.assertTrue(self._report(doc)["hidden_text"])

    def test_text_under_a_pasted_image_is_detected(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 80), "Numero secret 0612345678", fontsize=12)
        black = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), False)
        black.clear_with(0)
        page.insert_image(pymupdf.Rect(45, 65, 260, 85), pixmap=black)
        self.assertTrue(self._report(doc)["hidden_text"])

    def test_ocr_text_under_a_scanned_page_is_invisible_not_hidden(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 80), "Texte reconnu du scan", fontsize=12)
        scan = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), False)
        scan.clear_with(255)
        page.insert_image(page.rect, pixmap=scan)  # the scan drawn over its OCR text
        report = self._report(doc)
        self.assertEqual(report["hidden_text"], [])
        self.assertGreater(report["invisible_text_chars"], 0)

    def test_transparent_image_over_text_is_not_a_finding(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 80), "Texte sous un tampon", fontsize=12)
        stamp = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), True)
        stamp.clear_with(0)  # fully transparent
        page.insert_image(pymupdf.Rect(45, 65, 260, 85), pixmap=stamp)
        self.assertEqual(self._report(doc)["hidden_text"], [])

    def test_background_drawn_before_the_text_is_not_a_finding(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.draw_rect(pymupdf.Rect(45, 65, 260, 85), color=None, fill=(0.9, 0.9, 1))  # a cell background
        page.insert_text((50, 80), "Texte normal", fontsize=12)
        self.assertEqual(self._report(doc)["hidden_text"], [])

    def test_real_redaction_leaves_nothing_to_find(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 80), "Numero secret 0612345678", fontsize=12)
        _meta, out = pdf_engine.worker_redact(doc.tobytes(), 0, [(45, 65, 260, 85)])
        self.assertEqual(self._report(pymupdf.open(stream=out))["hidden_text"], [])

    def test_unapplied_redaction_marks_and_metadata_are_reported(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 80), "A masquer", fontsize=12)
        page.add_redact_annot(pymupdf.Rect(45, 65, 160, 85), fill=(0, 0, 0))  # marked, never applied
        doc.set_metadata({"author": "Jean Dupont"})
        report = self._report(doc)
        self.assertEqual(report["unapplied_redactions"], 1)
        self.assertEqual(report["metadata"].get("author"), "Jean Dupont")

    def test_earlier_versions_from_incremental_saves_are_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.pdf"
            doc = pymupdf.open()
            doc.new_page().insert_text((50, 80), "Version 1", fontsize=12)
            doc.save(path)
            doc = pymupdf.open(path)
            doc[0].insert_text((50, 120), "Version 2", fontsize=12)
            doc.saveIncr()
            meta, _ = pdf_engine.worker_inspect(path.read_bytes())
        self.assertGreaterEqual(meta["versions"], 2)

    def test_coordinates_must_be_finite(self):
        from pydantic import ValidationError

        from app.schemas import RedactRequest

        with self.assertRaises(ValidationError):
            RedactRequest(rects=[(0, 0, float("nan"), 10)])


class ReplaceTests(unittest.TestCase):
    """Find & replace is a series of ordinary line edits: the old text is
    really gone, untouched lines stay untouched."""

    def _doc(self, pages: list[list[str]]) -> bytes:
        doc = pymupdf.open()
        for lines in pages:
            page = doc.new_page()
            for i, text in enumerate(lines):
                page.insert_text((50, 80 + i * 24), text, fontsize=12)
        return doc.tobytes()

    def _replace_all(self, pdf: bytes, find: str, replacement: str, match_case=False, whole_word=False) -> tuple[bytes, int]:
        found, _ = pdf_engine.worker_find(pdf, find, match_case, whole_word)
        total = 0
        for page_index, _count in found["pages"]:
            meta, pdf = pdf_engine.worker_replace_page(pdf, page_index, find, replacement, match_case, whole_word, 60)
            total += meta["replaced"]
        return pdf, total

    def test_replaces_on_every_page_and_removes_the_old_text(self):
        pdf = self._doc([["Client : Dupont SARL", "Total 1 200"], ["Contact Dupont SARL"], ["Rien ici"]])
        found, _ = pdf_engine.worker_find(pdf, "dupont", False, False)
        self.assertEqual(found["pages"], [[0, 1], [1, 1]])
        out, total = self._replace_all(pdf, "dupont", "Martin")
        self.assertEqual(total, 2)
        doc = pymupdf.open(stream=out)
        self.assertIn("Client : Martin SARL", doc[0].get_text())
        self.assertIn("Total 1 200", doc[0].get_text())
        self.assertIn("Contact Martin SARL", doc[1].get_text())
        self.assertNotIn(b"Dupont", _all_stream_bytes(out))

    def test_replacement_containing_the_search_text_does_not_loop(self):
        pdf = self._doc([["Dupont et Dupont", "Dupont"]])
        out, total = self._replace_all(pdf, "Dupont", "Dupont-Martin", match_case=True)
        self.assertEqual(total, 3)
        text = pymupdf.open(stream=out)[0].get_text()
        self.assertEqual(text.count("Dupont-Martin"), 3)

    def test_match_case_and_whole_word(self):
        search = pdf_engine.compile_search("jean", match_case=False, whole_word=True)
        self.assertEqual(pdf_engine.replace_in_text("Jean, Jeanne et JEAN", search, "Paul", False), ("Paul, Jeanne et Paul", 2))
        search = pdf_engine.compile_search("Jean", match_case=True, whole_word=False)
        self.assertEqual(pdf_engine.replace_in_text("Jean JEAN Jeanne", search, "Paul", True), ("Paul JEAN Paulne", 2))

    def test_ligatures_and_special_spaces_are_found(self):
        search = pdf_engine.compile_search("le fichier", match_case=False, whole_word=False)
        self.assertEqual(pdf_engine.replace_in_text("Le ﬁchier", search, "Ce document", False), ("Ce document", 1))
        # A match that would cut a ligature in half is left alone.
        search = pdf_engine.compile_search("f", match_case=False, whole_word=False)
        self.assertEqual(pdf_engine.replace_in_text("ﬁn", search, "X", False), ("ﬁn", 0))

    def test_accents_match_whether_composed_or_not(self):
        composed = pdf_engine.compile_search("Chère", match_case=False, whole_word=False)
        self.assertEqual(pdf_engine.replace_in_text("Che\u0300re Adhérente", composed, "Albatard", False), ("Albatard Adhérente", 1))
        decomposed = pdf_engine.compile_search("Che\u0300re", match_case=False, whole_word=False)
        self.assertEqual(pdf_engine.replace_in_text("Chère Adhérente", decomposed, "Albatard", False), ("Albatard Adhérente", 1))
        # "e" must not match the "e" of a decomposed "è" and strip its accent.
        plain = pdf_engine.compile_search("Che", match_case=False, whole_word=False)
        self.assertEqual(pdf_engine.replace_in_text("Che\u0300re", plain, "X", False), ("Che\u0300re", 0))

    def test_line_breaks_are_rejected(self):
        from pydantic import ValidationError

        from app.schemas import ReplaceRequest

        with self.assertRaises(ValidationError):
            ReplaceRequest(find="a\nb", replace="c")
        with self.assertRaises(ValidationError):
            ReplaceRequest(find="a", replace="b\nc")
        with self.assertRaises(ValidationError):
            ReplaceRequest(find="", replace="c")

    def test_route_makes_one_undo_step(self):
        from app import documents, main
        from app.schemas import ReplaceRequest

        document_id = documents.create(self._doc([["Dupont"], ["Dupont"]]))
        try:
            res = main.replace(document_id, ReplaceRequest(find="Dupont", replace="Martin"))
            self.assertEqual((res.replaced, res.pages, res.truncated), (2, [1, 2], False))
            self.assertFalse(main.undo(document_id).can_undo)
        finally:
            documents.delete(document_id)

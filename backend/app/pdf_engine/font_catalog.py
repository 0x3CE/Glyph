"""Catalog of the free font families bundled under `app/fonts/`.

Single source of truth for two consumers:

- `fonts.py`, at runtime: maps the font name found in a PDF (e.g.
  "ABCDEF+Calibri-Bold") to a bundled family through `aliases`, then to
  a file on disk for the requested bold/italic style.
- `scripts/fetch_fonts.py`, offline: downloads every family's files from
  its declared `source`. The files themselves are committed to the repo
  (the backend must work offline and identically on every machine), the
  script only documents provenance and makes refreshing/adding them
  reproducible.

Two kinds of entries:

- `same_typeface=True`: the bundled file IS the original typeface (a
  PDF made with Montserrat gets the real Montserrat back). Using it is not
  a "substitution" from the user's point of view.
- `same_typeface=False`: a free stand-in for a proprietary font,
  metric-compatible whenever one exists (Carlito <-> Calibri, Liberation
  Sans <-> Arial, Nimbus Sans Narrow <-> Arial/Helvetica Narrow, Gelasio
  <-> Georgia, ...): same advance width glyph for glyph, so edited text
  reflows exactly like the original would have.

Every bundled family is licensed for redistribution (SIL OFL, Apache 2.0,
Ubuntu Font Licence, GUST, Bitstream Vera, or AGPL with font exception for
URW base35); each directory carries its own license file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

Style = tuple[bool, bool]  # (bold, italic)
REGULAR: Style = (False, False)
BOLD: Style = (True, False)
ITALIC: Style = (False, True)
BOLD_ITALIC: Style = (True, True)
STYLES: tuple[Style, ...] = (REGULAR, BOLD, ITALIC, BOLD_ITALIC)
STYLE_SUFFIX = {REGULAR: "Regular", BOLD: "Bold", ITALIC: "Italic", BOLD_ITALIC: "BoldItalic"}


@dataclass(frozen=True)
class GoogleSource:
    """Static TTF instances served by the Google Fonts CSS API."""

    family: str  # exact Google Fonts family name, e.g. "Source Sans 3"


@dataclass(frozen=True)
class UrlSource:
    """Individual files at stable URLs (style -> url), plus a license URL."""

    urls: dict[Style, str]
    license_url: str


@dataclass(frozen=True)
class ZipSource:
    """Files extracted from a release archive (style -> member path)."""

    url: str
    members: dict[Style, str]
    license_member: str | None = None
    license_url: str | None = None


@dataclass(frozen=True)
class FontFamily:
    key: str  # canonical family name, also the key `_SYSTEM_FAMILIES` uses
    category: str  # "sans" | "serif" | "mono" | "display"
    directory: str  # under app/fonts/
    files: dict[Style, str]  # style -> filename (missing styles degrade, see fonts.py)
    aliases: tuple[str, ...]  # normalized font-name needles, see `match_family`
    same_typeface: bool
    source: GoogleSource | UrlSource | ZipSource | None = None  # None = committed to the repo
    license_file: str = "LICENSE"
    # Family to use instead when this one's files aren't on disk (not
    # fetched): a committed one, so a common family never drops to a generic.
    fallback: str | None = None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _google(name: str, category: str, *extra_aliases: str, key: str | None = None, same_typeface: bool = True) -> FontFamily:
    slug = _slug(name)
    prefix = re.sub(r"[^A-Za-z0-9]", "", name)
    return FontFamily(
        key=key or name.lower(),
        category=category,
        directory=slug,
        files={style: f"{prefix}-{STYLE_SUFFIX[style]}.ttf" for style in STYLES},
        aliases=(slug, *extra_aliases),
        same_typeface=same_typeface,
        source=GoogleSource(name),
    )


# Sources are pinned to fixed commits/releases; on top of that, every file's
# exact URL and SHA-256 are recorded in scripts/fonts.lock.json, which is
# what the build actually installs from.
_URW = "https://raw.githubusercontent.com/ArtifexSoftware/urw-base35-fonts/3c0ba3b5687632dfc66526544a4e811fe0ec0cd9/fonts/"
_URW_LICENSE = _URW + "COPYING"


def _urw(key: str, category: str, files: dict[Style, str], *aliases: str, fallback: str | None = None) -> FontFamily:
    return FontFamily(
        fallback=fallback,
        key=key,
        category=category,
        directory="urw",
        files=files,
        aliases=aliases,
        same_typeface=False,
        source=UrlSource({style: _URW + f for style, f in files.items()}, _URW_LICENSE),
        license_file="COPYING",
    )


_DEJAVU_ZIP = "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip"


def _dejavu(key: str, category: str, files: dict[Style, str], *aliases: str, same_typeface: bool) -> FontFamily:
    return FontFamily(
        key=key,
        category=category,
        directory="dejavu",
        files=files,
        aliases=aliases,
        same_typeface=same_typeface,
        source=ZipSource(
            _DEJAVU_ZIP,
            {style: f"dejavu-fonts-ttf-2.37/ttf/{f}" for style, f in files.items()},
            license_member="dejavu-fonts-ttf-2.37/LICENSE",
        ),
    )


_CTAN_LM = "https://mirrors.ctan.org/fonts/lm/fonts/opentype/public/lm/"
_LM_LICENSE = "https://mirrors.ctan.org/fonts/lm/doc/fonts/lm/GUST-FONT-LICENSE.TXT"


def _latin_modern(key: str, category: str, files: dict[Style, str], *aliases: str) -> FontFamily:
    return FontFamily(
        key=key,
        category=category,
        directory="latinmodern",
        files=files,
        aliases=aliases,
        same_typeface=True,  # Latin Modern is Computer Modern, extended
        source=UrlSource({style: _CTAN_LM + f for style, f in files.items()}, _LM_LICENSE),
    )


def _liberation(key: str, category: str, prefix: str, *aliases: str) -> FontFamily:
    return FontFamily(
        key=key,
        category=category,
        directory="liberation",
        files={style: f"{prefix}-{STYLE_SUFFIX[style]}.ttf" for style in STYLES},
        aliases=aliases,
        same_typeface=False,
    )


CATALOG: tuple[FontFamily, ...] = (
    # --- Metric-compatible stand-ins for proprietary fonts -----------------
    _liberation("arial", "sans", "LiberationSans", "arial", "liberationsans", "arimo"),
    _liberation("times new roman", "serif", "LiberationSerif", "timesnewroman", "times", "liberationserif", "tinos"),
    # Courier / Courier New: Nimbus Mono PS (URW's Courier clone) rather than
    # Liberation Mono. Both have Courier's exact 0.6 em pitch, but Liberation
    # Mono's strokes are much heavier: a retyped payslip line stood out as
    # "bold" next to its thin Courier neighbours in production (Linux, where
    # the real Courier New isn't available). Liberation Mono stays as the
    # committed fallback.
    _urw("courier new", "mono", {
        REGULAR: "NimbusMonoPS-Regular.ttf", BOLD: "NimbusMonoPS-Bold.ttf",
        ITALIC: "NimbusMonoPS-Italic.ttf", BOLD_ITALIC: "NimbusMonoPS-BoldItalic.ttf",
    }, "couriernew", "courier", "nimbusmono", "texgyrecursor", fallback="liberation mono"),
    _liberation("liberation mono", "mono", "LiberationMono", "liberationmono", "cousine"),
    _google("Carlito", "sans", "calibri", key="calibri", same_typeface=False),
    _google("Caladea", "serif", "cambria", key="cambria", same_typeface=False),
    _google("Gelasio", "serif", "georgia", key="georgia", same_typeface=False),
    _urw("helvetica", "sans", {
        REGULAR: "NimbusSans-Regular.ttf", BOLD: "NimbusSans-Bold.ttf",
        ITALIC: "NimbusSans-Italic.ttf", BOLD_ITALIC: "NimbusSans-BoldItalic.ttf",
    }, "helvetica", "nimbussans", "texgyreheros"),
    _urw("arial narrow", "sans", {
        REGULAR: "NimbusSansNarrow-Regular.ttf", BOLD: "NimbusSansNarrow-Bold.ttf",
        ITALIC: "NimbusSansNarrow-Oblique.ttf", BOLD_ITALIC: "NimbusSansNarrow-BoldOblique.ttf",
    }, "arialnarrow", "helveticanarrow", "helveticacondensed", "nimbussansnarrow"),
    _urw("palatino", "serif", {
        REGULAR: "P052-Roman.ttf", BOLD: "P052-Bold.ttf",
        ITALIC: "P052-Italic.ttf", BOLD_ITALIC: "P052-BoldItalic.ttf",
    }, "palatino", "bookantiqua", "p052", "texgyrepagella"),
    _urw("bookman", "serif", {
        REGULAR: "URWBookman-Light.ttf", BOLD: "URWBookman-Demi.ttf",
        ITALIC: "URWBookman-LightItalic.ttf", BOLD_ITALIC: "URWBookman-DemiItalic.ttf",
    }, "bookman", "urwbookman", "texgyrebonum"),
    _urw("century schoolbook", "serif", {
        REGULAR: "C059-Roman.ttf", BOLD: "C059-Bold.ttf",
        ITALIC: "C059-Italic.ttf", BOLD_ITALIC: "C059-BdIta.ttf",
    }, "centuryschoolbook", "newcenturyschlbk", "c059", "texgyreschola"),
    _urw("century gothic", "sans", {
        REGULAR: "URWGothic-Book.ttf", BOLD: "URWGothic-Demi.ttf",
        ITALIC: "URWGothic-BookOblique.ttf", BOLD_ITALIC: "URWGothic-DemiOblique.ttf",
    }, "centurygothic", "avantgarde", "urwgothic", "texgyreadventor"),
    _urw("zapf chancery", "display", {
        REGULAR: "Z003-MediumItalic.ttf", ITALIC: "Z003-MediumItalic.ttf",
    }, "zapfchancery", "monotypecorsiva", "z003", "texgyrechorus"),
    _dejavu("verdana", "sans", {
        REGULAR: "DejaVuSans.ttf", BOLD: "DejaVuSans-Bold.ttf",
        ITALIC: "DejaVuSans-Oblique.ttf", BOLD_ITALIC: "DejaVuSans-BoldOblique.ttf",
    }, "verdana", "dejavusans", "bitstreamverasans", "lucidagrande", "lucidasans", same_typeface=False),
    _dejavu("tahoma", "sans", {
        REGULAR: "DejaVuSansCondensed.ttf", BOLD: "DejaVuSansCondensed-Bold.ttf",
        ITALIC: "DejaVuSansCondensed-Oblique.ttf", BOLD_ITALIC: "DejaVuSansCondensed-BoldOblique.ttf",
    }, "tahoma", "dejavusanscondensed", same_typeface=False),
    _dejavu("dejavu serif", "serif", {
        REGULAR: "DejaVuSerif.ttf", BOLD: "DejaVuSerif-Bold.ttf",
        ITALIC: "DejaVuSerif-Italic.ttf", BOLD_ITALIC: "DejaVuSerif-BoldItalic.ttf",
    }, "dejavuserif", "bitstreamveraserif", same_typeface=True),
    _dejavu("dejavu sans mono", "mono", {
        REGULAR: "DejaVuSansMono.ttf", BOLD: "DejaVuSansMono-Bold.ttf",
        ITALIC: "DejaVuSansMono-Oblique.ttf", BOLD_ITALIC: "DejaVuSansMono-BoldOblique.ttf",
    }, "dejavusansmono", "bitstreamverasansmono", "lucidaconsole", "menlo", same_typeface=True),
    FontFamily(
        key="segoe ui",
        category="sans",
        directory="selawik",
        files={REGULAR: "selawk.ttf", BOLD: "selawkb.ttf"},
        aliases=("segoe", "selawik"),
        same_typeface=False,
        source=ZipSource(
            "https://github.com/microsoft/Selawik/releases/download/1.01/Selawik_Release.zip",
            {REGULAR: "selawk.ttf", BOLD: "selawkb.ttf"},
            license_url="https://raw.githubusercontent.com/microsoft/Selawik/89362e84731d1f5777fa078fd4d5ebbd339e4378/LICENSE.txt",
        ),
    ),
    _google("EB Garamond", "serif", "garamond", "ebgaramond"),
    _google("Libre Baskerville", "serif", "baskerville"),
    _google("Libre Franklin", "sans", "franklingothic", "franklin"),
    _google("Libre Bodoni", "serif", "bodoni"),
    _google("Jost", "sans", "futura"),
    _google("Inconsolata", "mono", "consolas"),
    _google("Comic Neue", "display", "comicsans"),
    _google("Courier Prime", "mono"),
    # --- LaTeX ---------------------------------------------------------------
    _latin_modern("latin modern roman", "serif", {
        REGULAR: "lmroman10-regular.otf", BOLD: "lmroman10-bold.otf",
        ITALIC: "lmroman10-italic.otf", BOLD_ITALIC: "lmroman10-bolditalic.otf",
    }, "lmroman", "latinmodernroman", "cmr", "cmbx", "cmti", "cmsl", "sfrm", "sfbx", "sfti"),
    _latin_modern("latin modern sans", "sans", {
        REGULAR: "lmsans10-regular.otf", BOLD: "lmsans10-bold.otf",
        ITALIC: "lmsans10-oblique.otf", BOLD_ITALIC: "lmsans10-boldoblique.otf",
    }, "lmsans", "latinmodernsans", "cmss", "sfss"),
    _latin_modern("latin modern mono", "mono", {
        REGULAR: "lmmono10-regular.otf", BOLD: "lmmonolt10-bold.otf",
        ITALIC: "lmmono10-italic.otf", BOLD_ITALIC: "lmmonolt10-boldoblique.otf",
    }, "lmmono", "latinmodernmono", "cmtt", "sftt"),
    # --- Google Fonts: sans-serif ---------------------------------------------
    FontFamily(
        key="open sans",
        category="sans",
        directory="opensans",
        files={style: f"OpenSans-{STYLE_SUFFIX[style]}.ttf" for style in STYLES},
        aliases=("opensans",),
        same_typeface=True,
        source=None,  # committed: the Type3 weight matching depends on these exact files
    ),
    _google("Roboto", "sans"),
    _google("Roboto Condensed", "sans"),
    _google("Roboto Flex", "sans"),
    _google("Lato", "sans"),
    _google("Montserrat", "sans"),
    _google("Poppins", "sans"),
    _google("Raleway", "sans"),
    _google("Inter", "sans"),
    _google("Inter Tight", "sans"),
    _google("Nunito", "sans"),
    _google("Nunito Sans", "sans"),
    _google("Source Sans 3", "sans", "sourcesanspro", "sourcesans"),
    _google("Noto Sans", "sans"),
    _google("Noto Sans Display", "sans"),
    _google("PT Sans", "sans"),
    _google("PT Sans Narrow", "sans"),
    _google("Ubuntu", "sans"),
    _google("Ubuntu Condensed", "sans"),
    _google("Work Sans", "sans"),
    _google("Rubik", "sans"),
    _google("Fira Sans", "sans"),
    _google("Fira Sans Condensed", "sans"),
    _google("IBM Plex Sans", "sans"),
    _google("IBM Plex Sans Condensed", "sans"),
    _google("Quicksand", "sans"),
    _google("Barlow", "sans"),
    _google("Barlow Condensed", "sans"),
    _google("Barlow Semi Condensed", "sans"),
    _google("Mulish", "sans", "muli"),
    _google("DM Sans", "sans"),
    _google("Manrope", "sans"),
    _google("Karla", "sans"),
    _google("Cabin", "sans"),
    _google("Archivo", "sans"),
    _google("Archivo Narrow", "sans"),
    _google("Heebo", "sans"),
    _google("Titillium Web", "sans"),
    _google("Josefin Sans", "sans"),
    _google("Exo 2", "sans"),
    _google("Hind", "sans"),
    _google("Oswald", "sans"),
    _google("Questrial", "sans"),
    _google("Varela Round", "sans"),
    _google("Assistant", "sans"),
    _google("Overpass", "sans"),
    _google("Outfit", "sans"),
    _google("Plus Jakarta Sans", "sans"),
    _google("Lexend", "sans"),
    _google("Figtree", "sans"),
    _google("Red Hat Display", "sans"),
    _google("Red Hat Text", "sans"),
    _google("Kanit", "sans"),
    _google("Space Grotesk", "sans"),
    _google("Public Sans", "sans"),
    _google("Signika", "sans"),
    _google("Asap", "sans"),
    _google("Catamaran", "sans"),
    _google("Prompt", "sans"),
    _google("Sora", "sans"),
    _google("Urbanist", "sans"),
    _google("Encode Sans", "sans"),
    _google("Abel", "sans"),
    _google("Dosis", "sans"),
    _google("Comfortaa", "sans"),
    _google("Maven Pro", "sans"),
    _google("Merriweather Sans", "sans"),
    _google("Hanken Grotesk", "sans"),
    _google("Schibsted Grotesk", "sans"),
    _google("Albert Sans", "sans"),
    _google("Onest", "sans"),
    _google("Geologica", "sans"),
    _google("Tenor Sans", "sans"),
    _google("Didact Gothic", "sans"),
    _google("Arsenal", "sans"),
    _google("Istok Web", "sans"),
    _google("Cantarell", "sans"),
    _google("Oxygen", "sans"),
    _google("Atkinson Hyperlegible", "sans"),
    _google("Instrument Sans", "sans"),
    _google("Be Vietnam Pro", "sans"),
    _google("Chivo", "sans"),
    _google("Saira", "sans"),
    _google("Teko", "sans"),
    _google("Yanone Kaffeesatz", "sans"),
    _google("Pathway Gothic One", "sans"),
    # --- Google Fonts: serif ----------------------------------------------------
    _google("Merriweather", "serif"),
    _google("Playfair Display", "serif"),
    _google("Playfair", "serif"),
    _google("Lora", "serif"),
    _google("PT Serif", "serif"),
    _google("Noto Serif", "serif"),
    _google("Noto Serif Display", "serif"),
    _google("Source Serif 4", "serif", "sourceserifpro", "sourceserif"),
    _google("Cormorant Garamond", "serif"),
    _google("Cormorant", "serif"),
    _google("Crimson Text", "serif", "crimson"),
    _google("Crimson Pro", "serif"),
    _google("Bitter", "serif"),
    _google("Arvo", "serif"),
    _google("Zilla Slab", "serif"),
    _google("Roboto Slab", "serif"),
    _google("Roboto Serif", "serif"),
    _google("Alegreya", "serif"),
    _google("Cardo", "serif"),
    _google("Old Standard TT", "serif"),
    _google("Spectral", "serif"),
    _google("Domine", "serif"),
    _google("Noticia Text", "serif"),
    _google("Vollkorn", "serif"),
    _google("IBM Plex Serif", "serif"),
    _google("DM Serif Display", "serif"),
    _google("DM Serif Text", "serif"),
    _google("Frank Ruhl Libre", "serif"),
    _google("Prata", "serif"),
    _google("Literata", "serif"),
    _google("Newsreader", "serif"),
    _google("Fraunces", "serif"),
    _google("Josefin Slab", "serif"),
    _google("Rokkitt", "serif"),
    _google("Libre Caslon Text", "serif", "caslon"),
    _google("Sorts Mill Goudy", "serif", "goudy"),
    _google("Gilda Display", "serif"),
    _google("Marcellus", "serif"),
    _google("Cinzel", "serif", "trajan"),
    _google("Yeseva One", "serif"),
    _google("Abril Fatface", "serif"),
    _google("Alfa Slab One", "serif"),
    _google("Ibarra Real Nova", "serif"),
    _google("Bodoni Moda", "serif"),
    _google("Instrument Serif", "serif"),
    _google("Young Serif", "serif"),
    _google("Brygada 1918", "serif"),
    _google("Petrona", "serif"),
    # --- Google Fonts: monospace ------------------------------------------------
    _google("Roboto Mono", "mono"),
    _google("Source Code Pro", "mono"),
    _google("Fira Code", "mono"),
    _google("Fira Mono", "mono"),
    _google("IBM Plex Mono", "mono"),
    _google("JetBrains Mono", "mono"),
    _google("Space Mono", "mono"),
    _google("Ubuntu Mono", "mono"),
    _google("DM Mono", "mono"),
    _google("Anonymous Pro", "mono"),
    _google("Noto Sans Mono", "mono"),
    _google("Overpass Mono", "mono"),
    _google("Red Hat Mono", "mono"),
    _google("Cutive Mono", "mono"),
    _google("Share Tech Mono", "mono"),
    _google("Azeret Mono", "mono"),
    _google("Martian Mono", "mono"),
    _google("Geist Mono", "mono"),
    _google("Geist", "sans"),
    # --- Google Fonts: display / script / handwriting (Canva-style docs) -------
    _google("Bebas Neue", "display"),
    _google("Anton", "display"),
    _google("Archivo Black", "display"),
    _google("Fjalla One", "display"),
    _google("Righteous", "display"),
    _google("Russo One", "display"),
    _google("Lilita One", "display"),
    _google("Passion One", "display"),
    _google("Bungee", "display"),
    _google("Chewy", "display"),
    _google("Lobster", "display"),
    _google("Pacifico", "display"),
    _google("Dancing Script", "display"),
    _google("Great Vibes", "display"),
    _google("Caveat", "display"),
    _google("Satisfy", "display"),
    _google("Sacramento", "display"),
    _google("Allura", "display"),
    _google("Parisienne", "display"),
    _google("Kaushan Script", "display"),
    _google("Alex Brush", "display"),
    _google("Courgette", "display"),
    _google("Cookie", "display"),
    _google("Shadows Into Light", "display"),
    _google("Permanent Marker", "display"),
    _google("Indie Flower", "display"),
    _google("Amatic SC", "display"),
    _google("Patrick Hand", "display"),
    _google("Architects Daughter", "display"),
    _google("Gloria Hallelujah", "display"),
    _google("Homemade Apple", "display"),
    _google("Mrs Saint Delafield", "display"),
    _google("Pinyon Script", "display"),
    _google("Tangerine", "display"),
    _google("Playball", "display"),
    _google("Yellowtail", "display"),
    _google("Marck Script", "display"),
    _google("Nothing You Could Do", "display"),
    _google("Reenie Beanie", "display"),
    _google("Rock Salt", "display"),
    _google("La Belle Aurore", "display"),
    _google("Monsieur La Doulaise", "display"),
    _google("Herr Von Muellerhoff", "display"),
    _google("Kalam", "display"),
    _google("Gochi Hand", "display"),
    _google("Special Elite", "display"),
    _google("Press Start 2P", "display"),
    _google("Black Ops One", "display"),
    _google("Audiowide", "display"),
    _google("Orbitron", "display"),
    _google("Monoton", "display"),
    _google("Bangers", "display"),
    _google("Luckiest Guy", "display"),
    _google("Fredoka", "display"),
    _google("Baloo 2", "display"),
    _google("Sniglet", "display"),
    _google("Staatliches", "display"),
    _google("League Spartan", "sans"),
    _google("League Gothic", "display"),
    _google("Six Caps", "display"),
)

BY_KEY: dict[str, FontFamily] = {family.key: family for family in CATALOG}

# Wide-coverage families tried last, by category, when every closer match
# lacks a character the new text needs (Greek, Cyrillic, math symbols, ...).
COVERAGE_FALLBACK: dict[str, str] = {
    "sans": "verdana",  # DejaVu Sans
    "serif": "dejavu serif",
    "mono": "dejavu sans mono",
}


def _build_alias_index() -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for family in CATALOG:
        for needle in family.aliases:
            seen.setdefault(needle, family.key)
    # Longest needle first: "robotomono" must win over "roboto",
    # "arialnarrow" over "arial", "cormorantgaramond" over "garamond".
    return sorted(seen.items(), key=lambda item: len(item[0]), reverse=True)


_ALIAS_INDEX = _build_alias_index()


def match_family(normalized_name: str) -> str | None:
    """Family key for a normalized PDF font name, or None if unknown.

    Needles of 6+ characters match anywhere in the name (designer names
    are often prefixed: "ITCFranklinGothic", "AdobeGaramondPro",
    "NeueHaasHelvetica"); shorter ones only as a prefix, so "inter" or
    "cmr" don't fire inside an unrelated longer name ("printer...",
    "arcmregular").
    """
    for needle, key in _ALIAS_INDEX:
        if normalized_name.startswith(needle) or (len(needle) >= 6 and needle in normalized_name):
            return key
    return None

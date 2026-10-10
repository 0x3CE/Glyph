# Glyph

Glyph edits text directly inside a PDF's content stream instead of drawing a patch on top of it. When you edit a line, the original glyphs are actually removed (via PDF redaction) and the new text is re-inserted in their place — not covered by a white rectangle with new text stacked over it.

It's a small, focused, open-source tool: no accounts, no ads, no visitor tracking (the hosted site only collects anonymous, cookie-free page views and page-load performance through Vercel Web Analytics and Speed Insights). Editing does **not** happen in your browser: the PDF is sent to Glyph's backend server, which processes it in memory only — never written to disk — and deletes it when you close the tab, or after 30 minutes of inactivity. If you self-host, that server is yours.

## How it works

1. Open a PDF (uploaded to the backend server, kept in its memory only).
2. Click a line of text — an editor appears exactly where it is. Editing is always per line, including a field that visually spans several lines (an address, say) — see "Known limitations" below.
3. Change the text and save.
4. The backend removes the original glyphs (real redaction, not an overlay) and re-inserts the new text using the original font if it covers all the needed characters, or the same family from Glyph's bundled catalog of ~240 free fonts otherwise (Roboto, Montserrat, Lato, Merriweather…), or a metric-compatible free clone for proprietary fonts (Calibri → Carlito, Arial → Liberation Sans, Arial Narrow → Nimbus Sans Narrow…), with metric compensation (you'll see a warning banner when the result isn't the original typeface). If the line mixes styles (a bold word inside an otherwise plain sentence, say), Glyph diffs your edit against the original and keeps that word's exact original formatting wherever the surrounding edit left it untouched, instead of collapsing the whole line to one font (see `docs/DECISIONS.md`).
5. Add a signature: draw one on a canvas, or import a file (PDF, PNG, or JPEG), then drag/resize it into place. A PDF signature is embedded as vector (crisp at any zoom); an image is stamped as-is.
6. Redact: tap lines or draw areas, then apply. Everything under them is deleted from the file (text, image pixels, shapes fully inside), not covered by a black box. "Remove metadata" strips the info dictionary, XMP, attachments, JavaScript, invisible text and thumbnails, and rewrites the whole file.
7. Find and replace a word across the whole document: each matching line is edited exactly like a manual edit, and the whole replacement is one undo step.
8. Undo/redo walk through the document's version history (kept server-side).
9. Download the result whenever you like.

A separate **redacted-PDF checker** (`/verifier-pdf-caviarde`, `/en/check-redacted-pdf`) reports, without storing or changing the file, what a PDF still hides: text covered by a shape or image drawn after it (fake redactions, white-box "edits"), redactions marked but never applied, invisible text, metadata, earlier versions kept by incremental saves, attachments.

Besides the landing page and the editor, the site has a small set of **content pages** (one per tool, a few guides and an article, plus terms of use), each in both languages with its own translated slug. They're plain data in `lib/seo/content/`, registered in `lib/seo/registry.ts`; a page gets a route, a sitemap entry and live internal links only once its content is listed in `lib/seo/content/index.ts`.

The site (landing page and editor) is in **French and English**. French lives at `/` and `/editor`, English at `/en` and `/en/editor`. On a first visit, `proxy.ts` picks the language from the visitor's country (French for France, its overseas territories and Monaco; English everywhere else), using the `x-vercel-ip-country` header Vercel adds — no IP is read or stored. A FR/EN switch in the header overrides that guess and is remembered in a `glyph-lang` cookie. Search engine crawlers are never redirected, so both versions stay indexed (with `hreflang` links between them).

## Getting started

Backend (Python / FastAPI / PyMuPDF):

```bash
cd backend
python3 -m venv .venv        # once
.venv/bin/pip install -r requirements.txt   # once
.venv/bin/python scripts/fetch_fonts.py     # once: downloads the bundled font catalog (~95 MB)
.venv/bin/uvicorn app.main:app --port 8000 --reload
```

Frontend (Next.js, proxies `/api` to the backend via `next.config.ts`):

```bash
npm install
npm run dev
```

Open <http://localhost:3000/editor>.

### Configuration

Both sides read a few optional environment variables — useful once you deploy the backend and frontend separately (e.g. backend on Render, frontend on Vercel) instead of running both on `localhost`.

| Variable | Where | Default | Purpose |
| --- | --- | --- | --- |
| `BACKEND_URL` | frontend | `http://localhost:8000` | Where `/api/*` gets proxied to (`next.config.ts`). |
| `ALLOWED_ORIGINS` | backend | `http://localhost:3000` | Comma-separated CORS allowlist. Set to your deployed frontend URL. |
| `MAX_UPLOAD_MB` | backend | `20` | Upload size cap. |
| `MAX_SIGNATURE_MB` | backend | `5` | Signature file size cap (drawn signatures are small PNGs and rarely get close to this). |
| `SANDBOX_MAX_MEMORY_MB` / `SANDBOX_MAX_CPU_SECONDS` / `SANDBOX_TIMEOUT_SECONDS` | backend | `512` / `8` / `15` | Limits applied to the isolated subprocess that parses each PDF (see below). |
| `SANDBOX_MAX_CONCURRENCY` / `SANDBOX_QUEUE_TIMEOUT_SECONDS` | backend | `2` / `20` | How many of those subprocesses may run at once, and how long a request waits for a free one before getting a `503`. Size it so `SANDBOX_MAX_CONCURRENCY × SANDBOX_MAX_MEMORY_MB` + `STORE_MAX_MB` fits in the instance's RAM. |
| `SANDBOX_MAX_RESULT_MB` | backend | `64` | Largest result (re-saved PDF) a subprocess may send back. |
| `DOCUMENT_TTL_MINUTES` | backend | `30` | An open document nobody touched for this long is deleted. |
| `DOCUMENT_MAX_MB` | backend | `60` | Per-document cap on its undo history; the oldest undo states are dropped first. |
| `STORE_MAX_MB` / `MAX_DOCUMENTS` | backend | `200` / `200` | Caps on everything held in memory; past them, new uploads/edits get a `503` instead of evicting someone else's document. |
| `MAX_CONCURRENT_UPLOADS` | backend | `4` | Upload-type requests (upload, checker, signature) processed at once, since each body is held in memory; others wait up to 10 s, then get a `503`. |
| `ENABLE_API_DOCS` | backend | unset | Set to `1` to serve FastAPI's `/docs` and `/openapi.json` (local development). Off by default, so off in production. |
| `MAX_DOCUMENTS_PER_OWNER` | backend | `10` | Documents one visitor (one IP, taken from the left-most `X-Forwarded-For` entry that Vercel sets) can have open at once; past it, uploads get a `429`. Only an HMAC of the IP, keyed at startup, is kept in memory. |
| `NEXT_PUBLIC_SITE_URL` | frontend | Vercel production URL | Public origin used for canonical URLs, hreflang, Open Graph images, sitemap and robots.txt (`lib/site.ts`). Set it once a custom domain is attached; without it, Vercel's production domain (`VERCEL_PROJECT_PRODUCTION_URL`) is used, and `http://localhost:3000` outside Vercel. |

## Deployment

Frontend and backend deploy as two separate services — there's no requirement to use these specific providers, but this is the tested path:

**Backend on [Render](https://render.com)**, from `backend/Dockerfile`:

1. New Web Service → connect this repo → Render picks up `render.yaml` (Blueprint) automatically, or point it at `backend/Dockerfile` manually if you'd rather configure it by hand.
2. Set `ALLOWED_ORIGINS` to your Vercel URL once you have it (step below) — the placeholder in `render.yaml` is intentionally left blank.
3. Note the resulting service URL (`https://<something>.onrender.com`).

**Frontend on [Vercel](https://vercel.com)**, zero-config for Next.js:

1. New Project → import this repo (Vercel auto-detects Next.js, no build settings to change).
2. Set the `BACKEND_URL` environment variable to the Render URL from above.
3. Once a custom domain is attached, set `NEXT_PUBLIC_SITE_URL` to it (e.g. `https://glyph-pdf.com`) so canonical URLs, the sitemap and share previews use it; until then, Vercel's production domain is used automatically.
4. Redeploy after setting env vars (Vercel doesn't hot-reload them into a running build).

Then go back to Render and set `ALLOWED_ORIGINS` to the Vercel URL from step 2, so the backend's CORS allowlist matches — the two services reference each other's URLs, so the first deploy of each will need one follow-up env var update once the other's URL is known.

The backend has no database and keeps everything in the web service's own memory (see `docs/ARCHITECTURE.md`) — Render's free/starter tiers that spin a service down on idle will lose all in-progress documents on the next cold start. Fine for the tool's intended use (open a PDF, edit it, download it, done), not a place to expect long-lived state.

## Project structure

```text
app/[lang]/     # Next.js routes per language (home page, /editor, content pages [slug], OG image, 404)
app/            # sitemap, robots, icon, global styles
proxy.ts        # language routing: /en prefix, country-based first visit, cookie
components/     # PdfPage (render + edit + redaction), EditorApp (editor screen), SeoPage (content pages), PdfChecker, ReplaceModal…
lib/            # API client, shared types, pdf.js setup
lib/i18n/       # fr.ts / en.ts dictionaries, locale config, hreflang helpers
lib/seo/        # content pages: registry (ids, kinds, slugs per language) and content
backend/        # FastAPI + PyMuPDF (the actual editing engine)
  app/fonts/    # bundled free fonts (only Liberation + Open Sans are committed)
  scripts/      # fetch_fonts.py: downloads the rest of the font catalog
```

## Documentation

- [`docs/HANDOFF.md`](./docs/HANDOFF.md) — start here to pick the project up or fork it: setup, architecture, engine rules, fonts, security, deployment, known pitfalls (in French).
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — how the frontend and backend fit together.
- [`docs/API.md`](./docs/API.md) — backend route reference.
- [`docs/DECISIONS.md`](./docs/DECISIONS.md) — the real bugs behind the editing engine's design choices, and why each workaround exists. Good starting point before touching `backend/app/pdf_engine/`.

## Known limitations

- **Upload and edit size**: PDFs over 20 MB are rejected, a single edit is capped at 5000 characters, and a signature file over 5 MB is rejected (all configurable, see above).
- **Signature placement doesn't preserve aspect ratio automatically**: the placement box is freely resizable in both dimensions, so a signature can be stretched out of proportion if you drag unevenly — nothing currently locks the ratio while resizing.
- **PDF parsing is sandboxed**: every operation touching an uploaded PDF runs in a short-lived, resource-limited subprocess (see [`docs/DECISIONS.md`](./docs/DECISIONS.md#isoler-le-parsing-pdf-dans-un-sous-processus)), since a malformed PDF can crash the underlying C library. At most `SANDBOX_MAX_CONCURRENCY` of them run at once, and nothing they send back is unpickled (raw bytes + JSON only). This adds a small per-request overhead but keeps one bad file from taking down the whole backend. The sandbox is a resource boundary, not a security boundary in the OS sense: the subprocess runs as the same user with the same filesystem/network access.
- **PDFs that hide their text**: some generators (payslips, notably) embed subset fonts with no character map and a `ToUnicode` table that doesn't match the glyph codes the page actually uses (and is incomplete), so the page looks right but its text can't be read back. Glyph detects it (`Block.text_reliable`): the edit field opens empty with an explanation, the line must be retyped in full, and it is rewritten in a fallback font chosen from the measured character spacing (fixed-width or not), at the original width.
- **Language detection needs Vercel**: the country comes from Vercel's `x-vercel-ip-country` header. Without it (local dev, another host), every visitor gets French until they use the switch; the browser's `Accept-Language` isn't used.
- **Server capacity is bounded**: open documents expire after 30 minutes of inactivity, and total memory use is capped (see Configuration). On a full server, uploads get a `503` and should be retried later.
- **Reusing the original font** only works if it exposes a usable Unicode cmap. Most PDFs produced by Word or a virtual printer embed subsetted Identity-H fonts without one. In that (very common) case Glyph falls back, in order, to:
  1. the real proprietary font, if the backend happens to run on macOS (Arial, Arial Narrow, Times New Roman, Courier New, Georgia, Verdana, Tahoma);
  2. the same family from the bundled catalog (`backend/app/pdf_engine/font_catalog.py`): ~240 free families, either the original typeface itself (Google Fonts families, Latin Modern for LaTeX documents, DejaVu) or a metric-compatible clone of a proprietary one: Liberation Sans/Serif (Arial, Times New Roman), Nimbus Mono PS (Courier / Courier New, with Liberation Mono as committed fallback), Carlito (Calibri), Caladea (Cambria), Gelasio (Georgia), Nimbus Sans / Nimbus Sans Narrow (Helvetica, Arial Narrow), P052 (Palatino / Book Antiqua), C059 (Century Schoolbook), URW Gothic (Century Gothic / Avant Garde), URW Bookman, Selawik (Segoe UI), DejaVu Sans (Verdana);
  3. a generic family for the font's category (sans-serif, serif, monospace);
  4. DejaVu, for characters none of the above cover (Greek, Cyrillic, symbols…).

  Metric compensation preserves the original visual width whenever the result isn't the original font. A **Type3-sourced font** (glyphs drawn as arbitrary vector programs, common in some report generators) carries no weight metadata at all. In that case Glyph uses a bundled Open Sans variable font at an empirically chosen weight (see `docs/DECISIONS.md`) rather than guessing.
- **Font catalog size**: the full catalog is ~95 MB. Only Liberation and Open Sans are committed (the guaranteed floor, so the backend never ends up with no font file at all); the rest is downloaded by `backend/scripts/fetch_fonts.py`, which the Docker build runs automatically, from the exact URLs and SHA-256 hashes pinned in `backend/scripts/fonts.lock.json` (a file whose hash doesn't match fails the build). A family that isn't on disk is skipped and the next closest one is used. Fonts outside the catalog, and weights other than regular/bold (Light, Medium, SemiBold…), map to the closest bundled family/style.
- **Editing is per line, deliberately**: a field spanning several visual lines (an address, a multi-line note) is edited one line at a time rather than as a single reflow-capable block. Earlier versions tried to auto-detect "this is one wrapped paragraph" from shared edges/alignment, but real documents kept surfacing independent lines that looked just like a wrapped paragraph by coincidence (a title stacked on a subtitle, a right-aligned column of unrelated values) — merging them let editing one line corrupt another. Per-line editing has no such failure mode. See `docs/DECISIONS.md`.
- **Block overflow**: if you type a manual line break into a field, growing it to more lines than it originally had, it grows downward — but only up to the nearest sibling below, never past it; a field one line tall never grows at all (its font size is reduced instead if the new text is too wide). Editing a block is also clamped against its immediate neighbors on all four sides, so it can never bleed into a sibling's territory even when their bounding boxes already overlap slightly in the source PDF (common with tight line leading or tightly-packed table columns — see `docs/DECISIONS.md`).
- **Colored backgrounds**: redaction clears everything in the edited area, including any vector fill behind the text. Not an issue for typical text blocks (names, dates, paragraphs), but worth knowing if you're editing colored table cells.
- **Password-protected PDFs** are rejected at upload with a clear error — not supported.
- No advanced text shaping (HarfBuzz), no RTL/CJK support, no page rotation — out of scope for now. Free text, form fields, shapes, and OCR aren't implemented yet.
- **Find and replace** works line by line too: a phrase broken across two lines isn't found, and lines with an unreadable text layer are skipped. One run edits at most 20 pages and 300 lines (60 per page, each page in its own sandbox run), over the first 300 pages; the response says `truncated` when there's more.
- **The checker** can't see a box drawn over a scan (the scan's text is pixels), text the same color as its background, or text placed outside the page; it reads the first 300 pages. Text drawn under a page-sized image is reported as invisible (an OCR layer), not as hidden.
- `backend/tests/` covers the block-detection and redaction-safety invariants (`python -m unittest discover -s tests -v`); `backend/smoke_test.py` remains a manual, ad hoc script on top of that, not part of CI.

## Contributing

Issues and pull requests are welcome. If you're planning a non-trivial change to the editing engine, reading `docs/DECISIONS.md` first will save you from re-discovering bugs that are already worked around.

## License

Glyph is free software, released under the [GNU Affero General Public License v3.0](./LICENSE) (AGPL-3.0-only). Copyright © 2026 Glyph contributors.

In short: you can use, study, modify and redistribute it. If you distribute a modified version, **or run one as a network service** (a hosted website, say), you must make its complete source code available to its users under the same license. That matches PyMuPDF, the PDF engine Glyph is built on, which is AGPL-licensed itself.

Versions published before this change remain available under the MIT license they were released with. The bundled fonts keep their own licenses (SIL Open Font License, Apache, GPL with font exception…), shipped next to them in `backend/app/fonts/`.

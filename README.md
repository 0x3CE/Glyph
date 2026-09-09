# Glyph

Glyph edits text directly inside a PDF's content stream instead of drawing a patch on top of it. When you edit a line, the original glyphs are actually removed (via PDF redaction) and the new text is re-inserted in their place — not covered by a white rectangle with new text stacked over it.

It's a small, focused, open-source tool: no accounts, no cloud storage, no tracking. Everything runs locally — your PDF stays in server memory for the duration of your session and is never written to disk.

## How it works

1. Open a PDF (uploaded to the local backend, kept in memory only).
2. Click a line of text — an editor appears exactly where it is. Editing is always per line, including a field that visually spans several lines (an address, say) — see "Known limitations" below.
3. Change the text and save.
4. The backend removes the original glyphs (real redaction, not an overlay) and re-inserts the new text using the original font if it covers all the needed characters, or a close system font with metric compensation otherwise (you'll see a warning banner when that happens).
5. Undo/redo walk through the document's version history (kept server-side).
6. Download the result whenever you like.

## Getting started

Backend (Python / FastAPI / PyMuPDF):

```bash
cd backend
python3 -m venv .venv        # once
.venv/bin/pip install -r requirements.txt   # once
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
| `SANDBOX_MAX_MEMORY_MB` / `SANDBOX_MAX_CPU_SECONDS` / `SANDBOX_TIMEOUT_SECONDS` | backend | `512` / `8` / `15` | Limits applied to the isolated subprocess that parses each PDF (see below). |
| `NEXT_PUBLIC_SITE_URL` | frontend | placeholder | Canonical URL used for SEO metadata once you have a real domain. |

## Project structure

```text
app/            # Next.js routes (home page, /editor, sitemap, robots, OG image)
components/     # PdfPage (render + edit), EditorApp (editor screen), BrandMark
lib/            # API client, shared types, pdf.js setup
backend/        # FastAPI + PyMuPDF (the actual editing engine)
```

## Documentation

- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — how the frontend and backend fit together.
- [`docs/API.md`](./docs/API.md) — backend route reference.
- [`docs/DECISIONS.md`](./docs/DECISIONS.md) — the real bugs behind the editing engine's design choices, and why each workaround exists. Good starting point before touching `pdf_engine.py`.

## Known limitations

- **Upload and edit size**: PDFs over 20 MB are rejected, and a single edit is capped at 5000 characters (both configurable, see above).
- **PDF parsing is sandboxed**: every operation touching an uploaded PDF runs in a short-lived, resource-limited subprocess (see [`docs/DECISIONS.md`](./docs/DECISIONS.md#isoler-le-parsing-pdf-dans-un-sous-processus)), since a malformed PDF can crash the underlying C library. This adds a small per-request overhead but keeps one bad file from taking down the whole backend.
- **Reusing the original font** only works if it exposes a usable Unicode cmap. Most PDFs produced by Word or a virtual printer embed subsetted Identity-H fonts without one — in that (very common) case, Glyph falls back to a system font with the same name (e.g. Arial Narrow), or a generic system font otherwise, with metric compensation to preserve the original visual width.
- **Editing is per line, deliberately**: a field spanning several visual lines (an address, a multi-line note) is edited one line at a time rather than as a single reflow-capable block. Earlier versions tried to auto-detect "this is one wrapped paragraph" from shared edges/alignment, but real documents kept surfacing independent lines that looked just like a wrapped paragraph by coincidence (a title stacked on a subtitle, a right-aligned column of unrelated values) — merging them let editing one line corrupt another. Per-line editing has no such failure mode. See `docs/DECISIONS.md`.
- **Block overflow**: if you type a manual line break into a field, growing it to more lines than it originally had, it grows downward — but only up to the nearest sibling below, never past it; a field one line tall never grows at all (its font size is reduced instead if the new text is too wide). Editing a block is also clamped against its immediate neighbors on all four sides, so it can never bleed into a sibling's territory even when their bounding boxes already overlap slightly in the source PDF (common with tight line leading or tightly-packed table columns — see `docs/DECISIONS.md`).
- **Colored backgrounds**: redaction clears everything in the edited area, including any vector fill behind the text. Not an issue for typical text blocks (names, dates, paragraphs), but worth knowing if you're editing colored table cells.
- **Password-protected PDFs** are rejected at upload with a clear error — not supported.
- No advanced text shaping (HarfBuzz), no RTL/CJK support, no page rotation — out of scope for now. Signatures, form fields, shapes, and OCR aren't implemented yet.
- The system-font fallback currently only looks in macOS's font directory; running the backend on Linux/Windows will skip that fallback tier (see `docs/DECISIONS.md`).
- `backend/tests/` covers the block-detection and redaction-safety invariants (`python -m unittest discover -s tests -v`); `backend/smoke_test.py` remains a manual, ad hoc script on top of that, not part of CI.

## Contributing

Issues and pull requests are welcome. If you're planning a non-trivial change to the editing engine, reading `docs/DECISIONS.md` first will save you from re-discovering bugs that are already worked around.

## License

[MIT](./LICENSE)

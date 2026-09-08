# Glyph

Glyph edits text directly inside a PDF's content stream instead of drawing a patch on top of it. When you edit a paragraph, the original glyphs are actually removed (via PDF redaction) and the new text is re-inserted in their place — not covered by a white rectangle with new text stacked over it.

It's a small, focused, open-source tool: no accounts, no cloud storage, no tracking. Everything runs locally — your PDF stays in server memory for the duration of your session and is never written to disk.

## How it works

1. Open a PDF (uploaded to the local backend, kept in memory only).
2. Click a paragraph or table cell — an editor appears exactly where the text is.
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

- **Reusing the original font** only works if it exposes a usable Unicode cmap. Most PDFs produced by Word or a virtual printer embed subsetted Identity-H fonts without one — in that (very common) case, Glyph falls back to a system font with the same name (e.g. Arial Narrow), or a generic system font otherwise, with metric compensation to preserve the original visual width.
- **Block overflow**: a multi-line paragraph can grow downward if the new text is longer; a table cell (single line) never grows — its font size is reduced instead, so it never overlaps a neighboring row or column.
- **Colored backgrounds**: redaction clears everything in the edited area, including any vector fill behind the text. Not an issue for typical text blocks (names, dates, paragraphs), but worth knowing if you're editing colored table cells.
- No advanced text shaping (HarfBuzz), no RTL/CJK support, no page rotation — out of scope for now. Signatures, form fields, shapes, and OCR aren't implemented yet.
- The system-font fallback currently only looks in macOS's font directory; running the backend on Linux/Windows will skip that fallback tier (see `docs/DECISIONS.md`).
- No automated test suite yet — `backend/smoke_test.py` is a manual verification script, not CI.

## Contributing

Issues and pull requests are welcome. If you're planning a non-trivial change to the editing engine, reading `docs/DECISIONS.md` first will save you from re-discovering bugs that are already worked around.

## License

[MIT](./LICENSE)

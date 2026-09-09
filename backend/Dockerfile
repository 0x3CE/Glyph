FROM python:3.12-slim

WORKDIR /app

# PyMuPDF ships its own bundled shared libs on manylinux wheels -- no extra
# system packages needed beyond a C toolchain-free slim base.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Non-root: this process opens and parses PDFs nobody here produced (see
# docs/DECISIONS.md, "Isoler le parsing PDF dans un sous-processus") --
# don't also hand it root in the container on top of that.
RUN useradd --create-home --uid 1000 glyph
USER glyph

EXPOSE 8000

# Render (and most PaaS) inject $PORT at runtime; default to 8000 for local
# `docker run`. Shell form so $PORT actually expands.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

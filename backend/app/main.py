from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import math
import os
import secrets
from contextlib import asynccontextmanager
from typing import TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from . import documents
from .isolation import SandboxBusyError, SandboxError, run_isolated, warm_up
from .pdf_engine import (
    worker_add_signature,
    worker_apply_edit,
    worker_extract_structure,
    worker_find,
    worker_inspect,
    worker_redact,
    worker_replace_page,
    worker_sanitize,
    worker_validate_pdf,
)
from .schemas import (
    EditRequest,
    EditResponse,
    FindResult,
    HistoryResponse,
    InspectReport,
    PageReplaceResult,
    PageStructure,
    RedactRequest,
    RedactResponse,
    ReplaceRequest,
    ReplaceResponse,
    SanitizeResponse,
    SignatureResponse,
    UploadResponse,
)

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024
MAX_SIGNATURE_BYTES = int(os.environ.get("MAX_SIGNATURE_MB", "5")) * 1024 * 1024
# Find & replace: lines edited per sandbox run (one page each) and per
# request, and pages per request -- each page is one sandbox run (~1 s on a
# small CPU), so without this one request could hold a sandbox slot for
# minutes. Past the cap the response says `truncated`: run it again.
REPLACE_MAX_LINES_PER_PAGE = 60
REPLACE_MAX_LINES = 300
REPLACE_MAX_PAGES = 20
# Request bodies are read whole into memory (see _read_body): at most this
# many at once, so a burst of large uploads can't exhaust the API's RAM.
# A request that can't get a slot within UPLOAD_QUEUE_TIMEOUT_SECONDS gets
# a 503.
MAX_CONCURRENT_UPLOADS = int(os.environ.get("MAX_CONCURRENT_UPLOADS", "4"))
UPLOAD_QUEUE_TIMEOUT_SECONDS = 10
# Signature placement: coordinates must be finite and within this many PDF
# points (PDF caps page sides at 14,400 pt).
MAX_COORDINATE = 100_000

# Comma-separated list, e.g. "https://glyph.vercel.app,http://localhost:3000".
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in _allowed_origins.split(",") if origin.strip()]

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Start the sandbox's forkserver (and its preloaded PDF engine) now, so
    # the first visitor doesn't pay for it. Not fatal: run_isolated starts it
    # on demand anyway.
    try:
        await run_in_threadpool(warm_up)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("sandbox warm-up failed")
    yield


# The interactive API docs (/docs, /redoc, /openapi.json) are off unless
# ENABLE_API_DOCS=1 (local development): in production they'd only map the
# API out for whoever finds the backend's address.
_docs = os.environ.get("ENABLE_API_DOCS") == "1"
app = FastAPI(
    title="PDF Editor API",
    lifespan=lifespan,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sandbox_error_to_http(
    e: SandboxError,
    *,
    not_found: dict[str, str] | None = None,
    bad_request: dict[str, str] | None = None,
) -> HTTPException:
    if isinstance(e, SandboxBusyError):
        return HTTPException(503, str(e))
    if not_found and e.kind in not_found:
        return HTTPException(404, not_found[e.kind])
    if bad_request and e.kind in bad_request:
        return HTTPException(400, bad_request[e.kind])
    return HTTPException(422, f"failed to process PDF: {e}")


def _valid_rect(bbox: tuple[float, float, float, float]) -> bool:
    """Finite (query parameters accept "nan" and "inf"), within the largest
    possible page, and not empty or inverted."""
    x0, y0, x1, y1 = bbox
    return all(math.isfinite(v) and abs(v) <= MAX_COORDINATE for v in bbox) and x1 > x0 and y1 > y0


_UPLOAD_SLOTS = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)


@asynccontextmanager
async def _upload_slot():
    """Held for a whole upload-type request (body read, processing, storing):
    the body stays in memory that long."""
    try:
        await asyncio.wait_for(_UPLOAD_SLOTS.acquire(), UPLOAD_QUEUE_TIMEOUT_SECONDS)
    except TimeoutError as e:
        raise HTTPException(503, "server busy, please retry in a moment") from e
    try:
        yield
    finally:
        _UPLOAD_SLOTS.release()


async def _read_body(request: Request, limit: int, what: str) -> bytes:
    """The raw request body, read into memory only, and cut off as soon as
    it exceeds `limit`. Uploads are sent as a raw body rather than
    multipart: Starlette's multipart parser spools every file part over
    1 MB to a temporary file on disk, and only lets us check the size once
    the whole thing has been received."""
    too_large = HTTPException(413, f"{what} too large (max {limit // (1024 * 1024)} MB)")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise too_large
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise too_large
    return bytes(body)


Model = TypeVar("Model", bound=BaseModel)


def _validated(model: type[Model], meta: object, **extra: object) -> Model:
    """`meta` comes out of the sandbox, i.e. from a process that just parsed
    an untrusted PDF: check its shape before anything else touches it."""
    if not isinstance(meta, dict):
        raise HTTPException(422, "failed to process PDF")
    try:
        return model.model_validate({**meta, **extra})
    except ValidationError as e:
        raise HTTPException(422, "failed to process PDF") from e


# Key for the per-visitor document quota: an HMAC of the client IP with a
# key drawn at startup, so the store only ever holds an opaque value -- never
# the IP itself, and nothing that can be linked back to it after a restart.
_CLIENT_KEY_SECRET = secrets.token_bytes(32)


def _client_key(request: Request) -> str:
    """Who is making this request, for quotas. In production the API sits
    behind Vercel (the frontend's /api rewrite), which overwrites
    X-Forwarded-For with the visitor's real IP (a client can't spoof it
    there); proxies after it (Render) append their own hop, so the
    left-most entry is the visitor. A client calling the backend directly
    could forge the header: closing that door (only Vercel may call the
    backend) is a separate measure."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "")
    return hmac.new(_CLIENT_KEY_SECRET, ip.encode(), hashlib.sha256).hexdigest()


def _current_or_404(document_id: str) -> bytes:
    pdf = documents.current(document_id)
    if pdf is None:
        raise HTTPException(404, "document not found")
    return pdf


def _push_or_error(document_id: str, new_pdf: bytes | None) -> None:
    if new_pdf is None:
        raise HTTPException(422, "failed to process PDF")
    try:
        stored = documents.push(document_id, new_pdf)
    except documents.StoreFullError as e:
        raise HTTPException(503, str(e)) from e
    if not stored:
        raise HTTPException(404, "document not found")


@app.post("/api/documents", response_model=UploadResponse)
async def upload(request: Request) -> UploadResponse:
    async with _upload_slot():
        return await _upload(request)


async def _upload(request: Request) -> UploadResponse:
    raw = await _read_body(request, MAX_UPLOAD_BYTES, "file")
    try:
        meta, _ = await run_in_threadpool(run_isolated, worker_validate_pdf, raw)
    except SandboxBusyError as e:
        raise HTTPException(503, str(e)) from e
    except SandboxError as e:
        raise HTTPException(400, f"invalid PDF: {e}") from e
    page_count = _validated(UploadResponse, meta, document_id="pending").page_count
    try:
        document_id = documents.create(raw, owner=_client_key(request))
    except documents.TooManyDocumentsError as e:
        raise HTTPException(429, str(e)) from e
    except documents.StoreFullError as e:
        raise HTTPException(503, str(e)) from e
    return UploadResponse(document_id=document_id, page_count=page_count)


@app.get("/api/documents/{document_id}/file")
def download(document_id: str) -> Response:
    return Response(content=_current_or_404(document_id), media_type="application/pdf")


@app.get("/api/documents/{document_id}/pages/{page_index}/structure", response_model=PageStructure)
def structure(document_id: str, page_index: int) -> PageStructure:
    pdf = _current_or_404(document_id)
    try:
        meta, _ = run_isolated(worker_extract_structure, pdf, page_index)
    except SandboxError as e:
        raise _sandbox_error_to_http(e, not_found={"IndexError": "page not found"}) from e
    return _validated(PageStructure, meta, page_index=page_index)


@app.post(
    "/api/documents/{document_id}/pages/{page_index}/blocks/{block_id}/edit",
    response_model=EditResponse,
)
def edit_block(document_id: str, page_index: int, block_id: str, body: EditRequest) -> EditResponse:
    pdf = _current_or_404(document_id)
    try:
        meta, new_pdf = run_isolated(worker_apply_edit, pdf, page_index, block_id, body.text)
    except SandboxError as e:
        raise _sandbox_error_to_http(
            e, not_found={"IndexError": "page not found", "LookupError": "block not found"}
        ) from e

    response = _validated(EditResponse, meta)
    _push_or_error(document_id, new_pdf)
    return response


@app.post(
    "/api/documents/{document_id}/pages/{page_index}/signature",
    response_model=SignatureResponse,
)
async def add_signature(
    request: Request,
    document_id: str,
    page_index: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> SignatureResponse:
    bbox = (x0, y0, x1, y1)
    if not _valid_rect(bbox):
        raise HTTPException(422, "invalid signature rectangle")
    pdf = _current_or_404(document_id)
    async with _upload_slot():
        return await _add_signature(request, document_id, page_index, pdf, bbox)


async def _add_signature(
    request: Request,
    document_id: str,
    page_index: int,
    pdf: bytes,
    bbox: tuple[float, float, float, float],
) -> SignatureResponse:
    raw = await _read_body(request, MAX_SIGNATURE_BYTES, "signature file")
    try:
        meta, new_pdf = await run_in_threadpool(
            run_isolated, worker_add_signature, pdf, page_index, raw, bbox
        )
    except SandboxError as e:
        raise _sandbox_error_to_http(
            e,
            not_found={"IndexError": "page not found"},
            bad_request={"UnsupportedSignatureFileError": str(e)},
        ) from e

    response = _validated(SignatureResponse, meta)
    _push_or_error(document_id, new_pdf)
    return response


@app.post("/api/documents/{document_id}/pages/{page_index}/redact", response_model=RedactResponse)
def redact(document_id: str, page_index: int, body: RedactRequest) -> RedactResponse:
    """Real redaction: everything under the areas is deleted from the file,
    then painted black (pdf_engine/redaction.py)."""
    pdf = _current_or_404(document_id)
    try:
        meta, new_pdf = run_isolated(worker_redact, pdf, page_index, body.rects)
    except SandboxError as e:
        raise _sandbox_error_to_http(e, not_found={"IndexError": "page not found"}) from e
    response = _validated(RedactResponse, meta)
    _push_or_error(document_id, new_pdf)
    return response


@app.post("/api/documents/{document_id}/sanitize", response_model=SanitizeResponse)
def sanitize(document_id: str) -> SanitizeResponse:
    """Strips metadata, XMP, attachments, JavaScript, invisible text..."""
    pdf = _current_or_404(document_id)
    try:
        meta, new_pdf = run_isolated(worker_sanitize, pdf)
    except SandboxError as e:
        raise _sandbox_error_to_http(e) from e
    response = _validated(SanitizeResponse, meta)
    _push_or_error(document_id, new_pdf)
    return response


@app.post("/api/documents/{document_id}/replace", response_model=ReplaceResponse)
def replace(document_id: str, body: ReplaceRequest) -> ReplaceResponse:
    """Find & replace across the document (pdf_engine/replace.py). One
    sandbox run to find the pages, then one per page to edit -- each stays
    inside the CPU budget -- and a single undo step for the whole thing."""
    pdf = _current_or_404(document_id)
    nothing = ReplaceResponse(replaced=0, lines=0, pages=[], truncated=False, font_substituted=False)
    if body.match_case and body.find == body.replace:
        return nothing
    options = (body.match_case, body.whole_word)
    try:
        found_meta, _ = run_isolated(worker_find, pdf, body.find, *options)
        found = _validated(FindResult, found_meta)
        replaced = lines = 0
        changed: list[int] = []
        substituted = truncated = False
        for done, (page_index, _count) in enumerate(found.pages):
            budget = min(REPLACE_MAX_LINES_PER_PAGE, REPLACE_MAX_LINES - lines)
            if budget <= 0 or done >= REPLACE_MAX_PAGES:
                truncated = True
                break
            meta, new_pdf = run_isolated(
                worker_replace_page, pdf, page_index, body.find, body.replace, *options, budget
            )
            result = _validated(PageReplaceResult, meta)
            if result.lines:
                if new_pdf is None:
                    raise HTTPException(422, "failed to process PDF")
                pdf = new_pdf
                changed.append(page_index + 1)
            replaced += result.replaced
            lines += result.lines
            substituted |= result.font_substituted
            truncated |= result.remaining_lines > 0
    except SandboxError as e:
        raise _sandbox_error_to_http(e) from e
    if not changed:
        return nothing
    _push_or_error(document_id, pdf)
    return ReplaceResponse(
        replaced=replaced, lines=lines, pages=changed, truncated=truncated, font_substituted=substituted
    )


@app.post("/api/inspect", response_model=InspectReport)
async def inspect(request: Request) -> InspectReport:
    """Read-only report of what a PDF hides. The file is analysed in the
    sandbox and never stored."""
    async with _upload_slot():
        return await _inspect(request)


async def _inspect(request: Request) -> InspectReport:
    raw = await _read_body(request, MAX_UPLOAD_BYTES, "file")
    try:
        meta, _ = await run_in_threadpool(run_isolated, worker_inspect, raw)
    except SandboxBusyError as e:
        raise HTTPException(503, str(e)) from e
    except SandboxError as e:
        raise HTTPException(400, f"invalid PDF: {e}") from e
    return _validated(InspectReport, meta)


def _history(state: documents.DocumentState | None) -> HistoryResponse:
    if state is None:
        raise HTTPException(404, "document not found")
    return HistoryResponse(cursor=state.cursor, can_undo=state.can_undo, can_redo=state.can_redo)


@app.post("/api/documents/{document_id}/undo", response_model=HistoryResponse)
def undo(document_id: str) -> HistoryResponse:
    return _history(documents.undo(document_id))


@app.post("/api/documents/{document_id}/redo", response_model=HistoryResponse)
def redo(document_id: str) -> HistoryResponse:
    return _history(documents.redo(document_id))


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str) -> dict:
    documents.delete(document_id)
    return {"ok": True}

from __future__ import annotations

import logging
import os
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
    worker_validate_pdf,
)
from .schemas import (
    EditRequest,
    EditResponse,
    HistoryResponse,
    PageStructure,
    SignatureResponse,
    UploadResponse,
)

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024
MAX_SIGNATURE_BYTES = int(os.environ.get("MAX_SIGNATURE_MB", "5")) * 1024 * 1024

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


app = FastAPI(title="PDF Editor API", lifespan=lifespan)
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
    raw = await _read_body(request, MAX_UPLOAD_BYTES, "file")
    try:
        meta, _ = await run_in_threadpool(run_isolated, worker_validate_pdf, raw)
    except SandboxBusyError as e:
        raise HTTPException(503, str(e)) from e
    except SandboxError as e:
        raise HTTPException(400, f"invalid PDF: {e}") from e
    page_count = _validated(UploadResponse, meta, document_id="pending").page_count
    try:
        document_id = documents.create(raw)
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
    pdf = _current_or_404(document_id)
    raw = await _read_body(request, MAX_SIGNATURE_BYTES, "signature file")
    try:
        meta, new_pdf = await run_in_threadpool(
            run_isolated, worker_add_signature, pdf, page_index, raw, (x0, y0, x1, y1)
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

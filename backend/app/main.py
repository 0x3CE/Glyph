from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import documents
from .isolation import SandboxError, run_isolated
from .pdf_engine import worker_apply_edit, worker_extract_structure, worker_validate_pdf
from .schemas import (
    BlockOut,
    EditRequest,
    EditResponse,
    LineOut,
    PageStructure,
    SpanOut,
    UploadResponse,
)

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024

# Comma-separated list, e.g. "https://glyph.vercel.app,http://localhost:3000".
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
ALLOWED_ORIGINS = [origin.strip() for origin in _allowed_origins.split(",") if origin.strip()]

app = FastAPI(title="PDF Editor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sandbox_error_to_http(e: SandboxError, *, not_found: dict[str, str] | None = None) -> HTTPException:
    if not_found and e.kind in not_found:
        return HTTPException(404, not_found[e.kind])
    return HTTPException(422, f"failed to process PDF: {e}")


@app.post("/api/documents", response_model=UploadResponse)
async def upload(file: UploadFile) -> UploadResponse:
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"file too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
    try:
        page_count = await run_in_threadpool(run_isolated, worker_validate_pdf, raw)
    except SandboxError as e:
        raise HTTPException(400, f"invalid PDF: {e}") from e
    document_id = documents.create(raw)
    return UploadResponse(document_id=document_id, page_count=page_count)


@app.get("/api/documents/{document_id}/file")
def download(document_id: str) -> Response:
    state = documents.get(document_id)
    if state is None:
        raise HTTPException(404, "document not found")
    return Response(content=state.current, media_type="application/pdf")


@app.get("/api/documents/{document_id}/pages/{page_index}/structure", response_model=PageStructure)
def structure(document_id: str, page_index: int) -> PageStructure:
    state = documents.get(document_id)
    if state is None:
        raise HTTPException(404, "document not found")
    try:
        result = run_isolated(worker_extract_structure, state.current, page_index)
    except SandboxError as e:
        raise _sandbox_error_to_http(e, not_found={"IndexError": "page not found"}) from e
    return PageStructure(
        page_index=page_index,
        width=result.width,
        height=result.height,
        blocks=[
            BlockOut(
                id=b.id,
                bbox=b.bbox,
                text=b.text,
                lines=[
                    LineOut(
                        bbox=line.bbox,
                        spans=[
                            SpanOut(
                                text=s.text,
                                bbox=s.bbox,
                                font=s.font,
                                size=s.size,
                                color=s.color,
                                flags=s.flags,
                            )
                            for s in line.spans
                        ],
                    )
                    for line in b.lines
                ],
            )
            for b in result.blocks
        ],
    )


@app.post(
    "/api/documents/{document_id}/pages/{page_index}/blocks/{block_id}/edit",
    response_model=EditResponse,
)
def edit_block(document_id: str, page_index: int, block_id: str, body: EditRequest) -> EditResponse:
    state = documents.get(document_id)
    if state is None:
        raise HTTPException(404, "document not found")
    try:
        new_pdf_bytes, substituted, new_bbox = run_isolated(
            worker_apply_edit, state.current, page_index, block_id, body.text
        )
    except SandboxError as e:
        raise _sandbox_error_to_http(
            e, not_found={"IndexError": "page not found", "LookupError": "block not found"}
        ) from e

    state.push(new_pdf_bytes)
    return EditResponse(font_substituted=substituted, new_bbox=new_bbox)


@app.post("/api/documents/{document_id}/undo")
def undo(document_id: str) -> dict:
    state = documents.get(document_id)
    if state is None:
        raise HTTPException(404, "document not found")
    state.undo()
    return {"cursor": state.cursor, "can_undo": state.cursor > 0, "can_redo": state.cursor < len(state.history) - 1}


@app.post("/api/documents/{document_id}/redo")
def redo(document_id: str) -> dict:
    state = documents.get(document_id)
    if state is None:
        raise HTTPException(404, "document not found")
    state.redo()
    return {"cursor": state.cursor, "can_undo": state.cursor > 0, "can_redo": state.cursor < len(state.history) - 1}


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str) -> dict:
    documents.delete(document_id)
    return {"ok": True}

from __future__ import annotations

import io

import pymupdf
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import documents
from .pdf_engine import apply_block_edit, extract_structure
from .schemas import (
    BlockOut,
    EditRequest,
    EditResponse,
    LineOut,
    PageStructure,
    SpanOut,
    UploadResponse,
)

app = FastAPI(title="PDF Editor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _open(document_id: str) -> tuple[documents.DocumentState, pymupdf.Document]:
    state = documents.get(document_id)
    if state is None:
        raise HTTPException(404, "document not found")
    doc = pymupdf.open(stream=state.current, filetype="pdf")
    return state, doc


@app.post("/api/documents", response_model=UploadResponse)
async def upload(file: UploadFile) -> UploadResponse:
    raw = await file.read()
    try:
        doc = pymupdf.open(stream=raw, filetype="pdf")
    except Exception as e:
        raise HTTPException(400, f"invalid PDF: {e}") from e
    document_id = documents.create(raw)
    return UploadResponse(document_id=document_id, page_count=doc.page_count)


@app.get("/api/documents/{document_id}/file")
def download(document_id: str) -> Response:
    state = documents.get(document_id)
    if state is None:
        raise HTTPException(404, "document not found")
    return Response(content=state.current, media_type="application/pdf")


@app.get("/api/documents/{document_id}/pages/{page_index}/structure", response_model=PageStructure)
def structure(document_id: str, page_index: int) -> PageStructure:
    _state, doc = _open(document_id)
    if not (0 <= page_index < doc.page_count):
        raise HTTPException(404, "page not found")
    page = doc[page_index]
    blocks = extract_structure(page)
    return PageStructure(
        page_index=page_index,
        width=page.rect.width,
        height=page.rect.height,
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
            for b in blocks
        ],
    )


@app.post(
    "/api/documents/{document_id}/pages/{page_index}/blocks/{block_id}/edit",
    response_model=EditResponse,
)
def edit_block(document_id: str, page_index: int, block_id: str, body: EditRequest) -> EditResponse:
    state, doc = _open(document_id)
    if not (0 <= page_index < doc.page_count):
        raise HTTPException(404, "page not found")
    page = doc[page_index]
    blocks = extract_structure(page)
    block = next((b for b in blocks if b.id == block_id), None)
    if block is None:
        raise HTTPException(404, "block not found")

    substituted, new_bbox = apply_block_edit(doc, page, block, body.text)

    buf = io.BytesIO()
    doc.save(buf)
    state.push(buf.getvalue())

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

from pydantic import BaseModel, ConfigDict, Field


class SpanOut(BaseModel):
    text: str
    bbox: tuple[float, float, float, float]
    font: str
    size: float
    color: int
    flags: int


class LineOut(BaseModel):
    bbox: tuple[float, float, float, float]
    spans: list[SpanOut]


class BlockOut(BaseModel):
    id: str
    bbox: tuple[float, float, float, float]
    lines: list[LineOut]
    text: str
    # False: the PDF's text can't be read back (no character map, or a
    # ToUnicode table that doesn't match the codes drawn);
    # `text` is then meaningless and the line must be retyped in full.
    text_reliable: bool = True


class PageStructure(BaseModel):
    page_index: int
    width: float
    height: float
    blocks: list[BlockOut]


class UploadResponse(BaseModel):
    document_id: str
    page_count: int


class EditRequest(BaseModel):
    text: str = Field(max_length=5000)


class EditResponse(BaseModel):
    font_substituted: bool
    new_bbox: tuple[float, float, float, float]


class SignatureResponse(BaseModel):
    bbox: tuple[float, float, float, float]


class HistoryResponse(BaseModel):
    cursor: int
    can_undo: bool
    can_redo: bool


class RedactRequest(BaseModel):
    # Finite coordinates only (no NaN/inf), at most 200 areas per call.
    model_config = ConfigDict(allow_inf_nan=False)
    rects: list[tuple[float, float, float, float]] = Field(min_length=1, max_length=200)


class RedactResponse(BaseModel):
    redacted: int


class SanitizeResponse(BaseModel):
    removed: list[str]


class HiddenText(BaseModel):
    page: int
    text: str


class InspectReport(BaseModel):
    page_count: int
    pages_inspected: int
    hidden_text: list[HiddenText]
    unapplied_redactions: int
    invisible_text_chars: int
    invisible_text_samples: list[HiddenText]
    metadata: dict[str, str]
    has_xmp: bool
    versions: int
    attachments: list[str]
    annotations: dict[str, int]


class ReplaceRequest(BaseModel):
    # One line at a time (see pdf_engine/replace.py): no line breaks.
    find: str = Field(min_length=1, max_length=200, pattern=r"^[^\r\n]+$")
    replace: str = Field(max_length=200, pattern=r"^[^\r\n]*$")
    match_case: bool = False
    whole_word: bool = False


class ReplaceResponse(BaseModel):
    replaced: int
    lines: int
    pages: list[int]  # 1-based, the pages that changed
    truncated: bool  # stopped at the limit: some occurrences are left
    font_substituted: bool


# Internal: what the find & replace workers send back out of the sandbox.
class FindResult(BaseModel):
    pages: list[tuple[int, int]]  # (page index, occurrences)


class PageReplaceResult(BaseModel):
    replaced: int
    lines: int
    remaining_lines: int
    font_substituted: bool

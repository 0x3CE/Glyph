from pydantic import BaseModel, Field


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

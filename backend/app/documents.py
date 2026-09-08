"""In-memory document store: no PDF is ever written to disk. Each document
keeps a stack of full-PDF byte snapshots for linear undo/redo."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class DocumentState:
    history: list[bytes]
    cursor: int  # index into history of the "current" version

    @property
    def current(self) -> bytes:
        return self.history[self.cursor]

    def push(self, new_bytes: bytes) -> None:
        del self.history[self.cursor + 1 :]
        self.history.append(new_bytes)
        self.cursor += 1

    def undo(self) -> bytes:
        self.cursor = max(0, self.cursor - 1)
        return self.current

    def redo(self) -> bytes:
        self.cursor = min(len(self.history) - 1, self.cursor + 1)
        return self.current


_STORE: dict[str, DocumentState] = {}


def create(initial_bytes: bytes) -> str:
    document_id = uuid.uuid4().hex
    _STORE[document_id] = DocumentState(history=[initial_bytes], cursor=0)
    return document_id


def get(document_id: str) -> DocumentState | None:
    return _STORE.get(document_id)


def delete(document_id: str) -> None:
    _STORE.pop(document_id, None)

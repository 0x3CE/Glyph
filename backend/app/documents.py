"""In-memory document store: no PDF is ever written to disk. Each document
keeps a stack of full-PDF byte snapshots for linear undo/redo.

Everything here is bounded, because it all lives in the API process's own
memory -- the one process the sandbox exists to keep alive:

- a document nobody touched for DOCUMENT_TTL_MINUTES is dropped;
- one document's history is capped at DOCUMENT_MAX_MB (the oldest undo
  states go first, the current version is always kept);
- the whole store is capped at STORE_MAX_MB and MAX_DOCUMENTS; past that, new
  uploads/edits are refused (`StoreFullError` -> 503) rather than evicting
  someone else's document mid-edit;
- one visitor (`owner`, an opaque key derived from their IP by main.py) can
  have at most MAX_DOCUMENTS_PER_OWNER open at once (`TooManyDocumentsError`
  -> 429): without it, a single client could fill MAX_DOCUMENTS with tiny
  PDFs in seconds and lock everyone else out.

Routes run on a threadpool, so every access goes through `_LOCK`.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field

DOCUMENT_TTL_SECONDS = int(os.environ.get("DOCUMENT_TTL_MINUTES", "30")) * 60
DOCUMENT_MAX_BYTES = int(os.environ.get("DOCUMENT_MAX_MB", "60")) * 1024 * 1024
STORE_MAX_BYTES = int(os.environ.get("STORE_MAX_MB", "200")) * 1024 * 1024
MAX_DOCUMENTS = int(os.environ.get("MAX_DOCUMENTS", "200"))
MAX_DOCUMENTS_PER_OWNER = int(os.environ.get("MAX_DOCUMENTS_PER_OWNER", "10"))


class StoreFullError(Exception):
    """The store is at capacity; the client should retry later."""


class TooManyDocumentsError(Exception):
    """This owner already has MAX_DOCUMENTS_PER_OWNER documents open."""


@dataclass
class DocumentState:
    history: list[bytes]
    cursor: int  # index into history of the "current" version
    last_access: float = field(default_factory=time.monotonic)
    owner: str = ""

    @property
    def current(self) -> bytes:
        return self.history[self.cursor]

    @property
    def size(self) -> int:
        return sum(len(v) for v in self.history)

    @property
    def can_undo(self) -> bool:
        return self.cursor > 0

    @property
    def can_redo(self) -> bool:
        return self.cursor < len(self.history) - 1


_STORE: dict[str, DocumentState] = {}
_LOCK = threading.Lock()


def _total_size() -> int:
    return sum(state.size for state in _STORE.values())


def _purge_expired(now: float) -> None:
    for document_id in [d for d, s in _STORE.items() if now - s.last_access > DOCUMENT_TTL_SECONDS]:
        del _STORE[document_id]


def create(initial_bytes: bytes, owner: str = "") -> str:
    with _LOCK:
        now = time.monotonic()
        _purge_expired(now)
        if owner and sum(1 for s in _STORE.values() if s.owner == owner) >= MAX_DOCUMENTS_PER_OWNER:
            raise TooManyDocumentsError(
                f"too many open documents (max {MAX_DOCUMENTS_PER_OWNER}): close one, or wait for it to expire"
            )
        if len(_STORE) >= MAX_DOCUMENTS or _total_size() + len(initial_bytes) > STORE_MAX_BYTES:
            raise StoreFullError("server at capacity, please retry later")
        document_id = uuid.uuid4().hex
        _STORE[document_id] = DocumentState(history=[initial_bytes], cursor=0, last_access=now, owner=owner)
        return document_id


def current(document_id: str) -> bytes | None:
    """The document's current bytes (and a TTL refresh), or None."""
    with _LOCK:
        now = time.monotonic()
        _purge_expired(now)
        state = _STORE.get(document_id)
        if state is None:
            return None
        state.last_access = now
        return state.current


def push(document_id: str, new_bytes: bytes) -> bool:
    """Appends a new version (dropping any redo branch). False if the
    document is gone (expired/deleted while the edit was running)."""
    with _LOCK:
        state = _STORE.get(document_id)
        if state is None:
            return False
        del state.history[state.cursor + 1 :]

        others = _total_size() - state.size
        if others + state.size + len(new_bytes) > STORE_MAX_BYTES:
            # Give up this document's own undo history before refusing.
            state.history = [state.current]
            state.cursor = 0
            if others + state.size + len(new_bytes) > STORE_MAX_BYTES:
                raise StoreFullError("server at capacity, please retry later")

        state.history.append(new_bytes)
        state.cursor += 1
        while state.size > DOCUMENT_MAX_BYTES and len(state.history) > 1:
            state.history.pop(0)
            state.cursor -= 1
        state.last_access = time.monotonic()
        return True


def undo(document_id: str) -> DocumentState | None:
    with _LOCK:
        state = _STORE.get(document_id)
        if state is not None:
            state.cursor = max(0, state.cursor - 1)
            state.last_access = time.monotonic()
        return state


def redo(document_id: str) -> DocumentState | None:
    with _LOCK:
        state = _STORE.get(document_id)
        if state is not None:
            state.cursor = min(len(state.history) - 1, state.cursor + 1)
            state.last_access = time.monotonic()
        return state


def delete(document_id: str) -> None:
    with _LOCK:
        _STORE.pop(document_id, None)

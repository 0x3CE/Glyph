"""Runs untrusted-PDF processing in a throwaway subprocess.

PyMuPDF is a C library parsing files nobody here controls the origin of.
A malformed or adversarial PDF that segfaults, OOMs, or infinite-loops the
process handling it would otherwise take down the whole API (and every other
in-flight request) with it. Every call that touches PDF bytes we didn't
generate ourselves goes through `run_isolated`: a fresh process per call,
with hard memory/CPU/wall-clock limits, so the worst a hostile PDF can do is
waste one short-lived process.

`forkserver`, with the engine preloaded: a dedicated server process is
started once (cleanly, not forked from the API), imports `app.pdf_engine`
(PyMuPDF, fontTools...) once, and every call is a fork of THAT process.
Never a plain `fork` of the API process itself: that would copy its file
descriptors and sockets, and forking uvicorn's multi-threaded process is
unsafe. The forkserver is single-threaded and holds nothing but the
preloaded modules, and each child is still a separate, throwaway,
resource-limited copy. It replaced `spawn`, which re-imported the whole
engine in every child: measured ~3 s per operation on Render's small CPU
(every upload, every page change), vs ~120 ms -> ~11 ms locally.

The child is treated as potentially compromised (a memory-corruption bug in
MuPDF exploited by the PDF it's parsing), so nothing it sends back is ever
unpickled: results travel as one length-bounded JSON frame plus an optional
length-bounded raw-bytes frame (`Connection.send_bytes`/`recv_bytes`, no
pickle involved), and callers validate the JSON against their response
models. Pickle is only used parent -> child (the call's own argument
passing), the direction where the sender is trusted.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import resource
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

_CTX = mp.get_context("forkserver")
# Must be set before the forkserver starts (on the first call, or warm_up()).
_CTX.set_forkserver_preload(["app.pdf_engine"])

MAX_MEMORY_BYTES = int(os.environ.get("SANDBOX_MAX_MEMORY_MB", "512")) * 1024 * 1024
MAX_CPU_SECONDS = int(os.environ.get("SANDBOX_MAX_CPU_SECONDS", "8"))
TIMEOUT_SECONDS = int(os.environ.get("SANDBOX_TIMEOUT_SECONDS", "15"))
# How many sandboxed processes may run at once, and how long a request waits
# for a free slot before giving up with "busy". The per-process memory limit
# bounds ONE hostile PDF; this bounds how many of them a burst of requests
# can have in flight together (40 threadpool threads x 512 MB otherwise).
MAX_CONCURRENCY = int(os.environ.get("SANDBOX_MAX_CONCURRENCY", "2"))
QUEUE_TIMEOUT_SECONDS = int(os.environ.get("SANDBOX_QUEUE_TIMEOUT_SECONDS", "20"))
# Upper bound on what a worker may send back (a re-saved PDF, a page
# structure as JSON) -- a compromised child can't make the parent allocate
# more than this.
MAX_RESULT_BYTES = int(os.environ.get("SANDBOX_MAX_RESULT_MB", "64")) * 1024 * 1024
MAX_HEADER_BYTES = 32 * 1024 * 1024

_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENCY)

# Scratch files a worker writes (fonts extracted from the PDF, see
# pdf_engine/fonts.py) go to a per-call directory the parent always deletes,
# even when it had to kill the worker. RAM-backed (/dev/shm) when the
# platform has it -- the case on the Linux deployment -- so document-derived
# bytes don't land on disk either.
_SHM = Path("/dev/shm")
_SCRATCH_ROOT = str(_SHM) if _SHM.is_dir() and os.access(_SHM, os.W_OK) else None


class SandboxError(Exception):
    """A worker raised, was killed for exceeding its limits, or timed out.

    `kind` carries the original exception's class name (e.g. "IndexError")
    when the worker reported one cleanly, so callers can map specific
    failures (page/block not found) back to the right HTTP status instead
    of treating everything as an opaque 500.
    """

    def __init__(self, message: str, kind: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind


class SandboxBusyError(SandboxError):
    """Every sandbox slot stayed taken for QUEUE_TIMEOUT_SECONDS."""


def _set_limits() -> None:
    # Best-effort: RLIMIT_AS in particular is not reliably settable on macOS
    # (used for local dev), but both limits apply on Linux (the deployment
    # target). Either way, the parent's watchdog still bounds a worker that
    # hangs instead of being killed for CPU/memory.
    for res, limit in ((resource.RLIMIT_AS, MAX_MEMORY_BYTES), (resource.RLIMIT_CPU, MAX_CPU_SECONDS)):
        try:
            resource.setrlimit(res, (limit, limit))
        except (ValueError, OSError):
            pass


def _entrypoint(fn: Callable[..., Any], args: tuple[Any, ...], conn: Any, scratch_dir: str) -> None:
    """Child side. `fn` must return `(meta, blob)`: JSON-serializable
    metadata, and raw bytes or None."""
    try:
        tempfile.tempdir = scratch_dir
        _set_limits()
        meta, blob = fn(*args)
        header = json.dumps({"status": "ok", "meta": meta, "has_blob": blob is not None}).encode()
    except Exception as e:  # noqa: BLE001 - any worker failure must reach the parent
        header = json.dumps({"status": "error", "message": str(e), "kind": type(e).__name__}).encode()
        blob = None
    try:
        conn.send_bytes(header)
        if blob is not None:
            conn.send_bytes(blob)
    finally:
        conn.close()


def _parse_header(raw: bytes) -> dict[str, Any]:
    try:
        header = json.loads(raw)
    except ValueError as e:
        raise SandboxError("PDF processing returned a malformed result") from e
    if not isinstance(header, dict) or header.get("status") not in ("ok", "error"):
        raise SandboxError("PDF processing returned a malformed result")
    if header["status"] == "error":
        message, kind = header.get("message"), header.get("kind")
        raise SandboxError(
            message if isinstance(message, str) else "PDF processing failed",
            kind=kind if isinstance(kind, str) else None,
        )
    return header


def run_isolated(fn: Callable[..., Any], *args: Any) -> tuple[Any, bytes | None]:
    """Runs fn(*args) to completion in an isolated subprocess and returns
    its `(meta, blob)` result. `fn` and `args` must be picklable (spawn
    re-imports the target module in the child) and must not rely on any
    state besides their arguments -- the whole point is that the child owns
    nothing the parent needs back if it dies. `meta` is untrusted data:
    validate it before use.
    """
    if not _SLOTS.acquire(timeout=QUEUE_TIMEOUT_SECONDS):
        raise SandboxBusyError("server busy, please retry in a moment")
    scratch_dir = tempfile.mkdtemp(prefix="glyph-", dir=_SCRATCH_ROOT)
    parent_conn, child_conn = _CTX.Pipe(duplex=False)
    proc = _CTX.Process(target=_entrypoint, args=(fn, args, child_conn, scratch_dir), daemon=True)
    timed_out = threading.Event()

    def _watchdog() -> None:
        # Killing the child closes its end of the pipe, which unblocks a
        # recv_bytes() stuck mid-frame (a child that sent a length prefix
        # and then stalled) with EOFError.
        timed_out.set()
        proc.kill()

    timer = threading.Timer(TIMEOUT_SECONDS, _watchdog)
    try:
        proc.start()
        child_conn.close()
        timer.start()
        try:
            header = _parse_header(parent_conn.recv_bytes(MAX_HEADER_BYTES))
            blob = parent_conn.recv_bytes(MAX_RESULT_BYTES) if header.get("has_blob") is True else None
        except EOFError as e:
            if timed_out.is_set():
                raise SandboxError("PDF processing timed out") from e
            raise SandboxError("PDF processing crashed (out of memory or CPU limit exceeded)") from e
        except OSError as e:  # recv_bytes: frame longer than maxlength
            raise SandboxError("PDF processing result too large") from e
        return header.get("meta"), blob
    finally:
        timer.cancel()
        parent_conn.close()
        if proc.pid is not None:  # start() succeeded
            if proc.is_alive():
                proc.kill()
            proc.join(2)
        shutil.rmtree(scratch_dir, ignore_errors=True)
        _SLOTS.release()


def _noop() -> tuple[dict, None]:
    return {}, None


def warm_up() -> None:
    """Start the forkserver and preload the engine now (at API startup)
    rather than on the first visitor's request."""
    run_isolated(_noop)

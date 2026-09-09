"""Runs untrusted-PDF processing in a throwaway subprocess.

PyMuPDF is a C library parsing files nobody here controls the origin of.
A malformed or adversarial PDF that segfaults, OOMs, or infinite-loops the
process handling it would otherwise take down the whole API (and every other
in-flight request) with it. Every call that touches PDF bytes we didn't
generate ourselves goes through `run_isolated`: a fresh `spawn`-ed process
per call, with hard memory/CPU/wall-clock limits, so the worst a hostile PDF
can do is waste one short-lived process.

`spawn` (not `fork`) deliberately: fork would copy the parent's file
descriptors and already-imported C extension state, which defeats the
purpose of isolation and is unsafe to combine with threads (uvicorn's).
"""

from __future__ import annotations

import multiprocessing as mp
import os
import resource
from typing import Any, Callable

_CTX = mp.get_context("spawn")

MAX_MEMORY_BYTES = int(os.environ.get("SANDBOX_MAX_MEMORY_MB", "512")) * 1024 * 1024
MAX_CPU_SECONDS = int(os.environ.get("SANDBOX_MAX_CPU_SECONDS", "8"))
TIMEOUT_SECONDS = int(os.environ.get("SANDBOX_TIMEOUT_SECONDS", "15"))


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


def _set_limits() -> None:
    # Best-effort: RLIMIT_AS in particular is not reliably settable on macOS
    # (used for local dev), but both limits apply on Linux (the deployment
    # target). Either way, TIMEOUT_SECONDS in the parent still bounds a
    # worker that hangs instead of being killed for CPU/memory.
    for res, limit in ((resource.RLIMIT_AS, MAX_MEMORY_BYTES), (resource.RLIMIT_CPU, MAX_CPU_SECONDS)):
        try:
            resource.setrlimit(res, (limit, limit))
        except (ValueError, OSError):
            pass


def _entrypoint(fn: Callable[..., Any], args: tuple[Any, ...], conn: Any) -> None:
    try:
        _set_limits()
        result = fn(*args)
        conn.send(("ok", result, None))
    except Exception as e:  # noqa: BLE001 - any worker failure must reach the parent
        conn.send(("error", str(e), type(e).__name__))
    finally:
        conn.close()


def run_isolated(fn: Callable[..., Any], *args: Any) -> Any:
    """Runs fn(*args) to completion in an isolated subprocess and returns
    its result. `fn` and `args` must be picklable (spawn re-imports the
    target module in the child) and must not rely on any state besides
    their arguments -- the whole point is that the child owns nothing the
    parent needs back if it dies.
    """
    parent_conn, child_conn = _CTX.Pipe(duplex=False)
    proc = _CTX.Process(target=_entrypoint, args=(fn, args, child_conn), daemon=True)
    proc.start()
    child_conn.close()

    try:
        if not parent_conn.poll(TIMEOUT_SECONDS):
            proc.terminate()
            proc.join(2)
            if proc.is_alive():
                proc.kill()
                proc.join()
            raise SandboxError("PDF processing timed out")

        try:
            status, payload, kind = parent_conn.recv()
        except EOFError as e:
            proc.join(2)
            raise SandboxError("PDF processing crashed (out of memory or CPU limit exceeded)") from e

        proc.join(2)
        if status == "ok":
            return payload
        raise SandboxError(payload, kind=kind)
    finally:
        parent_conn.close()

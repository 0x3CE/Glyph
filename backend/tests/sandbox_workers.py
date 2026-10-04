"""Worker functions for test_hardening.py's sandbox tests. They live in their
own importable module because `spawn` re-imports a worker by module name in
the child process."""

from __future__ import annotations

import os
import pickle
import tempfile
import time


def ok(value):
    return {"value": value}, b"blob"


def returns_python_object():
    # Not JSON-serializable: must surface as a clean SandboxError, never be
    # pickled across to the parent.
    return {"value": object()}, None


def huge_blob(size):
    return {}, b"x" * size


def hang():
    time.sleep(60)
    return {}, None


def raises_lookup():
    raise LookupError("block not found")


def writes_scratch_file():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    return {"path": path, "dir": tempfile.gettempdir()}, None


def sends_raw_pickle(conn_marker_path):
    """Simulates a compromised child: tries to make the parent unpickle."""

    class Evil:
        def __reduce__(self):
            return (open, (conn_marker_path, "w"))

    return {"note": "irrelevant"}, pickle.dumps(Evil())

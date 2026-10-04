"""Tests for the resource and isolation bounds around the editing engine:
the sandbox protocol (`app.isolation`) and the in-memory document store
(`app.documents`). Run with the rest of the suite:

    .venv/bin/python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import pickle
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sandbox_workers  # noqa: E402

from app import documents, isolation  # noqa: E402
from app.isolation import SandboxBusyError, SandboxError, run_isolated  # noqa: E402


class SandboxProtocolTests(unittest.TestCase):
    def test_returns_json_meta_and_raw_blob(self):
        meta, blob = run_isolated(sandbox_workers.ok, [1, 2])
        self.assertEqual(meta, {"value": [1, 2]})
        self.assertEqual(blob, b"blob")

    def test_worker_exception_keeps_its_kind(self):
        with self.assertRaises(SandboxError) as ctx:
            run_isolated(sandbox_workers.raises_lookup)
        self.assertEqual(ctx.exception.kind, "LookupError")

    def test_non_json_result_is_an_error_not_a_pickle(self):
        with self.assertRaises(SandboxError) as ctx:
            run_isolated(sandbox_workers.returns_python_object)
        self.assertEqual(ctx.exception.kind, "TypeError")

    def test_parent_never_unpickles_the_blob(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "pwned")
            _meta, blob = run_isolated(sandbox_workers.sends_raw_pickle, marker)
            self.assertFalse(os.path.exists(marker))
            self.assertIsInstance(blob, bytes)

    def test_pickle_in_place_of_the_json_header_is_rejected(self):
        # What a compromised child could write straight into the pipe.
        with self.assertRaises(SandboxError):
            isolation._parse_header(pickle.dumps({"status": "ok", "meta": {}}))

    def test_oversized_result_is_refused(self):
        with mock.patch.object(isolation, "MAX_RESULT_BYTES", 1024):
            with self.assertRaises(SandboxError) as ctx:
                run_isolated(sandbox_workers.huge_blob, 10_000)
        self.assertIn("too large", str(ctx.exception))

    def test_hanging_worker_is_killed(self):
        with mock.patch.object(isolation, "TIMEOUT_SECONDS", 1):
            with self.assertRaises(SandboxError) as ctx:
                run_isolated(sandbox_workers.hang)
        self.assertIn("timed out", str(ctx.exception))

    def test_scratch_directory_is_private_and_removed(self):
        meta, _ = run_isolated(sandbox_workers.writes_scratch_file)
        self.assertTrue(meta["path"].startswith(meta["dir"]))
        self.assertIn("glyph-", meta["dir"])
        self.assertFalse(os.path.exists(meta["dir"]))

    def test_busy_when_every_slot_is_taken(self):
        slots = threading.BoundedSemaphore(1)
        slots.acquire()
        with mock.patch.object(isolation, "_SLOTS", slots), mock.patch.object(isolation, "QUEUE_TIMEOUT_SECONDS", 0.1):
            with self.assertRaises(SandboxBusyError):
                run_isolated(sandbox_workers.ok, 1)

    def test_slot_is_released_after_a_failure(self):
        slots = threading.BoundedSemaphore(1)
        with mock.patch.object(isolation, "_SLOTS", slots):
            with self.assertRaises(SandboxError):
                run_isolated(sandbox_workers.raises_lookup)
            self.assertEqual(run_isolated(sandbox_workers.ok, 1)[0], {"value": 1})


class DocumentStoreTests(unittest.TestCase):
    def setUp(self):
        self._store = mock.patch.object(documents, "_STORE", {})
        self._store.start()

    def tearDown(self):
        self._store.stop()

    def test_idle_documents_expire(self):
        with mock.patch.object(documents.time, "monotonic", return_value=1000.0):
            doc = documents.create(b"pdf")
        later = 1000.0 + documents.DOCUMENT_TTL_SECONDS + 1
        with mock.patch.object(documents.time, "monotonic", return_value=later):
            self.assertIsNone(documents.current(doc))

    def test_access_keeps_a_document_alive(self):
        with mock.patch.object(documents.time, "monotonic", return_value=1000.0):
            doc = documents.create(b"pdf")
        half = documents.DOCUMENT_TTL_SECONDS * 0.75
        with mock.patch.object(documents.time, "monotonic", return_value=1000.0 + half):
            self.assertEqual(documents.current(doc), b"pdf")
        with mock.patch.object(documents.time, "monotonic", return_value=1000.0 + 2 * half):
            self.assertEqual(documents.current(doc), b"pdf")

    def test_history_is_capped_per_document_oldest_first(self):
        with mock.patch.object(documents, "DOCUMENT_MAX_BYTES", 30):
            doc = documents.create(b"a" * 10)
            for c in b"bcde":
                documents.push(doc, bytes([c]) * 10)
            state = documents._STORE[doc]
            self.assertEqual(state.history, [b"c" * 10, b"d" * 10, b"e" * 10])
            self.assertEqual(state.current, b"e" * 10)
            self.assertEqual(state.cursor, 2)

    def test_store_refuses_new_documents_when_full(self):
        with mock.patch.object(documents, "STORE_MAX_BYTES", 25):
            documents.create(b"a" * 20)
            with self.assertRaises(documents.StoreFullError):
                documents.create(b"b" * 10)

    def test_document_count_is_capped(self):
        with mock.patch.object(documents, "MAX_DOCUMENTS", 2):
            documents.create(b"a")
            documents.create(b"b")
            with self.assertRaises(documents.StoreFullError):
                documents.create(b"c")

    def test_edit_gives_up_own_undo_history_before_refusing(self):
        with mock.patch.object(documents, "STORE_MAX_BYTES", 35):
            doc = documents.create(b"a" * 10)
            documents.push(doc, b"b" * 10)
            documents.push(doc, b"c" * 10)  # 30 bytes stored
            documents.push(doc, b"d" * 10)  # would be 40: undo history dropped
            self.assertEqual(documents._STORE[doc].history, [b"c" * 10, b"d" * 10])
            with self.assertRaises(documents.StoreFullError):
                documents.push(doc, b"e" * 30)

    def test_push_to_a_deleted_document_is_refused(self):
        doc = documents.create(b"a")
        documents.delete(doc)
        self.assertFalse(documents.push(doc, b"b"))


if __name__ == "__main__":
    unittest.main()

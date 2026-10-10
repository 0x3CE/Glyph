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
    def test_children_are_forked_from_a_preloaded_server(self):
        # `spawn` re-imported the whole engine in every child: ~3 s per
        # operation on Render. Don't silently go back to it.
        self.assertEqual(isolation._CTX.get_start_method(), "forkserver")

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

    def test_one_owner_can_have_at_most_ten_documents_open(self):
        self.assertEqual(documents.MAX_DOCUMENTS_PER_OWNER, 10)
        ids = [documents.create(b"pdf", owner="alice") for _ in range(10)]
        with self.assertRaises(documents.TooManyDocumentsError):
            documents.create(b"pdf", owner="alice")
        documents.create(b"pdf", owner="bob")  # someone else isn't affected
        documents.delete(ids[0])  # closing a tab frees a slot
        documents.create(b"pdf", owner="alice")

    def test_expired_documents_free_their_owner_slots(self):
        with mock.patch.object(documents, "MAX_DOCUMENTS_PER_OWNER", 1):
            with mock.patch.object(documents.time, "monotonic", return_value=1000.0):
                documents.create(b"pdf", owner="alice")
            later = 1000.0 + documents.DOCUMENT_TTL_SECONDS + 1
            with mock.patch.object(documents.time, "monotonic", return_value=later):
                documents.create(b"pdf", owner="alice")

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


class ClientKeyTests(unittest.TestCase):
    """The quota's notion of "one visitor"."""

    def _request(self, headers: dict[str, str], host: str = "10.0.0.1"):
        from starlette.requests import Request

        raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        return Request({"type": "http", "headers": raw, "client": (host, 1234)})

    def test_visitor_is_the_left_most_forwarded_address(self):
        from app.main import _client_key

        # Vercel writes the visitor's IP; Render appends its own hop.
        a = _client_key(self._request({"X-Forwarded-For": "203.0.113.7, 76.76.21.1"}))
        b = _client_key(self._request({"X-Forwarded-For": "203.0.113.7, 76.76.21.9"}))
        c = _client_key(self._request({"X-Forwarded-For": "198.51.100.2, 76.76.21.1"}))
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_the_ip_itself_is_never_stored(self):
        from app.main import _client_key

        key = _client_key(self._request({"X-Forwarded-For": "203.0.113.7"}))
        self.assertNotIn("203.0.113.7", key)
        self.assertEqual(len(key), 64)


class ApiGuardTests(unittest.TestCase):
    def test_signature_rectangle_must_be_finite_sane_and_not_inverted(self):
        from app.main import _valid_rect

        self.assertTrue(_valid_rect((100, 400, 300, 460)))
        for bad in [
            (float("nan"), 0, 100, 100),
            (0, 0, float("inf"), 100),
            (0, 0, 1e300, 100),
            (300, 400, 100, 460),  # inverted
            (100, 400, 100, 460),  # empty
        ]:
            self.assertFalse(_valid_rect(bad), bad)

    def test_api_docs_are_off_by_default(self):
        from app import main

        if os.environ.get("ENABLE_API_DOCS") == "1":
            self.skipTest("docs explicitly enabled in this environment")
        self.assertIsNone(main.app.docs_url)
        self.assertIsNone(main.app.openapi_url)

    def test_uploads_past_the_concurrency_cap_get_a_503(self):
        import asyncio

        from fastapi import HTTPException

        from app import main

        async def scenario():
            with mock.patch.object(main, "_UPLOAD_SLOTS", asyncio.Semaphore(1)), \
                 mock.patch.object(main, "UPLOAD_QUEUE_TIMEOUT_SECONDS", 0.05):
                async with main._upload_slot():
                    with self.assertRaises(HTTPException) as ctx:
                        async with main._upload_slot():
                            pass
                    self.assertEqual(ctx.exception.status_code, 503)
                async with main._upload_slot():  # released: free again
                    pass

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()

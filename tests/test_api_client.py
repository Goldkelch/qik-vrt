#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Client-side transport-boundary tests for the local dispatch adapter."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import qikvrt_api_client as client  # noqa: E402


class ApiClientTests(unittest.TestCase):
    def invoke(self, *arguments: str) -> int:
        argv = ["qikvrt_api_client.py", "--owner", "owner", "--repo", "repo", *arguments]
        with mock.patch.object(sys, "argv", argv):
            return client.main()

    def test_non_loopback_cleartext_endpoint_is_rejected_before_network(self) -> None:
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    self.invoke(
                        "--base-url", "http://example.test:8766",
                        "--operation", "release_status",
                        "--request-id", "cleartext-rejected",
                    )
        self.assertEqual(raised.exception.code, 2)

    def test_transport_failure_returns_blocking_exit_without_traceback(self) -> None:
        opener = mock.Mock()
        opener.open.side_effect = urllib.error.URLError("connection refused")
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with mock.patch.object(
                client.urllib.request,
                "build_opener",
                return_value=opener,
            ):
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    result = self.invoke(
                        "--operation", "release_status",
                        "--request-id", "transport-failure",
                    )
        self.assertEqual(result, 1)
        self.assertIn("BLOCK API request failed", stderr.getvalue())

    def test_redirects_are_never_followed(self) -> None:
        handler = client.NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(
                mock.Mock(), None, 302, "Found", {}, "https://other.invalid/"
            )
        )

    def test_github_workflow_dispatch_204_is_transport_continue(self) -> None:
        class Response:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self, limit):
                return b""

        opener = mock.Mock()
        opener.open.return_value = Response()
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    result = self.invoke(
                        "--base-url", "https://api.github.com",
                        "--operation", "release_status",
                        "--request-id", "github-204",
                    )
        self.assertEqual(result, 20)
        receipt = json.loads(stdout.getvalue())
        self.assertEqual(receipt["status"], "TRANSPORT_ACCEPTED_ASYNC")
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["ordinary_release"])

    def test_github_dispatch_payload_is_bounded_before_network(self) -> None:
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with mock.patch.object(
                client,
                "read_regular_file",
                return_value=b"x" * (40 * 1024),
            ):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        self.invoke(
                            "--base-url", "https://api.github.com",
                            "--operation", "ingest",
                            "--request-id", "oversized-github-dispatch",
                            "--payload-file", "ignored-by-mock.bin",
                        )
        self.assertEqual(raised.exception.code, 2)

    def test_repository_dispatch_uses_fixed_event_envelope(self) -> None:
        class Response:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self, limit):
                return b""

        opener = mock.Mock()
        opener.open.return_value = Response()
        with mock.patch.dict(os.environ, {"QIKVRT_API_TOKEN": "test-token"}, clear=False):
            with mock.patch.object(client.urllib.request, "build_opener", return_value=opener):
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    result = self.invoke(
                        "--base-url", "https://api.github.com",
                        "--dispatch-kind", "repository",
                        "--operation", "release_status",
                        "--request-id", "repository-dispatch",
                    )
        self.assertEqual(result, 20)
        request = opener.open.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/repos/owner/repo/dispatches"))
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["event_type"], "qikvrt_mesh_api")
        self.assertEqual(body["client_payload"]["request_id"], "repository-dispatch")
        receipt = json.loads(stdout.getvalue())
        self.assertEqual(receipt["transport"], "github_repository_dispatch")

    def test_file_reader_rejects_symlinks_and_oversize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.bin"
            target.write_bytes(b"12345")
            link = root / "link.bin"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(OSError):
                    client.read_regular_file(link, max_bytes=10)
            with self.assertRaisesRegex(OSError, "exceeds"):
                client.read_regular_file(target, max_bytes=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

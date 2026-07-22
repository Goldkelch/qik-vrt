#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline tests for the two-phase GitHub Actions Zenodo client."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import pathlib
import re
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from tools import qikvrt_zenodo_actions as zenodo  # noqa: E402


TOKEN = "z" * 64
PAPER_DOI = "10.5281/zenodo.301"
SOFTWARE_DOI = "10.5281/zenodo.302"


def json_response(status: int, value: object) -> zenodo.HttpResponse:
    return zenodo.HttpResponse(
        status=status,
        headers={"Content-Type": "application/json"},
        body=json.dumps(value, sort_keys=True).encode("utf-8"),
    )


class FakeZenodoTransport:
    """Small stateful legacy-API simulation; it never uses the network."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bytes | None]] = []
        self.publish_status = {301: 202, 302: 409}
        self.poll_misses = {301: 1, 302: 0}
        self.published: set[int] = set()
        self.depositions: dict[int, dict[str, object]] = {
            301: self._deposition(301, 300, PAPER_DOI, "paper-bucket"),
            302: self._deposition(
                302, zenodo.EXPECTED_SOFTWARE_CONCEPT_RECORD_ID,
                SOFTWARE_DOI, "software-bucket"
            ),
        }
        self.depositions[301]["files"] = [
            self._file("stale-paper.txt", b"old", "paper-bucket", "p-old")
        ]
        self.depositions[302]["files"] = [
            self._file("inherited-v8.33.zip", b"old", "software-bucket", "s-old-1"),
            self._file("inherited-v8.33.pdf", b"old", "software-bucket", "s-old-2"),
        ]

    @staticmethod
    def _deposition(record_id: int, concept: int, doi: str, bucket: str) -> dict[str, object]:
        return {
            "id": record_id,
            "conceptrecid": concept,
            "doi": doi,
            "metadata": {"prereserve_doi": {"doi": doi}},
            "files": [],
            "links": {
                "bucket": f"https://zenodo.org/api/files/{bucket}",
                "self": f"https://zenodo.org/api/deposit/depositions/{record_id}",
            },
        }

    @staticmethod
    def _file(name: str, data: bytes, bucket: str, file_id: str) -> dict[str, object]:
        return {
            "id": file_id,
            "filename": name,
            "filesize": len(data),
            "checksum": "md5:" + hashlib.md5(data).hexdigest(),  # noqa: S324
            "_data": data,
            "links": {
                "self": f"https://zenodo.org/api/files/{bucket}/{name}",
                "download": f"https://zenodo.org/api/files/{bucket}/{name}",
            },
        }

    @staticmethod
    def _public(value: dict[str, object]) -> dict[str, object]:
        result = copy.deepcopy(value)
        metadata = result["metadata"]  # type: ignore[index]
        metadata.pop("prereserve_doi", None)
        upload_type = metadata.pop("upload_type", None)
        publication_type = metadata.pop("publication_type", None)
        if upload_type is not None:
            resource_type: dict[str, object] = {"type": upload_type}
            if publication_type is not None:
                resource_type["subtype"] = publication_type
            metadata["resource_type"] = resource_type
        if isinstance(metadata.get("license"), str):
            metadata["license"] = {"id": metadata["license"]}
        public_files: list[dict[str, object]] = []
        for item in result["files"]:  # type: ignore[index]
            public_item = dict(item)
            public_item["key"] = public_item.pop("filename")
            public_item["size"] = public_item.pop("filesize")
            public_item.pop("_data", None)
            public_files.append(public_item)
        result["files"] = public_files
        return result

    @staticmethod
    def _clean(value: dict[str, object]) -> dict[str, object]:
        result = copy.deepcopy(value)
        result.pop("_data", None)
        for item in result.get("files", []):  # type: ignore[union-attr]
            item.pop("_data", None)
        return result

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        max_response_bytes: int = zenodo.MAX_RESPONSE_BYTES,
    ) -> zenodo.HttpResponse:
        del content_type, max_response_bytes
        path = urllib.parse.urlsplit(url).path
        method = method.upper()
        self.calls.append((method, path, body))

        if method == "GET" and path == "/api/records/21488116/versions/latest":
            return zenodo.HttpResponse(
                301,
                {"Location": "https://zenodo.org/api/records/21488116"},
                b'{"status": 301}',
            )
        if method == "GET" and path == "/api/records/21488116":
            return json_response(200, {
                "id": 21488116,
                "conceptrecid": 21488115,
                "doi": "10.5281/zenodo.21488116",
                "links": {
                    "latest": "https://zenodo.org/api/records/21488116/versions/latest"
                },
                "metadata": {
                    "relations": {"version": [{"index": 0, "is_last": True}]}
                },
            })
        if method == "POST" and path == "/api/deposit/depositions":
            return json_response(201, self._clean(self.depositions[301]))
        if method == "POST" and path == "/api/deposit/depositions/21488116/actions/newversion":
            # Deliberately misleading response id proves that latest_draft is followed.
            return json_response(201, {
                "id": 999999,
                "links": {
                    "latest_draft": "https://zenodo.org/api/deposit/depositions/302"
                },
            })

        match = re.fullmatch(r"/api/deposit/depositions/(\d+)", path)
        if match:
            record_id = int(match.group(1))
            if record_id in self.published:
                return json_response(404, {"message": "not an editable draft"})
            if record_id not in self.depositions:
                return json_response(404, {"message": "not found"})
            if method == "GET":
                return json_response(200, self._clean(self.depositions[record_id]))
            if method == "PUT":
                payload = json.loads((body or b"{}").decode("utf-8"))
                metadata = copy.deepcopy(payload["metadata"])
                if metadata.get("prereserve_doi") is True:
                    metadata["prereserve_doi"] = {
                        "doi": self.depositions[record_id]["doi"]
                    }
                self.depositions[record_id]["metadata"] = metadata
                return json_response(200, self._clean(self.depositions[record_id]))

        publish = re.fullmatch(
            r"/api/deposit/depositions/(\d+)/actions/publish", path
        )
        if method == "POST" and publish:
            record_id = int(publish.group(1))
            self.published.add(record_id)
            return json_response(self.publish_status[record_id], {"status": "queued"})

        record = re.fullmatch(r"/api/records/(\d+)", path)
        if method == "GET" and record:
            record_id = int(record.group(1))
            if record_id not in self.published:
                return json_response(404, {"message": "not published"})
            if self.poll_misses[record_id] > 0:
                self.poll_misses[record_id] -= 1
                return json_response(202, {"status": "indexing"})
            return json_response(200, self._public(self.depositions[record_id]))

        if path.startswith("/api/files/"):
            parts = path.split("/", 4)
            if len(parts) != 5:
                return json_response(404, {"message": "not found"})
            bucket, name = parts[3], urllib.parse.unquote(parts[4])
            deposition = next(
                value for value in self.depositions.values()
                if str(value["links"]["bucket"]).endswith("/" + bucket)  # type: ignore[index]
            )
            existing = next(
                (item for item in deposition["files"] if item["filename"] == name),  # type: ignore[index]
                None,
            )
            if method == "DELETE":
                if existing is None:
                    return json_response(404, {"message": "already absent"})
                deposition["files"].remove(existing)  # type: ignore[union-attr]
                return zenodo.HttpResponse(204, {}, b"")
            if method == "PUT":
                if existing is not None:
                    deposition["files"].remove(existing)  # type: ignore[union-attr]
                item = self._file(name, body or b"", bucket, "new-" + name)
                deposition["files"].append(item)  # type: ignore[union-attr]
                return json_response(201, self._clean(item))
            if method == "GET" and existing is not None:
                return zenodo.HttpResponse(200, {"Content-Type": "application/octet-stream"}, existing["_data"])  # type: ignore[arg-type]

        return json_response(500, {"message": f"unhandled fake request {method} {path}"})


class ZenodoActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        self.paper_path = self.root / "paper.txt"
        self.software_path = self.root / "software.tar.gz"
        self.paper_path.write_text("reservation input\n", encoding="utf-8")
        self.software_path.write_bytes(b"reservation software input\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def entry(path: pathlib.Path, root: pathlib.Path, name: str | None = None) -> dict[str, object]:
        data = path.read_bytes()
        return {
            "path": path.relative_to(root).as_posix(),
            "name": name or path.name,
            "size": len(data),
            "md5": hashlib.md5(data).hexdigest(),  # noqa: S324
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def manifest(self, *, final: bool = False) -> dict[str, object]:
        paper_metadata: dict[str, object] = {
            "title": "EFFECT_ACK scientific working paper",
            "version": "1.0.0",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "upload_type": "publication",
            "publication_type": "workingpaper",
            "prereserve_doi": True,
            "license": "cc-by-nc-nd-4.0",
        }
        software_metadata: dict[str, object] = {
            "title": "QIK-VRT EFFECT_ACK software",
            "version": "2026.07.22-effect-ack-universality-1.0.0",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "upload_type": "software",
            "license": "other-open",
        }
        if final:
            paper_metadata["related_identifiers"] = [
                {"identifier": SOFTWARE_DOI, "relation": "documents", "scheme": "doi"}
            ]
            software_metadata["related_identifiers"] = [
                {"identifier": PAPER_DOI, "relation": "isSupplementTo", "scheme": "doi"}
            ]
        value: dict[str, object] = {
            "schema_version": 1,
            "release_id": zenodo.EXPECTED_RELEASE_ID,
            "authorization": {
                "repositories": list(zenodo.EXPECTED_REPOSITORIES),
                "tag": zenodo.EXPECTED_TAG,
            },
            "paper": {
                "metadata": paper_metadata,
                "files": [self.entry(self.paper_path, self.root)],
            },
            "software": {
                "source_record_id": zenodo.EXPECTED_SOFTWARE_SOURCE_RECORD_ID,
                "concept_record_id": zenodo.EXPECTED_SOFTWARE_CONCEPT_RECORD_ID,
                "metadata": software_metadata,
                "files": [self.entry(self.software_path, self.root)],
            },
        }
        if final:
            value["reserved_dois"] = {"paper": PAPER_DOI, "software": SOFTWARE_DOI}
        return value

    def client(self, transport: FakeZenodoTransport) -> zenodo.ZenodoClient:
        return zenodo.ZenodoClient(
            TOKEN, zenodo.DEFAULT_BASE_URL, transport,
            poll_attempts=4, poll_interval=0, sleeper=lambda _: None,
        )

    def reserve_once(
        self, transport: FakeZenodoTransport
    ) -> tuple[dict[str, object], pathlib.Path, dict[str, object]]:
        raw_manifest = self.manifest()
        manifest = zenodo.validate_manifest(raw_manifest, self.root, final=False)
        raw = json.dumps(raw_manifest, sort_keys=True).encode("utf-8")
        result_path = self.root / "reservation.json"
        result = zenodo.reserve(
            self.client(transport), manifest, hashlib.sha256(raw).hexdigest(),
            self.root, result_path
        )
        return result, result_path, raw_manifest

    def test_only_allowlisted_https_api_origins_are_accepted(self) -> None:
        self.assertEqual(
            zenodo.validate_base_url("https://zenodo.org/api/"),
            "https://zenodo.org/api",
        )
        self.assertEqual(
            zenodo.validate_base_url("https://sandbox.zenodo.org/api"),
            "https://sandbox.zenodo.org/api",
        )
        for invalid in (
            "http://zenodo.org/api",
            "https://evil.example/api",
            "https://zenodo.org.evil.example/api",
            "https://zenodo.org/api?access_token=secret",
            "https://user@zenodo.org/api",
            "https://zenodo.org/records/1",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(zenodo.ZenodoError):
                zenodo.validate_base_url(invalid)
        with self.assertRaises(zenodo.ZenodoError):
            zenodo.validate_response_url(
                "https://evil.example/api/files/a", zenodo.DEFAULT_BASE_URL
            )

    def test_redirects_are_never_followed_and_cannot_relay_auth(self) -> None:
        handler = zenodo.NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(
                mock.Mock(), None, 302, "Found", {}, "https://evil.example/steal"
            )
        )
        opener = mock.Mock()
        opener.open.side_effect = urllib.error.HTTPError(
            "https://zenodo.org/api/records/1", 302, "Found",
            {"Location": "https://evil.example/steal"}, io.BytesIO(b"{}")
        )
        transport = zenodo.HttpTransport(TOKEN, zenodo.DEFAULT_BASE_URL)
        transport._opener = opener  # type: ignore[attr-defined]
        response = transport.request("GET", "https://zenodo.org/api/records/1")
        self.assertEqual(response.status, 302)
        self.assertEqual(opener.open.call_count, 1)

        class MaliciousRedirectTransport:
            def __init__(self) -> None:
                self.calls = 0

            def request(self, *args: object, **kwargs: object) -> zenodo.HttpResponse:
                del args, kwargs
                self.calls += 1
                return zenodo.HttpResponse(
                    302, {"Location": "https://evil.example/api/steal"}, b"{}"
                )

        malicious = MaliciousRedirectTransport()
        client = zenodo.ZenodoClient(TOKEN, zenodo.DEFAULT_BASE_URL, malicious)
        with self.assertRaisesRegex(zenodo.ZenodoError, "non-allowlisted"):
            client.get_with_validated_redirects("/api/records/1/versions/latest")
        self.assertEqual(malicious.calls, 1)

    def test_reserve_checks_live_latest_and_follows_latest_draft(self) -> None:
        transport = FakeZenodoTransport()
        result, path, _ = self.reserve_once(transport)
        self.assertEqual(result["phase"], "reserved")
        self.assertEqual(result["paper"]["doi"], PAPER_DOI)
        self.assertEqual(result["software"]["deposition_id"], 302)
        self.assertNotEqual(result["software"]["deposition_id"], 999999)
        self.assertRegex(result["authorization_mac"], r"^[0-9a-f]{64}$")
        serialized = path.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, serialized)
        paths = [(method, path) for method, path, _ in transport.calls]
        self.assertLess(
            paths.index(("GET", "/api/records/21488116")),
            paths.index(("POST", "/api/deposit/depositions")),
        )
        self.assertIn(("GET", "/api/deposit/depositions/302"), paths)

    def test_reserve_is_idempotent_and_does_not_create_duplicate_deposits(self) -> None:
        transport = FakeZenodoTransport()
        result, result_path, raw_manifest = self.reserve_once(transport)
        creation_count = sum(method == "POST" for method, _, _ in transport.calls)
        manifest = zenodo.validate_manifest(raw_manifest, self.root, final=False)
        raw = json.dumps(raw_manifest, sort_keys=True).encode("utf-8")
        repeated = zenodo.reserve(
            self.client(transport), manifest, hashlib.sha256(raw).hexdigest(),
            self.root, result_path
        )
        self.assertEqual(result, repeated)
        self.assertEqual(
            sum(method == "POST" for method, _, _ in transport.calls), creation_count
        )

    def test_newversion_409_resumes_from_source_latest_draft_link(self) -> None:
        class ExistingDraftTransport(FakeZenodoTransport):
            def request(
                self, method: str, url: str, **kwargs: object
            ) -> zenodo.HttpResponse:
                path = urllib.parse.urlsplit(url).path
                if (
                    method == "POST"
                    and path == "/api/deposit/depositions/21488116/actions/newversion"
                ):
                    self.calls.append((method, path, kwargs.get("body")))  # type: ignore[arg-type]
                    return json_response(409, {"message": "draft already exists"})
                if method == "GET" and path == "/api/deposit/depositions/21488116":
                    self.calls.append((method, path, None))
                    return json_response(200, {
                        "id": 21488116,
                        "links": {
                            "latest_draft": "https://zenodo.org/api/deposit/depositions/302"
                        },
                    })
                return super().request(method, url, **kwargs)

        transport = ExistingDraftTransport()
        result, _, _ = self.reserve_once(transport)
        self.assertEqual(result["software"]["deposition_id"], 302)
        self.assertIn(
            ("GET", "/api/deposit/depositions/21488116"),
            [(method, path) for method, path, _ in transport.calls],
        )

    def test_asynchronous_creation_and_newversion_are_polled(self) -> None:
        class AsyncTransport(FakeZenodoTransport):
            def __init__(self) -> None:
                super().__init__()
                self.source_polls = 0

            def request(
                self, method: str, url: str, **kwargs: object
            ) -> zenodo.HttpResponse:
                path = urllib.parse.urlsplit(url).path
                if method == "POST" and path == "/api/deposit/depositions":
                    self.calls.append((method, path, kwargs.get("body")))  # type: ignore[arg-type]
                    return zenodo.HttpResponse(
                        202,
                        {"Location": "https://zenodo.org/api/deposit/depositions/301"},
                        b"{}",
                    )
                if (
                    method == "POST"
                    and path == "/api/deposit/depositions/21488116/actions/newversion"
                ):
                    self.calls.append((method, path, kwargs.get("body")))  # type: ignore[arg-type]
                    return json_response(202, {"status": "queued"})
                if method == "GET" and path == "/api/deposit/depositions/21488116":
                    self.calls.append((method, path, None))
                    self.source_polls += 1
                    if self.source_polls == 1:
                        return json_response(202, {"status": "creating"})
                    return json_response(200, {
                        "id": 21488116,
                        "links": {
                            "latest_draft": "https://zenodo.org/api/deposit/depositions/302"
                        },
                    })
                return super().request(method, url, **kwargs)

        transport = AsyncTransport()
        result, _, _ = self.reserve_once(transport)
        self.assertEqual(result["paper"]["deposition_id"], 301)
        self.assertEqual(result["software"]["deposition_id"], 302)
        self.assertEqual(transport.source_polls, 2)

    def test_live_latest_or_concept_mismatch_blocks_before_deposition_creation(self) -> None:
        class MismatchTransport(FakeZenodoTransport):
            def request(self, method: str, url: str, **kwargs: object) -> zenodo.HttpResponse:
                path = urllib.parse.urlsplit(url).path
                if method == "GET" and path == "/api/records/21488116":
                    return json_response(200, {
                        "id": 21488116,
                        "conceptrecid": 21488115,
                        "links": {"latest": "https://zenodo.org/api/records/20712399"},
                    })
                if method == "GET" and path == "/api/records/20712399":
                    return json_response(200, {
                        "id": 20712399,
                        "conceptrecid": 21488115,
                        "links": {"latest": "https://zenodo.org/api/records/20712399"},
                    })
                return super().request(method, url, **kwargs)

        transport = MismatchTransport()
        raw = self.manifest()
        manifest = zenodo.validate_manifest(raw, self.root, final=False)
        with self.assertRaisesRegex(zenodo.ZenodoError, "no longer.*latest"):
            zenodo.reserve(
                self.client(transport), manifest, "0" * 64,
                self.root, self.root / "reservation.json"
            )
        self.assertFalse(any(
            method == "POST" and path == "/api/deposit/depositions"
            for method, path, _ in transport.calls
        ))

    def test_public_record_normalization_preserves_controlled_legacy_semantics(self) -> None:
        legacy = {
            "title": "Actual public-record fixture",
            "version": "1.0.0",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "upload_type": "publication",
            "publication_type": "workingpaper",
            "license": "cc-by-nc-nd-4.0",
            "prereserve_doi": True,
        }
        public = {
            "title": "Actual public-record fixture",
            "version": "1.0.0",
            "creators": [
                {"name": "Lohmann, Ingolf", "affiliation": "Independent researcher"}
            ],
            "resource_type": {
                "title": "Working paper",
                "type": "publication",
                "subtype": "workingpaper",
            },
            "license": {"id": "cc-by-nc-nd-4.0"},
            "doi": "10.5281/zenodo.21482023",
            "relations": {
                "version": [{"index": 0, "is_last": True}]
            },
        }
        self.assertTrue(zenodo._published_metadata_matches(public, legacy))
        changed = copy.deepcopy(public)
        changed["resource_type"]["subtype"] = "article"
        self.assertFalse(zenodo._published_metadata_matches(changed, legacy))

    def test_new_version_prefers_prereserved_doi_over_inherited_legacy_doi(self) -> None:
        value = {
            "doi": "10.5281/zenodo.21488116",
            "metadata": {"prereserve_doi": {"doi": SOFTWARE_DOI}},
        }
        self.assertEqual(
            zenodo._doi_from_deposition(value, "software draft"), SOFTWARE_DOI
        )

    def test_finalize_allows_doi_enrichment_replaces_files_and_publishes_in_order(self) -> None:
        transport = FakeZenodoTransport()
        reservation, reservation_path, _ = self.reserve_once(transport)
        self.paper_path.write_text(
            f"Final paper DOI {PAPER_DOI}; software DOI {SOFTWARE_DOI}\n",
            encoding="utf-8",
        )
        self.software_path.write_bytes(
            f"Final software {SOFTWARE_DOI}; paper {PAPER_DOI}\n".encode("ascii")
        )
        raw_final = self.manifest(final=True)
        final_manifest = zenodo.validate_manifest(raw_final, self.root, final=True)
        final_result = self.root / "published.json"
        outcome = zenodo.finalize(
            self.client(transport), final_manifest,
            hashlib.sha256(json.dumps(raw_final, sort_keys=True).encode()).hexdigest(),
            reservation, self.root, final_result,
        )
        self.assertEqual(outcome["phase"], "published")
        self.assertFalse(outcome["datatracker_submitted"])
        self.assertFalse(outcome["github_release_created"])
        self.assertNotIn(TOKEN, final_result.read_text(encoding="utf-8"))
        paper_names = {item["filename"] for item in transport.depositions[301]["files"]}  # type: ignore[index]
        software_names = {item["filename"] for item in transport.depositions[302]["files"]}  # type: ignore[index]
        self.assertEqual(paper_names, {"paper.txt"})
        self.assertEqual(software_names, {"software.tar.gz"})
        calls = [(method, path) for method, path, _ in transport.calls]
        paper_publish = calls.index(("POST", "/api/deposit/depositions/301/actions/publish"))
        software_publish = calls.index(("POST", "/api/deposit/depositions/302/actions/publish"))
        self.assertLess(paper_publish, software_publish)
        self.assertIn(("DELETE", "/api/files/software-bucket/inherited-v8.33.zip"), calls)
        self.assertIn(("DELETE", "/api/files/software-bucket/inherited-v8.33.pdf"), calls)
        # The 202 paper response was polled through one non-final response.
        self.assertGreaterEqual(
            calls.count(("GET", "/api/records/301")), 2
        )
        self.assertTrue(reservation_path.is_file())

    def test_finalize_is_idempotent_after_both_records_are_published(self) -> None:
        transport = FakeZenodoTransport()
        reservation, _, _ = self.reserve_once(transport)
        self.paper_path.write_text(
            f"{PAPER_DOI} {SOFTWARE_DOI}\n", encoding="utf-8"
        )
        self.software_path.write_text(
            f"{PAPER_DOI} {SOFTWARE_DOI}\n", encoding="utf-8"
        )
        raw_final = self.manifest(final=True)
        manifest = zenodo.validate_manifest(raw_final, self.root, final=True)
        client = self.client(transport)
        zenodo.finalize(
            client, manifest, "1" * 64, reservation, self.root,
            self.root / "published.json",
        )
        publishes_before = sum(
            method == "POST" and path.endswith("/actions/publish")
            for method, path, _ in transport.calls
        )
        zenodo.finalize(
            client, manifest, "1" * 64, reservation, self.root,
            self.root / "published-again.json",
        )
        publishes_after = sum(
            method == "POST" and path.endswith("/actions/publish")
            for method, path, _ in transport.calls
        )
        self.assertEqual(publishes_before, publishes_after)

    def test_submitted_deposition_shape_is_resolved_through_public_record(self) -> None:
        class SubmittedTransport(FakeZenodoTransport):
            def request(
                self, method: str, url: str, **kwargs: object
            ) -> zenodo.HttpResponse:
                path = urllib.parse.urlsplit(url).path
                if method == "GET" and path == "/api/deposit/depositions/301":
                    return json_response(200, {
                        "id": 301, "submitted": True, "state": "done"
                    })
                return super().request(method, url, **kwargs)

        transport = SubmittedTransport()
        transport.published.add(301)
        state, record = self.client(transport).get_deposition_or_record(301)
        self.assertEqual(state, "published")
        self.assertEqual(record["id"], 301)

    def test_final_identity_and_authorization_mutations_are_blocked(self) -> None:
        transport = FakeZenodoTransport()
        reservation, _, _ = self.reserve_once(transport)
        self.paper_path.write_text(f"{PAPER_DOI} {SOFTWARE_DOI}", encoding="utf-8")
        self.software_path.write_text(f"{PAPER_DOI} {SOFTWARE_DOI}", encoding="utf-8")
        base = self.manifest(final=True)
        mutations = {
            "paper title": lambda value: value["paper"]["metadata"].__setitem__("title", "Other"),
            "paper version": lambda value: value["paper"]["metadata"].__setitem__("version", "2.0.0"),
            "software creator": lambda value: value["software"]["metadata"].__setitem__("creators", [{"name": "Other"}]),
            "tag": lambda value: value["authorization"].__setitem__("tag", "v-other"),
            "repository": lambda value: value["authorization"].__setitem__("repositories", ["Other/repo"]),
            "source": lambda value: value["software"].__setitem__("source_record_id", 20712302),
            "concept": lambda value: value["software"].__setitem__("concept_record_id", 20712302),
        }
        for label, mutate in mutations.items():
            value = copy.deepcopy(base)
            mutate(value)
            with self.subTest(label=label), self.assertRaises(zenodo.ZenodoError):
                manifest = zenodo.validate_manifest(value, self.root, final=True)
                zenodo.finalize(
                    self.client(transport), manifest, "2" * 64,
                    reservation, self.root, self.root / f"blocked-{label}.json"
                )

    def test_reservation_deposition_or_doi_manipulation_breaks_mac(self) -> None:
        transport = FakeZenodoTransport()
        reservation, _, _ = self.reserve_once(transport)
        self.paper_path.write_text(f"{PAPER_DOI} {SOFTWARE_DOI}", encoding="utf-8")
        self.software_path.write_text(f"{PAPER_DOI} {SOFTWARE_DOI}", encoding="utf-8")
        manifest = zenodo.validate_manifest(self.manifest(final=True), self.root, final=True)
        for field, value in (("deposition_id", 999), ("doi", "10.5281/zenodo.999")):
            tampered = copy.deepcopy(reservation)
            tampered["paper"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                zenodo.ZenodoError, "MAC mismatch"
            ):
                zenodo.finalize(
                    self.client(transport), manifest, "3" * 64,
                    tampered, self.root, self.root / "blocked.json"
                )

    def test_wrong_local_sha_blocks_before_any_finalize_http_effect(self) -> None:
        transport = FakeZenodoTransport()
        reservation, _, _ = self.reserve_once(transport)
        self.paper_path.write_text(f"{PAPER_DOI} {SOFTWARE_DOI}", encoding="utf-8")
        self.software_path.write_text(f"{PAPER_DOI} {SOFTWARE_DOI}", encoding="utf-8")
        raw = self.manifest(final=True)
        raw["paper"]["files"][0]["sha256"] = "0" * 64
        manifest = zenodo.validate_manifest(raw, self.root, final=True)
        before = len(transport.calls)
        with self.assertRaisesRegex(zenodo.ZenodoError, "SHA-256 mismatch"):
            zenodo.finalize(
                self.client(transport), manifest, "4" * 64,
                reservation, self.root, self.root / "blocked.json"
            )
        self.assertEqual(len(transport.calls), before)

    def test_final_manifest_rejects_generated_software_archive_sentinel(self) -> None:
        sentinel = self.root / zenodo.SOFTWARE_ARCHIVE_SENTINEL
        sentinel.write_text(
            "Workflow must replace this file with the deterministic tag archive.\n",
            encoding="utf-8",
        )
        raw = self.manifest(final=True)
        raw["software"]["files"] = [
            self.entry(sentinel, self.root, zenodo.SOFTWARE_ARCHIVE_SENTINEL)
        ]
        with self.assertRaisesRegex(zenodo.ZenodoError, "archive sentinel"):
            zenodo.validate_manifest(raw, self.root, final=True)
        raw.pop("reserved_dois")
        # The checked-in marker is intentional and harmless during DOI reserve.
        zenodo.validate_manifest(raw, self.root, final=False)

    def test_secret_is_redacted_from_cli_errors_and_never_accepted_as_argument(self) -> None:
        parser_help = zenodo.build_parser().format_help()
        self.assertNotIn("token", parser_help.lower())
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        with mock.patch.dict(os.environ, {zenodo.TOKEN_ENVIRONMENT_VARIABLE: TOKEN}):
            with mock.patch.object(
                zenodo, "validate_manifest",
                side_effect=zenodo.ZenodoError("Authorization: Bearer " + TOKEN),
            ):
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    result = zenodo.main([
                        "reserve", "--manifest", "manifest.json",
                        "--result", "result.json",
                        "--repository-root", str(self.root),
                    ])
        self.assertEqual(result, 1)
        self.assertNotIn(TOKEN, stderr.getvalue())
        self.assertIn("[REDACTED]", stderr.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as malformed:
            with self.assertRaises(SystemExit) as raised:
                zenodo.build_parser().parse_args(
                    ["reserve", "--token", TOKEN]
                )
        self.assertEqual(raised.exception.code, 2)
        self.assertNotIn(TOKEN, malformed.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)

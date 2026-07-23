#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline tests for the Formalization v2 alpha.2 Zenodo client."""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import qikvrt_formalization_v2_zenodo as release  # noqa: E402
from tools import qikvrt_zenodo_actions as shared  # noqa: E402


TOKEN = "f" * 64
DRAFT_ID = 21509999
DRAFT_DOI = f"10.5281/zenodo.{DRAFT_ID}"


def json_response(status: int, value: object) -> shared.HttpResponse:
    return shared.HttpResponse(
        status,
        {"Content-Type": "application/json"},
        json.dumps(value, sort_keys=True).encode("utf-8"),
    )


class FakeTransport:
    def __init__(
        self,
        target_metadata: dict[str, object],
        source_files: list[tuple[str, bytes]],
        *,
        missing_latest_draft_link: bool = False,
        existing_draft: bool = False,
        extra_delta: bool = False,
        newversion_conflict: bool = False,
    ) -> None:
        self.calls: list[tuple[str, str, bytes | None]] = []
        self.target_metadata = copy.deepcopy(target_metadata)
        self.source_files = list(source_files)
        self.missing_latest_draft_link = missing_latest_draft_link
        self.draft_created = existing_draft
        self.extra_delta = extra_delta
        self.newversion_conflict = newversion_conflict
        self.published = False
        self.latest_record_id = release.SOURCE_RECORD_ID
        self.draft_metadata = self.source_metadata()
        self.draft_files = [
            self.file(name, data, f"inherited-{index}")
            for index, (name, data) in enumerate(source_files)
        ]

    @staticmethod
    def file(name: str, data: bytes, file_id: str) -> dict[str, object]:
        encoded = urllib.parse.quote(name, safe="")
        return {
            "id": file_id,
            "filename": name,
            "filesize": len(data),
            "checksum": "md5:" + hashlib.md5(data).hexdigest(),  # noqa: S324
            "_data": data,
            "links": {
                "self": f"https://zenodo.org/api/files/alpha2-bucket/{encoded}",
                "download": f"https://zenodo.org/api/files/alpha2-bucket/{encoded}",
            },
        }

    @staticmethod
    def source_metadata() -> dict[str, object]:
        return {
            "title": "QIK-VRT formalization alpha.1",
            "version": release.SOURCE_VERSION,
            "creators": [{"name": "Lohmann, Ingolf"}],
            "upload_type": "software",
            "description": "Published alpha.1 source.",
        }

    def source_public(self) -> dict[str, object]:
        return {
            "id": release.SOURCE_RECORD_ID,
            "conceptrecid": release.CONCEPT_RECORD_ID,
            "doi": release.SOURCE_VERSION_DOI,
            "metadata": {
                **self.source_metadata(),
                "relations": {
                    "version": [
                        {
                            "index": 4,
                            "is_last": self.latest_record_id
                            == release.SOURCE_RECORD_ID,
                        }
                    ]
                },
            },
            "files": [],
            "links": {
                "latest": (
                    "https://zenodo.org/api/records/"
                    + str(self.latest_record_id)
                )
            },
        }

    def owner_source(self) -> dict[str, object]:
        latest = release.SOURCE_RECORD_ID
        if self.draft_created and not self.missing_latest_draft_link:
            latest = DRAFT_ID
        return {
            "id": release.SOURCE_RECORD_ID,
            "conceptrecid": release.CONCEPT_RECORD_ID,
            "submitted": True,
            "state": "done",
            "metadata": self.source_metadata(),
            "files": [],
            "links": {
                "self": (
                    "https://zenodo.org/api/deposit/depositions/"
                    + str(release.SOURCE_RECORD_ID)
                ),
                "latest_draft": (
                    "https://zenodo.org/api/deposit/depositions/" + str(latest)
                ),
            },
        }

    def draft(self) -> dict[str, object]:
        return {
            "id": DRAFT_ID,
            "conceptrecid": release.CONCEPT_RECORD_ID,
            "submitted": False,
            "state": "unsubmitted",
            "doi": DRAFT_DOI,
            "metadata": {
                **copy.deepcopy(self.draft_metadata),
                "prereserve_doi": {"doi": DRAFT_DOI},
            },
            "files": [self.clean(item) for item in self.draft_files],
            "links": {
                "self": (
                    "https://zenodo.org/api/deposit/depositions/" + str(DRAFT_ID)
                ),
                "bucket": "https://zenodo.org/api/files/alpha2-bucket",
            },
        }

    def public_draft(self) -> dict[str, object]:
        metadata = copy.deepcopy(self.draft_metadata)
        metadata.pop("upload_type", None)
        metadata["resource_type"] = {"type": "software"}
        if isinstance(metadata.get("license"), str):
            metadata["license"] = {"id": metadata["license"]}
        return {
            "id": DRAFT_ID,
            "conceptrecid": release.CONCEPT_RECORD_ID,
            "doi": DRAFT_DOI,
            "submitted": True,
            "state": "done",
            "metadata": metadata,
            "files": [
                {
                    **self.clean(item),
                    "key": item["filename"],
                    "size": item["filesize"],
                }
                for item in self.draft_files
            ],
            "links": {
                "latest": "https://zenodo.org/api/records/" + str(DRAFT_ID)
            },
        }

    @staticmethod
    def clean(value: dict[str, object]) -> dict[str, object]:
        result = copy.deepcopy(value)
        result.pop("_data", None)
        return result

    def inventory(self) -> list[dict[str, object]]:
        values: list[dict[str, object]] = [
            {
                "id": release.SOURCE_RECORD_ID,
                "conceptrecid": release.CONCEPT_RECORD_ID,
                "submitted": True,
                "state": "done",
            }
        ]
        if self.draft_created:
            values.append(
                {
                    "id": DRAFT_ID,
                    "conceptrecid": release.CONCEPT_RECORD_ID,
                    "submitted": False,
                    "state": "unsubmitted",
                }
            )
            if self.extra_delta:
                values.append(
                    {
                        "id": DRAFT_ID + 1,
                        "conceptrecid": release.CONCEPT_RECORD_ID,
                        "submitted": False,
                        "state": "unsubmitted",
                    }
                )
        return values

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        max_response_bytes: int = shared.MAX_RESPONSE_BYTES,
    ) -> shared.HttpResponse:
        del content_type, max_response_bytes
        method = method.upper()
        path = urllib.parse.urlsplit(url).path.rstrip("/")
        self.calls.append((method, path, body))
        if method == "GET" and path == "/api/deposit/depositions":
            return json_response(200, self.inventory())
        if method == "GET" and path == f"/api/records/{release.SOURCE_RECORD_ID}":
            return json_response(200, self.source_public())
        if method == "GET" and path == f"/api/records/{DRAFT_ID}":
            if not self.published:
                return json_response(404, {"message": "not public"})
            return json_response(200, self.public_draft())
        if method == "GET" and path == f"/api/records/{self.latest_record_id}":
            return json_response(
                200,
                {
                    "id": self.latest_record_id,
                    "conceptrecid": release.CONCEPT_RECORD_ID,
                    "metadata": {
                        "relations": {
                            "version": [{"index": 99, "is_last": True}]
                        }
                    },
                    "links": {
                        "latest": (
                            "https://zenodo.org/api/records/"
                            + str(self.latest_record_id)
                        )
                    },
                },
            )
        if method == "GET" and path == (
            f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}"
        ):
            return json_response(200, self.owner_source())
        if method == "POST" and path == (
            f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}/actions/newversion"
        ):
            if self.newversion_conflict:
                return json_response(409, {"message": "already has a draft"})
            self.draft_created = True
            links: dict[str, object] = {}
            if not self.missing_latest_draft_link:
                links["latest_draft"] = (
                    "https://zenodo.org/api/deposit/depositions/" + str(DRAFT_ID)
                )
            return json_response(
                201,
                {
                    "id": release.SOURCE_RECORD_ID,
                    "links": links,
                },
            )
        if method == "GET" and path == f"/api/deposit/depositions/{DRAFT_ID}":
            if self.published:
                return json_response(404, {"message": "not editable"})
            return json_response(200, self.draft())
        if method == "PUT" and path == f"/api/deposit/depositions/{DRAFT_ID}":
            payload = json.loads((body or b"{}").decode("utf-8"))
            self.draft_metadata = copy.deepcopy(payload["metadata"])
            return json_response(200, self.draft())
        if method == "POST" and path == (
            f"/api/deposit/depositions/{DRAFT_ID}/actions/publish"
        ):
            self.published = True
            self.latest_record_id = DRAFT_ID
            return json_response(202, {"status": "queued"})
        if path.startswith("/api/files/alpha2-bucket/"):
            name = urllib.parse.unquote(path.rsplit("/", 1)[1])
            existing = next(
                (
                    item
                    for item in self.draft_files
                    if item["filename"] == name
                ),
                None,
            )
            if method == "DELETE":
                if existing is not None:
                    self.draft_files.remove(existing)
                return shared.HttpResponse(204, {}, b"")
            if method == "PUT":
                if existing is not None:
                    self.draft_files.remove(existing)
                self.draft_files.append(
                    self.file(name, body or b"", "uploaded-" + name)
                )
                return json_response(201, self.clean(self.draft_files[-1]))
            if method == "GET" and existing is not None:
                data = existing["_data"]
                assert isinstance(data, bytes)
                return shared.HttpResponse(
                    200, {"Content-Type": "application/octet-stream"}, data
                )
        return json_response(
            500, {"message": f"unhandled {method} {path}"}
        )


class FormalizationAlpha2ZenodoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="qikvrt-formalization-alpha2-"
        )
        self.root = pathlib.Path(self.temporary.name)
        self.payload = self.root / "alpha2.zip"
        self.payload.write_bytes(b"deterministic alpha.2 archive\n")
        self.metadata: dict[str, object] = {
            "title": "QIK-VRT formalization alpha.2",
            "upload_type": "software",
            "description": "Bounded formalization extension.",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "version": release.TARGET_VERSION,
            "access_right": "open",
            "license": "other-nc",
            "language": "deu",
            "keywords": ["QIK-VRT", "Lean 4", "EFFECT_ACK"],
        }
        self.source_files = [
            (f"source-{index:02d}.bin", f"source-{index}\n".encode())
            for index in range(14)
        ]
        self.evidence = self.source_evidence()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def entry(self) -> dict[str, object]:
        data = self.payload.read_bytes()
        return {
            "path": self.payload.name,
            "name": self.payload.name,
            "size": len(data),
            "md5": hashlib.md5(data).hexdigest(),  # noqa: S324
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def manifest(self) -> dict[str, object]:
        return {
            "schema": release.MANIFEST_SCHEMA,
            "software": {
                "source_record_id": release.SOURCE_RECORD_ID,
                "concept_record_id": release.CONCEPT_RECORD_ID,
                "metadata": copy.deepcopy(self.metadata),
                "files": [self.entry()],
            },
        }

    def source_evidence(self) -> dict[str, object]:
        files = []
        for name, data in self.source_files:
            files.append(
                {
                    "name": name,
                    "size": len(data),
                    "md5": hashlib.md5(data).hexdigest(),  # noqa: S324
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        return {
            "anonymous": True,
            "concept_record_id": release.CONCEPT_RECORD_ID,
            "doi": release.SOURCE_VERSION_DOI,
            "files": files,
            "manifest_sha256": "a" * 64,
            "public_record_verified": True,
            "published_record_id": release.SOURCE_RECORD_ID,
            "schema": release.SOURCE_EVIDENCE_SCHEMA,
            "source_latest_verified": True,
            # Historical evidence records the predecessor of alpha.1 here.
            "source_record_id": 21498774,
            "verified_at_utc": "2026-07-23T01:24:03Z",
            "version": release.SOURCE_VERSION,
        }

    @staticmethod
    def client(transport: FakeTransport) -> release.FormalizationVersionClient:
        return release.FormalizationVersionClient(
            TOKEN,
            shared.DEFAULT_BASE_URL,
            transport=transport,
            poll_attempts=2,
            poll_interval=0,
            sleeper=lambda _seconds: None,
        )

    def reserve(
        self, transport: FakeTransport
    ) -> tuple[dict[str, object], pathlib.Path]:
        manifest = release.validate_manifest(self.manifest(), self.root)
        evidence = release.validate_source_evidence(self.evidence)
        path = self.root / "reservation.json"
        result = release.reserve_release(
            self.client(transport),
            manifest,
            self.root,
            "b" * 64,
            evidence,
            "c" * 64,
            path,
        )
        return result, path

    def test_manifest_and_source_evidence_are_closed_to_alpha2(self) -> None:
        normalized = release.validate_manifest(self.manifest(), self.root)
        self.assertEqual(
            normalized["software"]["source_record_id"], release.SOURCE_RECORD_ID
        )
        self.assertEqual(
            release.validate_source_evidence(self.evidence)[
                "published_record_id"
            ],
            release.SOURCE_RECORD_ID,
        )
        for label, mutate in (
            (
                "source",
                lambda value: value["software"].__setitem__(
                    "source_record_id", 21498774
                ),
            ),
            (
                "concept",
                lambda value: value["software"].__setitem__(
                    "concept_record_id", 999
                ),
            ),
            (
                "version",
                lambda value: value["software"]["metadata"].__setitem__(
                    "version", "2.0.0-alpha.1"
                ),
            ),
        ):
            value = self.manifest()
            mutate(value)
            with self.subTest(label=label), self.assertRaises(shared.ZenodoError):
                release.validate_manifest(value, self.root)

    def test_reserve_creates_only_one_pristine_new_version(self) -> None:
        transport = FakeTransport(self.metadata, self.source_files)
        reservation, path = self.reserve(transport)
        self.assertTrue(path.is_file())
        self.assertEqual(reservation["software"]["deposition_id"], DRAFT_ID)
        self.assertEqual(reservation["software"]["doi"], DRAFT_DOI)
        self.assertRegex(reservation["authorization_mac"], r"^[0-9a-f]{64}$")
        calls = [(method, path) for method, path, _ in transport.calls]
        self.assertIn(
            (
                "POST",
                f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}/actions/newversion",
            ),
            calls,
        )
        self.assertFalse(
            any(
                method in {"PUT", "DELETE"} or path.endswith("/actions/publish")
                for method, path in calls
            )
        )
        self.assertNotIn(TOKEN, path.read_text(encoding="utf-8"))

    def test_missing_latest_draft_uses_one_unique_inventory_delta(self) -> None:
        transport = FakeTransport(
            self.metadata,
            self.source_files,
            missing_latest_draft_link=True,
        )
        reservation, _ = self.reserve(transport)
        self.assertEqual(reservation["software"]["deposition_id"], DRAFT_ID)
        self.assertGreaterEqual(
            [(m, p) for m, p, _ in transport.calls].count(
                ("GET", "/api/deposit/depositions")
            ),
            2,
        )

    def test_multiple_inventory_deltas_fail_without_publish(self) -> None:
        transport = FakeTransport(
            self.metadata,
            self.source_files,
            missing_latest_draft_link=True,
            extra_delta=True,
        )
        with self.assertRaisesRegex(
            shared.ZenodoError, "multiple candidate drafts"
        ):
            self.reserve(transport)
        self.assertFalse(transport.published)

    def test_unknown_existing_draft_blocks_before_newversion(self) -> None:
        transport = FakeTransport(
            self.metadata, self.source_files, existing_draft=True
        )
        with self.assertRaisesRegex(shared.ZenodoError, "unreserved editable"):
            self.reserve(transport)
        self.assertFalse(
            any(
                method == "POST" and path.endswith("/actions/newversion")
                for method, path, _ in transport.calls
            )
        )

    def test_newversion_conflict_never_adopts_an_unreserved_draft(self) -> None:
        transport = FakeTransport(
            self.metadata,
            self.source_files,
            newversion_conflict=True,
        )
        with self.assertRaisesRegex(
            shared.ZenodoError, "existing unreserved draft"
        ):
            self.reserve(transport)
        self.assertFalse(transport.published)

    def test_local_hash_delta_blocks_before_any_transport(self) -> None:
        transport = FakeTransport(self.metadata, self.source_files)
        manifest = self.manifest()
        manifest["software"]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(shared.ZenodoError, "SHA-256 mismatch"):
            release.reserve_release(
                self.client(transport),
                manifest,
                self.root,
                "b" * 64,
                self.evidence,
                "c" * 64,
                self.root / "reservation.json",
            )
        self.assertEqual(transport.calls, [])

    def test_reservation_tamper_blocks_finalize_before_network(self) -> None:
        transport = FakeTransport(self.metadata, self.source_files)
        reservation, _ = self.reserve(transport)
        tampered = copy.deepcopy(reservation)
        tampered["software"]["deposition_id"] += 1
        before = len(transport.calls)
        with self.assertRaisesRegex(shared.ZenodoError, "MAC mismatch"):
            release.finalize_release(
                self.client(transport),
                self.manifest(),
                self.root,
                "b" * 64,
                self.evidence,
                "c" * 64,
                tampered,
                self.root / "result.json",
            )
        self.assertEqual(len(transport.calls), before)

    def test_finalize_replaces_inherited_files_gates_and_publishes(self) -> None:
        transport = FakeTransport(self.metadata, self.source_files)
        reservation, _ = self.reserve(transport)
        result = release.finalize_release(
            self.client(transport),
            self.manifest(),
            self.root,
            "b" * 64,
            self.evidence,
            "c" * 64,
            reservation,
            self.root / "result.json",
        )
        self.assertTrue(result["published_by_this_run"])
        self.assertEqual(result["published_record_id"], DRAFT_ID)
        self.assertEqual(
            [item["filename"] for item in transport.draft_files],
            [self.payload.name],
        )
        calls = [(method, path) for method, path, _ in transport.calls]
        publish_index = calls.index(
            ("POST", f"/api/deposit/depositions/{DRAFT_ID}/actions/publish")
        )
        upload_index = calls.index(
            ("PUT", f"/api/files/alpha2-bucket/{self.payload.name}")
        )
        download_indices = [
            index
            for index, call in enumerate(calls)
            if call == ("GET", f"/api/files/alpha2-bucket/{self.payload.name}")
        ]
        self.assertLess(upload_index, min(download_indices))
        self.assertTrue(
            any(index < publish_index for index in download_indices),
            "the draft download gate must run before publication",
        )

    def test_finalize_rerun_accepts_only_exact_reserved_public_record(self) -> None:
        transport = FakeTransport(self.metadata, self.source_files)
        reservation, _ = self.reserve(transport)
        release.finalize_release(
            self.client(transport),
            self.manifest(),
            self.root,
            "b" * 64,
            self.evidence,
            "c" * 64,
            reservation,
            self.root / "first.json",
        )
        before = len(transport.calls)
        second = release.finalize_release(
            self.client(transport),
            self.manifest(),
            self.root,
            "b" * 64,
            self.evidence,
            "c" * 64,
            reservation,
            self.root / "second.json",
        )
        self.assertFalse(second["published_by_this_run"])
        self.assertFalse(
            any(
                method in {"POST", "PUT", "DELETE"}
                for method, _path, _body in transport.calls[before:]
            )
        )

    def test_source_latest_drift_blocks_finalize_before_draft_mutation(self) -> None:
        transport = FakeTransport(self.metadata, self.source_files)
        reservation, _ = self.reserve(transport)
        transport.latest_record_id = 999999
        before = len(transport.calls)
        with self.assertRaisesRegex(shared.ZenodoError, "no longer.*latest"):
            release.finalize_release(
                self.client(transport),
                self.manifest(),
                self.root,
                "b" * 64,
                self.evidence,
                "c" * 64,
                reservation,
                self.root / "result.json",
            )
        self.assertFalse(
            any(
                method in {"POST", "PUT", "DELETE"}
                for method, _path, _body in transport.calls[before:]
            )
        )

    def test_mutation_allowlist_blocks_source_edit_and_other_drafts(self) -> None:
        transport = FakeTransport(self.metadata, self.source_files)
        client = self.client(transport)
        for path in (
            f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}",
            "/api/deposit/depositions/999999",
            "/api/deposit/depositions/999999/actions/publish",
        ):
            with self.subTest(path=path), self.assertRaisesRegex(
                shared.ZenodoError, "outside the reserved"
            ):
                client.request("PUT", path, payload={"metadata": {}})
        self.assertEqual(transport.calls, [])

    def test_cli_has_no_token_argument_and_missing_secret_blocks(self) -> None:
        help_text = release.build_parser().format_help()
        self.assertNotIn("--token", help_text)
        with self.assertRaises(SystemExit):
            release.build_parser().parse_args(
                ["reserve", "--token", TOKEN]
            )
        self.assertEqual(
            release.main(
                [
                    "reserve",
                    "--manifest",
                    "missing.json",
                    "--source-evidence",
                    "missing.json",
                    "--reservation",
                    "out.json",
                    "--repository-root",
                    str(self.root),
                ]
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import ast
import copy
import hashlib
import json
import pathlib
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_zenodo_mixed_license_contract as contract
from tools import qikvrt_zenodo_publish as publish


ARTIFACT_LICENSE = {
    "classification": "machine_readable_license_policy",
    "copyright": "Copyright 2026 Ingolf Lohmann.",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}


def write(path: pathlib.Path, data: bytes) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_json(path: pathlib.Path, value: object) -> pathlib.Path:
    return write(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def git_blob(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def identity(root: pathlib.Path, relative: str) -> dict[str, object]:
    data = (root / relative).read_bytes()
    return {
        "path": relative,
        "name": pathlib.PurePosixPath(relative).name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha": git_blob(data),
    }


def metadata_rights(rights: list[dict[str, object]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for right in rights:
        if right["kind"] == "standard":
            result.append({"id": str(right["id"])})
        else:
            result.append(
                {
                    "title": str(right["title"]),
                    "description": str(right["description"]),
                    "link": str(right["url"]),
                }
            )
    return result


def build_fixture(root: pathlib.Path, *, custom: bool = False) -> pathlib.Path:
    publication_id = "fixture-mixed-license-v3"
    files: list[tuple[str, bytes, str]] = [
        (
            "candidate/LICENSE_NOTICE.md",
            b"SPDX-License-Identifier: CC-BY-NC-ND-4.0\n"
            b"Text=CC-BY-NC-ND-4.0; Formal=Apache-2.0\n",
            "cc-by-nc-nd-4.0",
        ),
        (
            "candidate/CITATION.cff",
            b"cff-version: 1.2.0\ntitle: Fixture\nmessage: Cite me\n",
            "cc-by-nc-nd-4.0",
        ),
        (
            "candidate/ARTICLE.md",
            b"# Fixture\n",
            "cc-by-nc-nd-4.0",
        ),
        (
            "candidate/FORMAL_Fixture.lean",
            b"-- SPDX-License-Identifier: Apache-2.0\nexample : True := by trivial\n",
            "apache-2.0",
        ),
    ]
    rights: list[dict[str, object]] = [
        {"id": "cc-by-nc-nd-4.0", "kind": "standard", "spdx_id": "CC-BY-NC-ND-4.0"},
        {"id": "apache-2.0", "kind": "standard", "spdx_id": "Apache-2.0"},
    ]
    if custom:
        files.extend(
            [
                (
                    "candidate/POLYFORM-NONCOMMERCIAL-1.0.0.md",
                    b"PolyForm Noncommercial License 1.0.0 fixture text\n",
                    "LicenseRef-PolyForm-Noncommercial-1.0.0",
                ),
                (
                    "candidate/tool.py",
                    b"# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0\n",
                    "LicenseRef-PolyForm-Noncommercial-1.0.0",
                ),
            ]
        )
    for relative, data, _right in files:
        write(root / relative, data)

    if custom:
        custom_right = dict(contract.POLYFORM_CUSTOM_RIGHT)
        custom_right["license_text"] = identity(
            root, "candidate/POLYFORM-NONCOMMERCIAL-1.0.0.md"
        )
        rights.append(custom_right)

    map_relative = "candidate/FILE_LICENSE_MAP.json"
    files.append((map_relative, b"", "cc-by-nc-nd-4.0"))
    license_map = {
        "_license": copy.deepcopy(ARTIFACT_LICENSE),
        "schema": contract.MAP_SCHEMA,
        "publication_id": publication_id,
        "rights": rights,
        "assignments": [
            {
                "path": relative,
                "name": pathlib.PurePosixPath(relative).name,
                "right_id": right_id,
            }
            for relative, _data, right_id in files
        ],
    }
    write_json(root / map_relative, license_map)
    identities = [identity(root, relative) for relative, _data, _right in files]
    manifest = {
        "_license": copy.deepcopy(ARTIFACT_LICENSE),
        "schema": contract.MANIFEST_SCHEMA,
        "state": contract.VALIDATE_STATE,
        "confirm": contract.NO_EFFECT_CONFIRMATION,
        "transport": contract.TRANSPORT_STATE,
        "repository": "Goldkelch/qik-vrt",
        "publication_id": publication_id,
        "metadata": {
            "title": "Fixture",
            "version": "3.0.0-candidate",
            "rights": metadata_rights(rights),
        },
        "files": identities,
        "license_notice": identity(root, "candidate/LICENSE_NOTICE.md"),
        "file_license_map": identity(root, map_relative),
    }
    return write_json(root / "release/v3/validate-request.json", manifest)


def rewrite_map_and_rebind(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
    mutate,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    map_path = root / manifest["file_license_map"]["path"]
    license_map = json.loads(map_path.read_text(encoding="utf-8"))
    mutate(license_map)
    write_json(map_path, license_map)
    rebound = identity(root, manifest["file_license_map"]["path"])
    manifest["file_license_map"] = rebound
    for index, item in enumerate(manifest["files"]):
        if item["path"] == rebound["path"]:
            manifest["files"][index] = rebound
            break
    write_json(manifest_path, manifest)


def rebind_file(root: pathlib.Path, manifest_path: pathlib.Path, relative: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rebound = identity(root, relative)
    for index, item in enumerate(manifest["files"]):
        if item["path"] == relative:
            manifest["files"][index] = rebound
            break
    if manifest["license_notice"]["path"] == relative:
        manifest["license_notice"] = rebound
    write_json(manifest_path, manifest)


class MixedLicenseContractTests(unittest.TestCase):
    def test_complete_two_right_contract_validates_without_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            receipt = contract.validate_manifest(manifest_path, root)
        self.assertEqual(receipt["state"], "VALIDATED_NO_REMOTE_EFFECT")
        self.assertEqual(receipt["upload_count"], 5)
        self.assertEqual(
            receipt["rights"],
            [
                {"id": "cc-by-nc-nd-4.0", "file_count": 4},
                {"id": "apache-2.0", "file_count": 1},
            ],
        )
        self.assertTrue(receipt["mixed_rights"])
        self.assertFalse(receipt["effect_permitted"])

    def test_missing_assignment_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            rewrite_map_and_rebind(
                root,
                manifest_path,
                lambda value: value["assignments"].pop(),
            )
            with self.assertRaisesRegex(contract.ContractError, "assign every upload"):
                contract.validate_manifest(manifest_path, root)

    def test_duplicate_assignment_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)

            def duplicate(value: dict[str, object]) -> None:
                value["assignments"].append(copy.deepcopy(value["assignments"][0]))

            rewrite_map_and_rebind(root, manifest_path, duplicate)
            with self.assertRaisesRegex(contract.ContractError, "duplicate repository paths"):
                contract.validate_manifest(manifest_path, root)

    def test_extra_assignment_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)

            def add_extra(value: dict[str, object]) -> None:
                value["assignments"].append(
                    {
                        "path": "candidate/not-uploaded.txt",
                        "name": "not-uploaded.txt",
                        "right_id": "cc-by-nc-nd-4.0",
                    }
                )

            rewrite_map_and_rebind(root, manifest_path, add_extra)
            with self.assertRaisesRegex(contract.ContractError, "assign every upload"):
                contract.validate_manifest(manifest_path, root)

    def test_undefined_right_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)

            def undefine(value: dict[str, object]) -> None:
                value["assignments"][0]["right_id"] = "LicenseRef-Undefined"

            rewrite_map_and_rebind(root, manifest_path, undefine)
            with self.assertRaisesRegex(contract.ContractError, "undefined rights"):
                contract.validate_manifest(manifest_path, root)

    def test_file_license_map_assignment_must_match_its_cc_license(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)

            def misassign(value: dict[str, object]) -> None:
                assignment = next(
                    item
                    for item in value["assignments"]
                    if item["name"] == "FILE_LICENSE_MAP.json"
                )
                assignment["right_id"] = "apache-2.0"

            rewrite_map_and_rebind(root, manifest_path, misassign)
            with self.assertRaisesRegex(
                contract.ContractError,
                "FILE_LICENSE_MAP.json must be assigned to cc-by-nc-nd-4.0",
            ):
                contract.validate_manifest(manifest_path, root)

    def test_license_notice_assignment_must_match_its_cc_license(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)

            def misassign(value: dict[str, object]) -> None:
                assignment = next(
                    item
                    for item in value["assignments"]
                    if item["name"] == "LICENSE_NOTICE.md"
                )
                assignment["right_id"] = "apache-2.0"

            rewrite_map_and_rebind(root, manifest_path, misassign)
            with self.assertRaisesRegex(
                contract.ContractError,
                "LICENSE_NOTICE.md must be assigned to cc-by-nc-nd-4.0",
            ):
                contract.validate_manifest(manifest_path, root)

    def test_license_notice_spdx_declaration_must_remain_cc(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            notice = root / "candidate/LICENSE_NOTICE.md"
            notice.write_text(
                notice.read_text(encoding="utf-8").replace(
                    "SPDX-License-Identifier: CC-BY-NC-ND-4.0",
                    "SPDX-License-Identifier: Apache-2.0",
                ),
                encoding="utf-8",
            )
            rebind_file(root, manifest_path, "candidate/LICENSE_NOTICE.md")
            with self.assertRaisesRegex(
                contract.ContractError,
                "must declare SPDX CC-BY-NC-ND-4.0",
            ):
                contract.validate_manifest(manifest_path, root)

    def test_metadata_rights_mismatch_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["metadata"]["rights"] = [{"id": "cc-by-nc-nd-4.0"}]
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(
                contract.ContractError, "exact file-license-map projection"
            ):
                contract.validate_manifest(manifest_path, root)

    def test_singular_legacy_license_field_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["metadata"]["license"] = "cc-by-nc-nd-4.0"
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(contract.ContractError, "singular legacy license"):
                contract.validate_manifest(manifest_path, root)

    def test_hash_and_blob_drift_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            with (root / "candidate/FORMAL_Fixture.lean").open("ab") as handle:
                handle.write(b"-- drift\n")
            with self.assertRaisesRegex(contract.ContractError, "observed file bytes"):
                contract.validate_manifest(manifest_path, root)

    def test_custom_polyform_right_is_structurally_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root, custom=True)
            receipt = contract.validate_manifest(manifest_path, root)
            custom_count = next(
                item["file_count"]
                for item in receipt["rights"]
                if item["id"] == "LicenseRef-PolyForm-Noncommercial-1.0.0"
            )
        self.assertEqual(custom_count, 2)

    def test_changed_polyform_definition_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root, custom=True)

            def change_url(value: dict[str, object]) -> None:
                value["rights"][2]["url"] = "https://example.invalid/license"

            rewrite_map_and_rebind(root, manifest_path, change_url)
            with self.assertRaisesRegex(contract.ContractError, "approved custom-right definition"):
                contract.validate_manifest(manifest_path, root)

    def test_mixed_candidate_cff_license_field_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            with (root / "candidate/CITATION.cff").open("ab") as handle:
                handle.write(b"license: [CC-BY-NC-ND-4.0, Apache-2.0]\n")
            rebind_file(root, manifest_path, "candidate/CITATION.cff")
            with self.assertRaisesRegex(contract.ContractError, "must omit top-level"):
                contract.validate_manifest(manifest_path, root)

    def test_quoted_mixed_candidate_cff_license_field_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            with (root / "candidate/CITATION.cff").open("ab") as handle:
                handle.write(b'"license": [CC-BY-NC-ND-4.0, Apache-2.0]\n')
            rebind_file(root, manifest_path, "candidate/CITATION.cff")
            with self.assertRaisesRegex(contract.ContractError, "must omit top-level"):
                contract.validate_manifest(manifest_path, root)

    def test_multiline_licenseref_cff_field_blocks_for_uniform_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)

            def make_uniform(value: dict[str, object]) -> None:
                value["rights"] = [value["rights"][0]]
                for assignment in value["assignments"]:
                    assignment["right_id"] = "cc-by-nc-nd-4.0"

            rewrite_map_and_rebind(root, manifest_path, make_uniform)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["metadata"]["rights"] = [{"id": "cc-by-nc-nd-4.0"}]
            write_json(manifest_path, manifest)
            with (root / "candidate/CITATION.cff").open("ab") as handle:
                handle.write(b"license:\n  - LicenseRef-Undefined\n")
            rebind_file(root, manifest_path, "candidate/CITATION.cff")
            with self.assertRaisesRegex(contract.ContractError, "unambiguous SPDX scalar"):
                contract.validate_manifest(manifest_path, root)

    def test_legacy_publisher_rejects_v3_before_client_or_git_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path = build_fixture(root)
            evidence = root / "release/v3/zenodo-publication.json"
            with (
                mock.patch.object(publish.zenodo, "ZenodoClient") as client,
                mock.patch.object(publish, "_acquire_remote_consumption_lock") as lock,
                mock.patch.object(publish, "_git") as git,
            ):
                with self.assertRaisesRegex(
                    publish.zenodo.ZenodoError,
                    "unsupported publication manifest schema",
                ):
                    publish.publish(manifest_path, root)
            client.assert_not_called()
            lock.assert_not_called()
            git.assert_not_called()
            self.assertFalse(evidence.exists())


class RepositoryMixedLicenseAuditTests(unittest.TestCase):
    def test_survival_v1_audit_is_exactly_bound_to_publication_receipt(self) -> None:
        audit_path = (
            ROOT
            / "evidence/publications/qikvrt-survival-of-the-anschlussfaehigsten-v1"
            / "ZENODO_FILE_LICENSE_AUDIT.json"
        )
        receipt_path = (
            ROOT
            / "release/survival-anschlussfaehigsten-2026-07-31"
            / "zenodo-publication.json"
        )
        request_path = (
            ROOT
            / "release/survival-anschlussfaehigsten-2026-07-31"
            / "publish-request.json"
        )
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        receipt_raw = receipt_path.read_bytes()
        receipt = json.loads(receipt_raw)
        request = json.loads(request_path.read_text(encoding="utf-8"))
        expected = []
        formal_names = {
            "FORMAL_OperationalContinuation.lean",
            "FORMAL_ConnectabilitySimulation.lean",
            "FORMAL_WeightedConnectability.lean",
        }
        for item in receipt["files"]:
            expected.append(
                {
                    "path": item["path"],
                    "name": item["name"],
                    "bytes": item["size"],
                    "sha256": item["sha256"],
                    "git_blob_sha": item["git_blob_sha"],
                    "right_id": (
                        "apache-2.0"
                        if item["name"] in formal_names
                        else "cc-by-nc-nd-4.0"
                    ),
                }
            )
        self.assertEqual(audit["assignments"], expected)
        self.assertEqual(len(expected), 31)
        self.assertEqual(sum(item["right_id"] == "apache-2.0" for item in expected), 3)
        self.assertEqual(
            audit["source"]["publication_receipt_sha256"],
            hashlib.sha256(receipt_raw).hexdigest(),
        )
        self.assertEqual(audit["source"]["doi"], receipt["doi"])
        self.assertEqual(
            audit["source"]["repository_evidence_commit"],
            receipt["repository_commit"],
        )
        requested = audit["requested_record_metadata"]
        self.assertEqual(requested["license"], request["metadata"]["license"])
        self.assertEqual(
            requested["publish_request_sha256"],
            hashlib.sha256(request_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            requested["notes_sha256"],
            hashlib.sha256(request["metadata"]["notes"].encode("utf-8")).hexdigest(),
        )
        self.assertTrue(requested["notes_preserve_file_level_licenses"])
        self.assertIn("dateibezogene Softwarelizenz", request["metadata"]["notes"])
        self.assertFalse(audit["invariants"]["zenodo_mutation_performed"])
        self.assertFalse(audit["future_gate"]["effect_permitted"])

    def test_frozen_survival_cff_has_no_archive_license_field(self) -> None:
        cff_path = (
            ROOT
            / "docs/publications/2026-07-31-survival-anschlussfaehigsten"
            / "CITATION.cff"
        )
        cff = cff_path.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"(?m)^license\s*:", cff))

    def test_frozen_survival_license_notice_blob_is_unchanged(self) -> None:
        notice_path = (
            ROOT
            / "docs/publications/2026-07-31-survival-anschlussfaehigsten"
            / "LICENSE_NOTICE.md"
        )
        self.assertEqual(
            git_blob(notice_path.read_bytes()),
            "111f483d4d3f35bd68604a7cbef138336eac185f",
        )

    def test_validator_has_no_remote_or_repository_mutation_primitive(self) -> None:
        source_path = ROOT / "tools/qikvrt_zenodo_mixed_license_contract.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        called_attributes: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called_attributes.add(node.func.attr)
        self.assertTrue(
            imported_roots.isdisjoint(
                {"http", "os", "requests", "socket", "subprocess", "urllib"}
            )
        )
        self.assertTrue(
            called_attributes.isdisjoint(
                {"mkdir", "rename", "replace", "unlink", "write_bytes", "write_text"}
            )
        )

    def test_new_policy_and_schemas_are_parseable(self) -> None:
        capability = json.loads(
            (ROOT / "runtime/capabilities/ZENODO_MIXED_LICENSE_METADATA_CAPABILITY.json")
            .read_text(encoding="utf-8")
        )
        map_schema = json.loads(
            (ROOT / "policy/qikvrt-zenodo-file-license-map-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        manifest_schema = json.loads(
            (ROOT / "policy/qikvrt-zenodo-publication-manifest-v3.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(capability["state"], "VALIDATE_ONLY")
        self.assertFalse(capability["remote_effects"])
        self.assertEqual(
            map_schema["properties"]["schema"]["const"],
            contract.MAP_SCHEMA,
        )
        self.assertEqual(
            manifest_schema["properties"]["schema"]["const"],
            contract.MANIFEST_SCHEMA,
        )


if __name__ == "__main__":
    unittest.main()

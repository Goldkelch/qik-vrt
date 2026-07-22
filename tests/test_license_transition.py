#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression checks for the prospective noncommercial license transition."""
from __future__ import annotations

import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLYFORM_ID = "PolyForm-Noncommercial-1.0.0"
POLYFORM_PATH = "LICENSES/PolyForm-Noncommercial-1.0.0.txt"
POLYFORM_SHA256 = "ffcca38841adb694b6f380647e15f17c446a4d1656fed51a1e2041d064c94cc8"
POLYFORM_SIZE = 4563

CURRENT_SOURCE_FILES = (
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/workflows/qikvrt_adaptive_runtime.yml",
    ".github/workflows/qikvrt_ci.yml",
    ".github/workflows/qikvrt_collective_review.yml",
    ".github/workflows/qikvrt_effect_ack_finalize.yml",
    ".github/workflows/qikvrt_formalization_and_audio.yml",
    ".github/workflows/qikvrt_mesh_api.yml",
    ".github/workflows/qikvrt_seed_dashboard_publish.yml",
    ".github/workflows/qikvrt_seed_mesh_audit_export.yml",
    ".github/workflows/qikvrt_seed_mesh_maintenance.yml",
    ".github/workflows/qikvrt_seed_node_revalidation.yml",
    ".github/workflows/qikvrt_seed_registry_acceptance.yml",
    ".github/workflows/qikvrt_zenodo_reserve.yml",
    "api/qikvrt_github_api.openapi.yaml",
    "include/qikvrt/effect_ack.h",
    "Makefile",
    "docs/assets/js/qikvrt-homepage.js",
    "docs/assets/js/qikvrt-local-engine.js",
    "docs/publications/2026-07-22-effect-ack-universal-effect-control/effect_ack_universality_proof.py",
    "qikvrt.cmd",
    "qikvrt.py",
    "qikvrt.sh",
    "scripts/qikvrt_api_client.py",
    "src/effect_ack_core.c",
    "src/qikvrt_api_handler.py",
    "src/qikvrt_effect_ack.py",
    "src/qikvrt_github_api_shim.py",
    "tests/test_api_client.py",
    "tests/test_adaptive_runtime.sh",
    "tests/test_effect_ack_core.c",
    "tests/test_effect_ack_core.sh",
    "tests/test_effect_ack_scientific_bundle.sh",
    "tests/test_effect_ack_conformance.py",
    "tests/test_effect_ack_release_workflows.py",
    "tests/test_handler_security.py",
    "tests/test_handler_unit.py",
    "tests/test_integrity.py",
    "tests/test_launcher_runtime.py",
    "tests/test_license_transition.py",
    "tests/test_ietf_offline_render.py",
    "tests/test_runtime_bootstrap.sh",
    "tests/test_zenodo_actions.py",
    "tests/test_zenodo_manifest_builder.py",
    "tests/test_seed_workflows.py",
    "tests/test_tcpip_e2e.py",
    "tools/__init__.py",
    "tools/bootstrap-gh.ps1",
    "tools/bootstrap-gh.sh",
    "tools/bootstrap-runtime.ps1",
    "tools/bootstrap-runtime.sh",
    "tools/qikvrt_adaptive_runtime.sh",
    "tools/qikvrt_build_zenodo_manifest.py",
    "tools/qikvrt_cicd_publish.py",
    "tools/qikvrt_initial_acceptance_gate.py",
    "tools/qikvrt_integrity.py",
    "tools/qikvrt_zenodo_actions.py",
    "tools/qikvrt_master_acceptance_gate.py",
    "tools/qikvrt_runtime_logger.py",
    "tools/qikvrt_seed_common.py",
    "tools/qikvrt_seed_dashboard_publish.sh",
    "tools/qikvrt_seed_mesh_audit_export.sh",
    "tools/qikvrt_seed_mesh_maintenance.sh",
    "tools/qikvrt_seed_node_revalidation.sh",
    "tools/qikvrt_seed_registry_acceptance.sh",
    "tools/qikvrt_subprocess.py",
    "tools/qikvrt_validate_state_run.py",
)

HISTORICAL_APACHE_FILES = (
    "LINUX.sh",
    "MACOS.command",
    "WINDOWS.bat",
    "QALL.ini",
    "qikvrt.bat",
    "qikvrt.ps1",
    "runtime/download_python_runtime.ps1",
    "runtime/download_python_runtime.sh",
    "runtime/resolve_dependency.py",
)


class LicenseTransitionTests(unittest.TestCase):
    def test_polyform_text_is_byte_exact(self) -> None:
        data = (ROOT / POLYFORM_PATH).read_bytes()
        self.assertEqual(len(data), POLYFORM_SIZE)
        self.assertEqual(hashlib.sha256(data).hexdigest(), POLYFORM_SHA256)

    def test_current_source_files_have_polyform_identifier(self) -> None:
        marker = f"SPDX-License-Identifier: {POLYFORM_ID}"
        for relative in CURRENT_SOURCE_FILES:
            with self.subTest(path=relative):
                self.assertIn(marker, (ROOT / relative).read_text(encoding="utf-8"))

    def test_historical_apache_files_remain_explicit(self) -> None:
        for relative in HISTORICAL_APACHE_FILES:
            with self.subTest(path=relative):
                self.assertIn("Apache-2.0", (ROOT / relative).read_text(encoding="utf-8"))

    def test_license_map_reserves_commercial_use_without_false_retroactivity(self) -> None:
        license_map = (ROOT / "LICENSE").read_text(encoding="utf-8")
        normalized_license_map = " ".join(license_map.split())
        transition = (ROOT / "LICENSE_TRANSITION.md").read_text(encoding="utf-8")
        self.assertIn(POLYFORM_ID, license_map)
        self.assertIn("Required Notice:", license_map)
        self.assertIn("Commercial use is not licensed", license_map)
        self.assertIn(
            "below `src/`, `include/`, `scripts/`, `tools/`, `tests/`, and",
            normalized_license_map,
        )
        self.assertIn("documentation, website HTML/CSS/data", license_map)
        self.assertIn("No retroactive withdrawal", transition)
        self.assertIn("Third-party", transition)

    def test_machine_readable_sources_and_transition_match(self) -> None:
        sources = json.loads((ROOT / "OFFICIAL_LICENSE_SOURCES.json").read_text(encoding="utf-8"))
        verified = sources["verified_files"][POLYFORM_PATH]
        self.assertEqual(verified["sha256"], POLYFORM_SHA256)
        self.assertEqual(verified["size_bytes"], POLYFORM_SIZE)
        record = json.loads((ROOT / "LICENSE_TRANSITION_RECORD.json").read_text(encoding="utf-8"))
        self.assertEqual(record["current_qikvrt_source_license"], POLYFORM_ID)
        self.assertEqual(record["polyform_license_sha256"], POLYFORM_SHA256)
        self.assertTrue(record["non_retroactivity"])
        self.assertTrue(record["third_party_licenses_preserved"])
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn(f'license: "{POLYFORM_ID}"', citation)


if __name__ == "__main__":
    unittest.main()

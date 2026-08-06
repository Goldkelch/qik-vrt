# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
TOOL = HERE / "tools/qikvrt_publication_overview.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_publication_overview", TOOL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PublicationOverviewTests(unittest.TestCase):
    def fixture(self, directory: str) -> pathlib.Path:
        root = pathlib.Path(directory)
        publications = root / "docs/publications"
        publications.mkdir(parents=True)
        (publications / "index.json").write_text(
            json.dumps(
                {
                    "schema": "qikvrt_publication_overview_v1",
                    "repository": "Goldkelch/qik-vrt",
                    "publication_bundles": [
                        {
                            "id": "historical",
                            "title": "Historical",
                            "path": "docs/publications/2026-01-01-historical/README.md",
                            "state": "repository_snapshot",
                            "repository_commit": "a" * 40,
                            "url": "https://example.invalid/historical",
                        }
                    ],
                    "featured_artifacts": [],
                    "zenodo_records": [],
                    "ietf_documents": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (publications / "index.html").write_text(
            '<html>\n<div class="collection-list">\n'
            '        <a class="collection-row" href="https://example.invalid/historical">'
            '<time>01.01.</time><span><strong>Historical</strong><small>Snapshot</small>'
            '</span><b>Öffnen →</b></a>\n'
            "      </div>\n</html>\n",
            encoding="utf-8",
        )
        historical = publications / "2026-01-01-historical"
        historical.mkdir()
        (historical / "README.md").write_text("# Historical\n", encoding="utf-8")
        return root

    def test_missing_bundle_materializes_both_indexes_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            qce = root / "docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence"
            qce.mkdir()
            (qce / "README.md").write_text(
                "# QIK-VRT Quantum Causal Emergence (QCE)\n\n"
                "## Unschärfe, Planck-Übergangselement und klassischer Lichtkegel\n\n"
                "Publication ID: `qikvrt-quantum-causal-emergence-v1`\n\n"
                "Physical Correspondence = OPEN_CANDIDATE\n",
                encoding="utf-8",
            )
            first = MODULE.execute(root, materialize=False)
            self.assertEqual(first["state"], "DRIFT")
            self.assertEqual(
                first["changed_paths"],
                ["docs/publications/index.json", "docs/publications/index.html"],
            )
            materialized = MODULE.execute(root, materialize=True)
            self.assertEqual(materialized["state"], "MATERIALIZED")
            current = MODULE.execute(root, materialize=False)
            self.assertEqual(current["state"], "CURRENT")
            index = json.loads((root / "docs/publications/index.json").read_text())
            entries = {item["path"]: item for item in index["publication_bundles"]}
            path = "docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/README.md"
            self.assertEqual(entries[path]["id"], "qikvrt-quantum-causal-emergence-v1")
            self.assertEqual(entries[path]["state"], "repository_candidate_open_correspondence")
            html = (root / "docs/publications/index.html").read_text(encoding="utf-8")
            self.assertIn(path, html)
            self.assertIn("05.08.", html)
            self.assertIn("Unschärfe, Planck-Übergangselement", html)

    def test_explicit_index_state_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            bundle = root / "docs/publications/2026-08-06-review-bound"
            bundle.mkdir()
            (bundle / "README.md").write_text(
                "# Review Bound\n\n"
                "Publication ID: `review-bound-v1`\n"
                "Publication Index State: `repository_candidate_human_physics_review_pending`\n",
                encoding="utf-8",
            )
            MODULE.execute(root, materialize=True)
            index = json.loads((root / "docs/publications/index.json").read_text())
            entry = next(item for item in index["publication_bundles"] if item["id"] == "review-bound-v1")
            self.assertEqual(
                entry["state"],
                "repository_candidate_human_physics_review_pending",
            )

    def test_existing_snapshot_entry_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            before = json.loads((root / "docs/publications/index.json").read_text())
            MODULE.execute(root, materialize=True)
            after = json.loads((root / "docs/publications/index.json").read_text())
            self.assertEqual(before["publication_bundles"][0], after["publication_bundles"][0])

    def test_duplicate_identifier_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            bundle = root / "docs/publications/2026-08-06-duplicate"
            bundle.mkdir()
            (bundle / "README.md").write_text(
                "# Duplicate\n\nPublication ID: `historical`\n",
                encoding="utf-8",
            )
            with self.assertRaises(MODULE.PublicationOverviewBlock):
                MODULE.execute(root, materialize=True)

    def test_cli_check_emits_exact_drift_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            bundle = root / "docs/publications/2026-08-06-new"
            bundle.mkdir()
            (bundle / "README.md").write_text("# New\n", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(TOOL), "check", "--root", str(root), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(process.returncode, 2)
            self.assertIn(MODULE.DRIFT_SIGNATURE, process.stderr)


if __name__ == "__main__":
    unittest.main()

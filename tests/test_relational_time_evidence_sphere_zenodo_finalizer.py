from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "release/relational-time-monotonic-evidence-sphere-zenodo-control-v2"
    / "finalize_authorized_controls.py"
)
SPEC = importlib.util.spec_from_file_location("relational_time_finalizer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
controls = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = controls
SPEC.loader.exec_module(controls)


class RelationalTimeEvidenceSphereZenodoFinalizerTests(unittest.TestCase):
    def action(self) -> dict[str, object]:
        frozen = controls.frozen_candidate()
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        observed = (now - dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        authorized = now.isoformat().replace("+00:00", "Z")
        authorization_id = "qikvrt-relational-time-v2-test-20260909-0001"
        return {
            "schema": controls.INPUT_SCHEMA,
            "authorization_id": authorization_id,
            "nonce": "a" * 64,
            "principal": controls.PRINCIPAL,
            "source_head": controls.current_head(),
            "authorized_at": authorized,
            "exact_statement": controls.expected_statement(authorization_id, frozen),
            "p7_reobservation": {
                "state": "SATISFIED",
                "trusted_main_head": controls.current_head(),
                "trusted_main_tree": controls.current_tree(),
                "external_obligations": "SATISFIED",
                "observed_at": observed,
                "evidence_locator": "external://test/P7-boundary",
            },
        }

    def test_default_check_is_inert(self) -> None:
        before = (
            controls.AUTHORIZATION_PATH.exists(),
            controls.MANIFEST_PATH.exists(),
        )
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        self.assertIn("inert pre-P7", completed.stdout)
        self.assertEqual(before, (False, False))
        self.assertFalse(controls.AUTHORIZATION_PATH.exists())
        self.assertFalse(controls.MANIFEST_PATH.exists())

    def test_frozen_candidate_is_exactly_nine_current_repository_files(self) -> None:
        frozen = controls.frozen_candidate()
        self.assertEqual(frozen["publication_id"], controls.PUBLICATION_ID)
        self.assertEqual(len(frozen["files"]), 9)
        self.assertEqual(
            frozen["files"][0]["sha256"],
            "38b0e62a46214a7cb9943dd3ef08283a70ae7e15ba22a59a9e53506f2945e311",
        )

    def test_valid_external_action_builds_but_does_not_write_controls(self) -> None:
        frozen = controls.frozen_candidate()
        action = self.action()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "action.json"
            path.write_text(json.dumps(action), encoding="utf-8")
            parsed = controls.load_action(path, frozen)
        authorization_raw, manifest_raw = controls.build_controls(parsed, frozen)
        authorization = json.loads(authorization_raw)
        manifest = json.loads(manifest_raw)
        self.assertEqual(authorization["authorization_id"], action["authorization_id"])
        self.assertEqual(authorization["source_head"], controls.current_head())
        self.assertEqual(manifest["source_head"], controls.current_head())
        self.assertEqual(len(manifest["files"]), 9)
        self.assertFalse(controls.AUTHORIZATION_PATH.exists())
        self.assertFalse(controls.MANIFEST_PATH.exists())

    def test_rejects_legacy_authorization_and_unsatisfied_p7(self) -> None:
        frozen = controls.frozen_candidate()
        action = self.action()
        action["authorization_id"] = controls.LEGACY_AUTHORIZATION_ID
        action["exact_statement"] = controls.expected_statement(
            controls.LEGACY_AUTHORIZATION_ID, frozen
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "legacy.json"
            path.write_text(json.dumps(action), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "consumed legacy"):
                controls.load_action(path, frozen)
        action = self.action()
        action["p7_reobservation"]["external_obligations"] = "UNSATISFIED"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "p7.json"
            path.write_text(json.dumps(action), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "P7 reobservation"):
                controls.load_action(path, frozen)

    def test_rejects_a_p7_reobservation_that_predates_its_source(self) -> None:
        frozen = controls.frozen_candidate()
        action = self.action()
        action["p7_reobservation"]["observed_at"] = "2026-01-01T00:00:00Z"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stale-p7.json"
            path.write_text(json.dumps(action), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "predates the selected source"):
                controls.load_action(path, frozen)

    def test_finalizer_has_no_effect_client_or_token_surface(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "urllib",
            "requests",
            "http.client",
            "ZENODO_ACCESS_TOKEN",
            "GITHUB_TOKEN",
            "subprocess.run([\"git\", \"push\"",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('mode.add_argument("--write"', source)
        self.assertIn('path.open("xb")', source)


if __name__ == "__main__":
    unittest.main()

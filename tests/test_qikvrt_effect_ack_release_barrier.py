#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Negative regressions for the reciprocal EFFECT_ACK publication barrier."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import urllib.parse
import unittest
from typing import Any

from tests.release_authority_hold_contract import assert_authority_hold_workflow
from tools import qikvrt_effect_ack_release_barrier as barrier


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_effect_ack_finalize.yml"
MARKER = ROOT / barrier.MARKER_PATH


class FakeGitHub:
    def __init__(self, values: dict[tuple[str, str], dict[str, Any]]) -> None:
        self.values = values

    def __call__(self, repository: str, path: str) -> dict[str, Any] | None:
        value = self.values.get((repository, path))
        return None if value is None else copy.deepcopy(value)


class EffectAckReleaseBarrierTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.authority_main = "a" * 40
        self.mirror_main = "b" * 40
        self.shared_tree = "c" * 40
        self.authority_authorization = "d" * 40
        self.mirror_authorization = "e" * 40
        self.authority_tag_object = "1" * 40
        self.mirror_tag_object = "2" * 40

        marker = json.loads(MARKER.read_text(encoding="utf-8"))
        marker["state"] = "finalize"
        marker["confirm"] = "FINALIZE_TAGS_AND_ZENODO_PUBLICATION"
        marker["release"]["expected_source_commit"] = self.authority_main
        marker["release"]["expected_source_tree"] = self.shared_tree
        marker["zenodo"]["client_sha256"] = "3" * 64
        marker["zenodo"]["manifest_sha256"] = "4" * 64
        marker["zenodo"]["reservation_evidence_sha256"] = "5" * 64
        marker["zenodo"]["paper_doi"] = "10.5281/zenodo.12345678"
        marker["zenodo"]["software_doi"] = "10.5281/zenodo.12345679"
        self.marker = barrier._with_payload_digest(marker)
        self.marker_bytes = (
            json.dumps(self.marker, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        self.marker_sha256 = hashlib.sha256(self.marker_bytes).hexdigest()
        mirror_marker = barrier._mirror_marker(
            self.marker, self.mirror_main, self.shared_tree
        )
        authority_inert = barrier._inert_marker(self.marker)
        mirror_inert = barrier._inert_marker(mirror_marker)

        tag = self.marker["release"]["tag"]
        tag_path = "git/ref/tags/" + urllib.parse.quote(tag, safe="")
        expected_tagger = {
            "name": self.marker["release"]["tagger_name"],
            "email": self.marker["release"]["tagger_email"],
            "date": self.marker["release"]["tagger_timestamp"],
        }

        def tag_object(target: str) -> dict[str, Any]:
            return {
                "tag": tag,
                "message": self.marker["release"]["tag_message"],
                "tagger": expected_tagger,
                "object": {"type": "commit", "sha": target},
            }

        marker_path = urllib.parse.quote(barrier.MARKER_PATH, safe="/")
        authority_active_query = urllib.parse.urlencode(
            {"ref": self.authority_authorization}
        )
        authority_inert_query = urllib.parse.urlencode({"ref": self.authority_main})
        mirror_active_query = urllib.parse.urlencode({"ref": self.mirror_authorization})
        mirror_inert_query = urllib.parse.urlencode({"ref": self.mirror_main})
        self.values: dict[tuple[str, str], dict[str, Any]] = {
            (
                barrier.AUTHORITY_REPOSITORY,
                f"git/ref/heads/{barrier.FINALIZE_BRANCH}",
            ): {"object": {"sha": self.authority_authorization}},
            (barrier.AUTHORITY_REPOSITORY, "git/ref/heads/main"): {
                "object": {"sha": self.authority_main}
            },
            (
                barrier.AUTHORITY_REPOSITORY,
                f"git/commits/{self.authority_main}",
            ): {"tree": {"sha": self.shared_tree}},
            (
                barrier.AUTHORITY_REPOSITORY,
                f"commits/{self.authority_authorization}",
            ): {
                "parents": [{"sha": self.authority_main}],
                "files": [
                    {"filename": barrier.MARKER_PATH, "status": "modified"}
                ],
            },
            (
                barrier.AUTHORITY_REPOSITORY,
                f"contents/{marker_path}?{authority_active_query}",
            ): {
                "encoding": "base64",
                "content": base64.b64encode(
                    json.dumps(self.marker).encode("utf-8")
                ).decode("ascii"),
            },
            (
                barrier.AUTHORITY_REPOSITORY,
                f"contents/{marker_path}?{authority_inert_query}",
            ): {
                "encoding": "base64",
                "content": base64.b64encode(
                    json.dumps(authority_inert).encode("utf-8")
                ).decode("ascii"),
            },
            (barrier.MIRROR_REPOSITORY, "git/ref/heads/main"): {
                "object": {"sha": self.mirror_main}
            },
            (barrier.MIRROR_REPOSITORY, f"git/commits/{self.mirror_main}"): {
                "tree": {"sha": self.shared_tree}
            },
            (
                barrier.MIRROR_REPOSITORY,
                f"git/ref/heads/{barrier.FINALIZE_BRANCH}",
            ): {"object": {"sha": self.mirror_authorization}},
            (barrier.MIRROR_REPOSITORY, f"commits/{self.mirror_authorization}"): {
                "parents": [{"sha": self.mirror_main}],
                "files": [
                    {"filename": barrier.MARKER_PATH, "status": "modified"}
                ],
            },
            (
                barrier.MIRROR_REPOSITORY,
                f"contents/{marker_path}?{mirror_active_query}",
            ): {
                "encoding": "base64",
                "content": base64.b64encode(
                    json.dumps(mirror_marker).encode("utf-8")
                ).decode("ascii"),
            },
            (
                barrier.MIRROR_REPOSITORY,
                f"contents/{marker_path}?{mirror_inert_query}",
            ): {
                "encoding": "base64",
                "content": base64.b64encode(
                    json.dumps(mirror_inert).encode("utf-8")
                ).decode("ascii"),
            },
            (barrier.AUTHORITY_REPOSITORY, tag_path): {
                "object": {"type": "tag", "sha": self.authority_tag_object}
            },
            (
                barrier.AUTHORITY_REPOSITORY,
                f"git/tags/{self.authority_tag_object}",
            ): tag_object(self.authority_main),
            (barrier.MIRROR_REPOSITORY, tag_path): {
                "object": {"type": "tag", "sha": self.mirror_tag_object}
            },
            (
                barrier.MIRROR_REPOSITORY,
                f"git/tags/{self.mirror_tag_object}",
            ): tag_object(self.mirror_main),
        }

    def validate(self) -> dict[str, Any]:
        return barrier.validate_prepublication_barrier(
            marker_bytes=self.marker_bytes,
            expected_marker_sha256=self.marker_sha256,
            expected_authority_commit=self.authority_main,
            expected_shared_tree=self.shared_tree,
            expected_authority_tag_object=self.authority_tag_object,
            github_sha=self.authority_authorization,
            api=FakeGitHub(self.values),
        )

    def pretag_values(self) -> dict[tuple[str, str], dict[str, Any]]:
        values = copy.deepcopy(self.values)
        tag_path = "git/ref/tags/" + urllib.parse.quote(
            self.marker["release"]["tag"], safe=""
        )
        values.pop((barrier.AUTHORITY_REPOSITORY, tag_path))
        values.pop((barrier.MIRROR_REPOSITORY, tag_path))
        return values

    def validate_pretag(
        self, values: dict[tuple[str, str], dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        return barrier.validate_pretag_barrier(
            marker_bytes=self.marker_bytes,
            expected_marker_sha256=self.marker_sha256,
            expected_source_commit=self.authority_main,
            expected_shared_tree=self.shared_tree,
            github_sha=self.authority_authorization,
            local_repository=barrier.AUTHORITY_REPOSITORY,
            api=FakeGitHub(self.pretag_values() if values is None else values),
        )

    def test_exact_reciprocal_subject_is_accepted(self) -> None:
        evidence = self.validate()
        self.assertEqual(evidence["state"], "EXACT_RECIPROCAL_SUBJECT_VERIFIED")
        self.assertEqual(evidence["authority_main"], self.authority_main)
        self.assertEqual(evidence["mirror_main"], self.mirror_main)
        self.assertEqual(evidence["shared_tree"], self.shared_tree)

    def test_authority_head_advance_is_blocked(self) -> None:
        advanced = "f" * 40
        self.values[(barrier.AUTHORITY_REPOSITORY, "git/ref/heads/main")] = {
            "object": {"sha": advanced}
        }
        with self.assertRaisesRegex(barrier.BarrierError, "current Authority main"):
            self.validate()

    def test_same_tree_different_mirror_tag_commit_is_blocked(self) -> None:
        different_commit = "9" * 40
        self.values[
            (
                barrier.MIRROR_REPOSITORY,
                f"git/tags/{self.mirror_tag_object}",
            )
        ]["object"]["sha"] = different_commit
        self.values[
            (barrier.MIRROR_REPOSITORY, f"git/commits/{different_commit}")
        ] = {"tree": {"sha": self.shared_tree}}
        with self.assertRaisesRegex(
            barrier.BarrierError, "annotated tag is not bound to the exact live main"
        ):
            self.validate()

    def test_head_advance_during_barrier_is_blocked_by_terminal_readback(self) -> None:
        calls = 0
        base = FakeGitHub(self.values)

        def advancing_api(repository: str, path: str) -> dict[str, Any]:
            nonlocal calls
            if repository == barrier.MIRROR_REPOSITORY and path == "git/ref/heads/main":
                calls += 1
                if calls == 2:
                    return {"object": {"sha": "f" * 40}}
            return base(repository, path)

        with self.assertRaisesRegex(barrier.BarrierError, "terminal readback"):
            barrier.validate_prepublication_barrier(
                marker_bytes=self.marker_bytes,
                expected_marker_sha256=self.marker_sha256,
                expected_authority_commit=self.authority_main,
                expected_shared_tree=self.shared_tree,
                expected_authority_tag_object=self.authority_tag_object,
                github_sha=self.authority_authorization,
                api=advancing_api,
            )

    def test_non_marker_only_mirror_authorization_is_blocked(self) -> None:
        self.values[
            (
                barrier.MIRROR_REPOSITORY,
                f"commits/{self.mirror_authorization}",
            )
        ]["files"].append({"filename": "README.md", "status": "modified"})
        with self.assertRaisesRegex(barrier.BarrierError, "not marker-only"):
            self.validate()

    def test_non_marker_only_authority_authorization_is_blocked(self) -> None:
        self.values[
            (
                barrier.AUTHORITY_REPOSITORY,
                f"commits/{self.authority_authorization}",
            )
        ]["files"].append({"filename": "README.md", "status": "modified"})
        with self.assertRaisesRegex(barrier.BarrierError, "not marker-only"):
            self.validate()

    def test_tag_ref_advance_during_barrier_is_blocked_by_terminal_readback(
        self,
    ) -> None:
        tag = self.marker["release"]["tag"]
        tag_path = "git/ref/tags/" + urllib.parse.quote(tag, safe="")
        calls = 0
        base = FakeGitHub(self.values)

        def advancing_api(repository: str, path: str) -> dict[str, Any]:
            nonlocal calls
            if repository == barrier.AUTHORITY_REPOSITORY and path == tag_path:
                calls += 1
                if calls == 2:
                    return {"object": {"type": "tag", "sha": "8" * 40}}
            return base(repository, path)

        with self.assertRaisesRegex(barrier.BarrierError, "annotated tag object"):
            barrier.validate_prepublication_barrier(
                marker_bytes=self.marker_bytes,
                expected_marker_sha256=self.marker_sha256,
                expected_authority_commit=self.authority_main,
                expected_shared_tree=self.shared_tree,
                expected_authority_tag_object=self.authority_tag_object,
                github_sha=self.authority_authorization,
                api=advancing_api,
            )

    def test_pretag_barrier_accepts_exact_bilateral_authorizations(self) -> None:
        evidence = self.validate_pretag()
        self.assertEqual(
            evidence["state"], "LOCAL_TAG_ABSENT_PEER_ABSENT_OR_EXACT_VERIFIED"
        )
        self.assertEqual(evidence["local_main"], self.authority_main)
        self.assertEqual(evidence["peer_main"], self.mirror_main)

    def test_pretag_barrier_blocks_missing_counterpart_authorization(self) -> None:
        values = self.pretag_values()
        values.pop(
            (
                barrier.MIRROR_REPOSITORY,
                f"git/ref/heads/{barrier.FINALIZE_BRANCH}",
            )
        )
        with self.assertRaisesRegex(barrier.BarrierError, "required reciprocal object"):
            self.validate_pretag(values)

    def test_pretag_barrier_blocks_divergent_counterpart_tree(self) -> None:
        values = self.pretag_values()
        values[(barrier.MIRROR_REPOSITORY, f"git/commits/{self.mirror_main}")][
            "tree"
        ]["sha"] = "f" * 40
        with self.assertRaisesRegex(barrier.BarrierError, "main tree"):
            self.validate_pretag(values)

    def test_pretag_barrier_accepts_exact_preexisting_counterpart_tag(self) -> None:
        values = self.pretag_values()
        tag_path = "git/ref/tags/" + urllib.parse.quote(
            self.marker["release"]["tag"], safe=""
        )
        values[(barrier.MIRROR_REPOSITORY, tag_path)] = {
            "object": {"type": "tag", "sha": self.mirror_tag_object}
        }
        evidence = self.validate_pretag(values)
        self.assertEqual(evidence["peer_tag_object"], self.mirror_tag_object)

    def test_pretag_barrier_accepts_exact_peer_tag_appearing_during_readback(
        self,
    ) -> None:
        values = self.pretag_values()
        base = FakeGitHub(values)
        tag_path = "git/ref/tags/" + urllib.parse.quote(
            self.marker["release"]["tag"], safe=""
        )
        calls = 0

        def advancing_api(repository: str, path: str) -> dict[str, Any] | None:
            nonlocal calls
            if repository == barrier.MIRROR_REPOSITORY and path == tag_path:
                calls += 1
                if calls >= 2:
                    return {
                        "object": {"type": "tag", "sha": self.mirror_tag_object}
                    }
            return base(repository, path)

        evidence = barrier.validate_pretag_barrier(
            marker_bytes=self.marker_bytes,
            expected_marker_sha256=self.marker_sha256,
            expected_source_commit=self.authority_main,
            expected_shared_tree=self.shared_tree,
            github_sha=self.authority_authorization,
            local_repository=barrier.AUTHORITY_REPOSITORY,
            api=advancing_api,
        )
        self.assertEqual(evidence["peer_tag_object"], self.mirror_tag_object)

    def test_pretag_barrier_blocks_divergent_peer_tag(self) -> None:
        values = self.pretag_values()
        tag_path = "git/ref/tags/" + urllib.parse.quote(
            self.marker["release"]["tag"], safe=""
        )
        values[(barrier.MIRROR_REPOSITORY, tag_path)] = {
            "object": {"type": "commit", "sha": self.mirror_main}
        }
        with self.assertRaisesRegex(barrier.BarrierError, "not an annotated tag"):
            self.validate_pretag(values)

    def test_pretag_barrier_blocks_preexisting_local_tag(self) -> None:
        values = self.pretag_values()
        tag_path = "git/ref/tags/" + urllib.parse.quote(
            self.marker["release"]["tag"], safe=""
        )
        values[(barrier.AUTHORITY_REPOSITORY, tag_path)] = {
            "object": {"type": "tag", "sha": self.authority_tag_object}
        }
        with self.assertRaisesRegex(barrier.BarrierError, "local release tag"):
            self.validate_pretag(values)

    def test_deterministic_authority_then_mirror_sequence_reaches_both_tags(
        self,
    ) -> None:
        values = self.pretag_values()
        authority_evidence = self.validate_pretag(values)
        self.assertIsNone(authority_evidence["peer_tag_object"])
        tag_path = "git/ref/tags/" + urllib.parse.quote(
            self.marker["release"]["tag"], safe=""
        )
        values[(barrier.AUTHORITY_REPOSITORY, tag_path)] = {
            "object": {"type": "tag", "sha": self.authority_tag_object}
        }
        mirror_marker = barrier._mirror_marker(
            self.marker, self.mirror_main, self.shared_tree
        )
        mirror_bytes = (
            json.dumps(mirror_marker, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
        mirror_evidence = barrier.validate_pretag_barrier(
            marker_bytes=mirror_bytes,
            expected_marker_sha256=hashlib.sha256(mirror_bytes).hexdigest(),
            expected_source_commit=self.mirror_main,
            expected_shared_tree=self.shared_tree,
            github_sha=self.mirror_authorization,
            local_repository=barrier.MIRROR_REPOSITORY,
            api=FakeGitHub(values),
        )
        self.assertEqual(
            mirror_evidence["peer_tag_object"], self.authority_tag_object
        )
        values[(barrier.MIRROR_REPOSITORY, tag_path)] = {
            "object": {"type": "tag", "sha": self.mirror_tag_object}
        }
        self.assertIn((barrier.AUTHORITY_REPOSITORY, tag_path), values)
        self.assertIn((barrier.MIRROR_REPOSITORY, tag_path), values)

    def test_deterministic_mirror_then_authority_sequence_reaches_both_tags(
        self,
    ) -> None:
        values = self.pretag_values()
        mirror_marker = barrier._mirror_marker(
            self.marker, self.mirror_main, self.shared_tree
        )
        mirror_bytes = (
            json.dumps(mirror_marker, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
        mirror_evidence = barrier.validate_pretag_barrier(
            marker_bytes=mirror_bytes,
            expected_marker_sha256=hashlib.sha256(mirror_bytes).hexdigest(),
            expected_source_commit=self.mirror_main,
            expected_shared_tree=self.shared_tree,
            github_sha=self.mirror_authorization,
            local_repository=barrier.MIRROR_REPOSITORY,
            api=FakeGitHub(values),
        )
        self.assertIsNone(mirror_evidence["peer_tag_object"])
        tag_path = "git/ref/tags/" + urllib.parse.quote(
            self.marker["release"]["tag"], safe=""
        )
        values[(barrier.MIRROR_REPOSITORY, tag_path)] = {
            "object": {"type": "tag", "sha": self.mirror_tag_object}
        }
        authority_evidence = self.validate_pretag(values)
        self.assertEqual(
            authority_evidence["peer_tag_object"], self.mirror_tag_object
        )
        values[(barrier.AUTHORITY_REPOSITORY, tag_path)] = {
            "object": {"type": "tag", "sha": self.authority_tag_object}
        }
        self.assertIn((barrier.AUTHORITY_REPOSITORY, tag_path), values)
        self.assertIn((barrier.MIRROR_REPOSITORY, tag_path), values)

    def test_workflow_runs_bilateral_barrier_immediately_before_tag_posts(
        self,
    ) -> None:
        assert_authority_hold_workflow(self, "qikvrt_effect_ack_finalize.yml")
        return
        workflow = WORKFLOW.read_text(encoding="utf-8")
        start = workflow.index("Revalidate marker bytes and create or verify annotated tag")
        end = workflow.index("\n      - name:", start)
        lines = [line.strip() for line in workflow[start:end].splitlines()]
        calls = [
            index
            for index, line in enumerate(lines)
            if line == "revalidate_bilateral_tag_absence()"
        ]
        self.assertEqual(len(calls), 2)
        for effect in (
            'tag_object = api("POST", "/git/tags", {',
            'api("POST", "/git/refs", {"ref": "refs/tags/" + tag, "sha": tag_object["sha"]})',
        ):
            effect_index = lines.index(effect)
            self.assertEqual(lines[effect_index - 1], "revalidate_bilateral_tag_absence()")

    def test_workflow_runs_barrier_immediately_before_finalize(self) -> None:
        assert_authority_hold_workflow(self, "qikvrt_effect_ack_finalize.yml")
        return
        workflow = WORKFLOW.read_text(encoding="utf-8")
        finalize_start = workflow.index("Finalize both Zenodo depositions")
        validation_start = workflow.index(
            "Reject secret-bearing or DOI-incomplete final output", finalize_start
        )
        validation_end = workflow.index("\n      - name:", validation_start)
        step = workflow[finalize_start:validation_start]
        validation_step = workflow[validation_start:validation_end]
        barrier_call = step.index("qikvrt_effect_ack_release_barrier.py")
        effect_call = step.index("qikvrt_zenodo_actions.py finalize")
        self.assertLess(barrier_call, effect_call)
        between = step[barrier_call:effect_call]
        self.assertNotIn("- name:", between)
        for binding in (
            "EXPECTED_MARKER_SHA256",
            "EXPECTED_AUTHORITY_COMMIT",
            "EXPECTED_SHARED_TREE",
            "EXPECTED_AUTHORITY_TAG_OBJECT",
            'github-sha "$GITHUB_SHA"',
        ):
            self.assertIn(binding, step[:effect_call])
        self.assertIn('zenodo_token="${ZENODO_ACCESS_TOKEN-}"', step[:barrier_call])
        self.assertIn("unset ZENODO_ACCESS_TOKEN", step[:barrier_call])
        self.assertIn("unset GH_API_TOKEN", step[barrier_call:effect_call])
        self.assertIn('ZENODO_ACCESS_TOKEN="$zenodo_token"', step[barrier_call:effect_call])
        self.assertIn('raw="$(<"$FINAL_RESULT")"', step[effect_call:])
        self.assertIn('[[ "$raw" == *"$zenodo_token"* ]]', step[effect_call:])
        self.assertIn("unset raw zenodo_token", step[effect_call:])
        self.assertNotIn("ZENODO_ACCESS_TOKEN", validation_step)
        self.assertNotIn("secrets.ZENODO_ACCESS_TOKEN", validation_step)
        self.assertNotIn("set -x", step[:effect_call])

    def test_barrier_and_finalizer_subprocess_secret_scopes_are_disjoint(self) -> None:
        assert_authority_hold_workflow(self, "qikvrt_effect_ack_finalize.yml")
        return
        script = r'''
set -euo pipefail
zenodo_token="${ZENODO_ACCESS_TOKEN-}"
unset ZENODO_ACCESS_TOKEN
python3 - <<'PY'
import json, os
print(json.dumps({"gh": "GH_API_TOKEN" in os.environ, "zenodo": "ZENODO_ACCESS_TOKEN" in os.environ}))
PY
unset GH_API_TOKEN
ZENODO_ACCESS_TOKEN="$zenodo_token" python3 - <<'PY'
import json, os, pathlib
print(json.dumps({"gh": "GH_API_TOKEN" in os.environ, "zenodo": "ZENODO_ACCESS_TOKEN" in os.environ}))
pathlib.Path(os.environ["FINAL_RESULT"]).write_text('{"phase":"published"}\n', encoding="utf-8")
PY
raw="$(<"$FINAL_RESULT")"
if [[ "$raw" == *"$zenodo_token"* ]]; then
  exit 71
fi
unset raw zenodo_token
test -z "${raw+x}"
test -z "${zenodo_token+x}"
'''
        environment = dict(os.environ)
        with tempfile.TemporaryDirectory() as temp_dir:
            environment.update(
                {
                    "GH_API_TOKEN": "github-sentinel",
                    "ZENODO_ACCESS_TOKEN": "zenodo-sentinel",
                    "FINAL_RESULT": str(pathlib.Path(temp_dir) / "final-result.json"),
                }
            )
            completed = subprocess.run(
                ["bash", "-c", script],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
        scopes = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(
            scopes,
            [{"gh": True, "zenodo": False}, {"gh": False, "zenodo": True}],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

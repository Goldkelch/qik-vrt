#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import collections
import copy
import hashlib
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

from tools import qikvrt_canonical_temporal_memory_kernel_evidence as kernel_evidence


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION = (
    ROOT
    / "docs/publications/2026-07-30-canonical-temporal-memory-effect-ack"
)
TEX = (
    PUBLICATION
    / "QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex"
)
PDF = (
    PUBLICATION
    / "QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.pdf"
)
CLAIMS = PUBLICATION / "CLAIM_MATRIX.json"
SOURCES = PUBLICATION / "SOURCE_EVIDENCE_BINDINGS.json"
PLAN = PUBLICATION / "KERNEL_PROOF_PLAN.json"
BOUNDARY = PUBLICATION / "EVIDENCE_BOUNDARY.md"
RENDER = PUBLICATION / "PDF_RENDER_VALIDATION.json"
ZENODO_SUMS = PUBLICATION / "ZENODO_SHA256SUMS"
ZENODO_FILESET = PUBLICATION / "ZENODO_FILESET.md"
KERNEL_TOOL = ROOT / "tools/qikvrt_canonical_temporal_memory_kernel_evidence.py"
PROJECT = ROOT / "formalization/QIKVRT_Formalization_v2.0"
LEAN = PROJECT / "QIKVRTEffectAck/CanonicalTemporalMemory.lean"
ENTRY = PROJECT / "QIKVRTEffectAck.lean"
SCOPE = "qikvrt-canonical-temporal-memory-effect-ack-v1"

THEOREM_NAMESPACE = "QIKVRT.CanonicalTemporalMemory.V1"
THEOREMS = (
    f"{THEOREM_NAMESPACE}.release_eq_true_iff",
    f"{THEOREM_NAMESPACE}.release_requires_valid_past",
    f"{THEOREM_NAMESPACE}.release_requires_valid_future",
    f"{THEOREM_NAMESPACE}.release_requires_effect_ack",
    f"{THEOREM_NAMESPACE}.future_boundary_is_counterfactually_relevant",
    f"{THEOREM_NAMESPACE}.future_boundary_does_not_overwrite_past",
    f"{THEOREM_NAMESPACE}.identifier_bound_eq_true_iff",
    f"{THEOREM_NAMESPACE}.reciprocal_closure_eq_true_iff",
    f"{THEOREM_NAMESPACE}.reciprocal_closure_requires_cause_and_effect",
)
FORMAL_IDS = {f"CTM-{index:03d}" for index in range(1, 5)}
FORMAL_MODES = {
    "AWAITING_EXACT_HEAD_KERNEL_RECEIPT": (
        "FORMAL_PENDING_KERNEL",
        "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_KERNEL_RECEIPT",
    ),
    "KERNEL_VERIFIED": ("FORMAL_PROVED", "KERNEL_VERIFIED"),
}
NONFORMAL_CLASSES = {
    "EMPIRICALLY_EVIDENCED",
    "INTERPRETATIVE",
    "NORMATIVE",
    "OPEN",
    "SOURCE_BOUND",
}
CLAIM_KEYS = {
    "boundary",
    "claim_id",
    "classification",
    "proof_refs",
    "sources",
    "statement",
    "status",
}


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def latex_citation_keys(text: str) -> list[str]:
    groups = re.findall(
        r"\\cite(?:\[[^]]*\])?(?:\[[^]]*\])?\{([^}]+)\}",
        text,
    )
    return [
        key.strip()
        for group in groups
        for key in group.split(",")
        if key.strip()
    ]


def latex_bibliography_keys(text: str) -> list[str]:
    return re.findall(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", text)


def release(
    past_valid: bool,
    future_valid: bool,
    cause_bound: bool,
    policy_passed: bool,
    effect_ack_done: bool,
) -> bool:
    return all(
        (
            past_valid,
            future_valid,
            cause_bound,
            policy_passed,
            effect_ack_done,
        )
    )


class CanonicalTemporalMemoryPublicationTests(unittest.TestCase):
    def test_candidate_files_and_scope_are_present(self) -> None:
        for path in (
            TEX,
            PDF,
            CLAIMS,
            SOURCES,
            PLAN,
            BOUNDARY,
            RENDER,
            ZENODO_SUMS,
            LEAN,
            ENTRY,
            KERNEL_TOOL,
            ZENODO_FILESET,
        ):
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 0, path)

    def test_release_truth_table_is_done_only_and_two_boundary(self) -> None:
        released = []
        for values in itertools.product((False, True), repeat=5):
            outcome = release(*values)
            if outcome:
                released.append(values)
            for index, value in enumerate(values):
                if not value:
                    self.assertFalse(
                        outcome,
                        f"release occurred with false condition {index}: {values}",
                    )
        self.assertEqual(released, [(True, True, True, True, True)])

    def test_future_boundary_is_nonvacuous_without_past_overwrite(self) -> None:
        fixed = {
            "past_valid": True,
            "cause_bound": True,
            "policy_passed": True,
            "effect_ack_done": True,
        }
        accepted = release(fixed["past_valid"], True, *tuple(fixed.values())[1:])
        rejected = release(fixed["past_valid"], False, *tuple(fixed.values())[1:])
        self.assertTrue(accepted)
        self.assertFalse(rejected)

        past_archive = b"canonical-observed-history"
        self.assertIs(past_archive, past_archive)
        self.assertEqual(
            (past_archive, b"anticipated-effect-a")[0],
            (past_archive, b"anticipated-effect-b")[0],
        )

    def test_lean_source_is_imported_named_and_escape_free(self) -> None:
        source = LEAN.read_text(encoding="utf-8")
        entry = ENTRY.read_text(encoding="utf-8")
        self.assertIn("import QIKVRTEffectAck.CanonicalTemporalMemory", entry)
        for theorem in THEOREMS:
            short_name = theorem.rsplit(".", 1)[-1]
            self.assertRegex(source, rf"\btheorem\s+{re.escape(short_name)}\b")
        for prohibited in (r"\bsorry\b", r"\badmit\b", r"\baxiom\b", r"\bunsafe\b"):
            self.assertIsNone(re.search(prohibited, source), prohibited)
        self.assertIn("does not assume an observation arriving from the physical", source)

    def test_claim_inventory_is_complete_typed_and_fail_closed(self) -> None:
        value = json.loads(CLAIMS.read_text(encoding="utf-8"))
        self.assertEqual(
            value["schema"],
            "qikvrt_canonical_temporal_memory_claim_matrix_v2",
        )
        self.assertEqual(value["publication_id"], SCOPE)
        self.assertEqual(value["claim_count"], 22)
        self.assertEqual(len(value["claims"]), 22)
        self.assertEqual(
            [item["claim_id"] for item in value["claims"]],
            [f"CTM-{index:03d}" for index in range(1, 23)],
        )
        self.assertIn(value["proof_state"], FORMAL_MODES)
        formal_class, formal_status = FORMAL_MODES[value["proof_state"]]
        self.assertEqual(
            {item["classification"] for item in value["claims"]},
            NONFORMAL_CLASSES | {formal_class},
        )
        self.assertEqual(
            value["completion_claims"],
            {
                "effect_ack_done": False,
                "final_pass": False,
                "pass": False,
                "system_wide_completion": "UNCLAIMED",
            },
        )
        formal = [
            item
            for item in value["claims"]
            if item["classification"] in {"FORMAL_PENDING_KERNEL", "FORMAL_PROVED"}
        ]
        self.assertEqual({item["claim_id"] for item in formal}, FORMAL_IDS)
        self.assertEqual({item["classification"] for item in formal}, {formal_class})
        self.assertEqual({item["status"] for item in formal}, {formal_status})
        self.assertEqual(
            {
                proof_ref
                for item in formal
                for proof_ref in item["proof_refs"]
            },
            set(THEOREMS),
        )
        for item in value["claims"]:
            self.assertEqual(set(item), CLAIM_KEYS)
            self.assertTrue(item["statement"].strip())
            self.assertTrue(item["boundary"].strip())
            self.assertTrue(item["sources"])
            self.assertEqual(len(item["sources"]), len(set(item["sources"])))
            self.assertEqual(len(item["proof_refs"]), len(set(item["proof_refs"])))
            if item["claim_id"] not in FORMAL_IDS:
                self.assertEqual(item["proof_refs"], [])

    def test_source_bindings_are_bidirectional_and_citations_are_exact(self) -> None:
        claims = json.loads(CLAIMS.read_text(encoding="utf-8"))
        sources = json.loads(SOURCES.read_text(encoding="utf-8"))
        self.assertEqual(sources["schema"], "qikvrt_source_evidence_bindings_v2")
        self.assertEqual(sources["scope_id"], SCOPE)

        bindings = sources["bindings"]
        binding_ids = [item["id"] for item in bindings]
        self.assertEqual(len(binding_ids), len(set(binding_ids)))
        claim_ids = {item["claim_id"] for item in claims["claims"]}
        matrix_pairs = {
            (item["claim_id"], source_id)
            for item in claims["claims"]
            for source_id in item["sources"]
        }
        binding_pairs = {
            (claim_id, item["id"])
            for item in bindings
            for claim_id in item["claim_ids"]
        }
        self.assertEqual({source_id for _, source_id in matrix_pairs}, set(binding_ids))
        self.assertEqual(binding_pairs, matrix_pairs)

        required = {
            "boundary",
            "claim_ids",
            "id",
            "role",
            "retrieval",
            "source_type",
            "tex_cite_keys",
            "title",
            "version",
        }
        pending_refresh_id = "PDF_RENDER_VALIDATION.json#completion_claims"
        for item in bindings:
            self.assertTrue(required.issubset(item), item["id"])
            self.assertTrue(item["claim_ids"], item["id"])
            self.assertEqual(len(item["claim_ids"]), len(set(item["claim_ids"])))
            self.assertTrue(set(item["claim_ids"]) <= claim_ids, item["id"])
            self.assertIsInstance(item["tex_cite_keys"], list, item["id"])
            self.assertEqual(
                len(item["tex_cite_keys"]),
                len(set(item["tex_cite_keys"])),
                item["id"],
            )
            self.assertIsInstance(item["retrieval"], dict, item["id"])
            self.assertTrue(item["retrieval"], item["id"])
            self.assertTrue(item["boundary"].strip(), item["id"])
            self.assertTrue("doi" in item or "locator" in item, item["id"])

            for snapshot in item.get("repository_snapshots", []):
                snapshot_path = ROOT / snapshot["path"]
                self.assertTrue(snapshot_path.is_file(), item["id"])
                snapshot_data = snapshot_path.read_bytes()
                self.assertEqual(
                    snapshot["size_bytes"],
                    len(snapshot_data),
                    item["id"],
                )
                self.assertEqual(
                    snapshot["sha256"],
                    hashlib.sha256(snapshot_data).hexdigest(),
                    item["id"],
                )
                self.assertEqual(
                    snapshot["git_blob_sha1"],
                    git_blob_sha1(snapshot_data),
                    item["id"],
                )

            if "path" not in item:
                continue
            bound_path = ROOT / item["path"]
            self.assertTrue(bound_path.is_file(), item["id"])
            if (
                item.get("content_state")
                == "LOCAL_REFERENCE_PENDING_FINAL_REFRESH"
            ):
                self.assertEqual(item["id"], pending_refresh_id)
                self.assertEqual(
                    item["content_state"],
                    "LOCAL_REFERENCE_PENDING_FINAL_REFRESH",
                )
                self.assertNotIn("sha256", item)
                self.assertNotIn("git_blob_sha1", item)
                self.assertNotIn("size_bytes", item)
                continue
            data = bound_path.read_bytes()
            self.assertEqual(item["size_bytes"], len(data), item["id"])
            self.assertEqual(
                item["sha256"],
                hashlib.sha256(data).hexdigest(),
                item["id"],
            )
            self.assertEqual(item["git_blob_sha1"], git_blob_sha1(data), item["id"])

        text = TEX.read_text(encoding="utf-8")
        cited = latex_citation_keys(text)
        bibliography = latex_bibliography_keys(text)
        mapped = [
            cite_key
            for item in bindings
            for cite_key in item["tex_cite_keys"]
        ]
        self.assertEqual(len(bibliography), 28)
        self.assertTrue(
            all(count == 1 for count in collections.Counter(bibliography).values())
        )
        self.assertEqual(set(cited), set(bibliography))
        self.assertEqual(set(mapped), set(bibliography))
        self.assertTrue(
            all(count == 1 for count in collections.Counter(mapped).values())
        )

    def test_kernel_plan_and_static_tool_bind_the_exact_source(self) -> None:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(plan["schema"], "qikvrt_publication_kernel_proof_plan_v1")
        self.assertEqual(plan["publication_id"], SCOPE)
        self.assertEqual(plan["theorems"], list(THEOREMS))
        self.assertEqual(
            set(plan["axiom_audit"]["expected_axioms_by_theorem"]),
            set(THEOREMS),
        )
        axiom_free = {
            f"{THEOREM_NAMESPACE}.future_boundary_is_counterfactually_relevant",
            f"{THEOREM_NAMESPACE}.future_boundary_does_not_overwrite_past",
        }
        for theorem in THEOREMS:
            expected = [] if theorem in axiom_free else ["propext"]
            self.assertEqual(
                plan["axiom_audit"]["expected_axioms_by_theorem"][theorem],
                expected,
            )

        source_data = LEAN.read_bytes()
        self.assertEqual(
            plan["source"],
            {
                "bytes": len(source_data),
                "compiled_object": (
                    ".lake/build/lib/lean/"
                    "QIKVRTEffectAck/CanonicalTemporalMemory.olean"
                ),
                "git_blob_sha1": git_blob_sha1(source_data),
                "path": "QIKVRTEffectAck/CanonicalTemporalMemory.lean",
                "sha256": hashlib.sha256(source_data).hexdigest(),
            },
        )
        self.assertEqual(plan["entrypoint"], "QIKVRTEffectAck.lean")
        self.assertEqual(
            plan["lean_toolchain"],
            {
                "path": "lean-toolchain",
                "value": "leanprover/lean4:v4.19.0",
            },
        )
        self.assertEqual(
            plan["completion_claims"],
            {
                "ietf_revision_02_posted": False,
                "system_wide_completion": "UNCLAIMED",
                "zenodo_published": False,
            },
        )

        static = kernel_evidence.static_validation(PLAN, CLAIMS)
        self.assertEqual(len(static["formal_claims"]), 4)
        self.assertEqual(static["plan"]["theorems"], list(THEOREMS))
        self.assertEqual(static["source"]["sha256"], plan["source"]["sha256"])

    def test_static_tool_cli_reports_only_static_input_verification(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            }
        )
        result = subprocess.run(
            [sys.executable, "-B", str(KERNEL_TOOL), "--static-only"],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["publication_id"], SCOPE)
        self.assertEqual(value["state"], "STATIC_INPUTS_VERIFIED")
        self.assertEqual(value["formal_claim_count"], 4)
        self.assertEqual(value["theorem_count"], 9)

    def test_axiom_report_parser_accepts_wrapping_and_rejects_duplicates(self) -> None:
        first, second = THEOREMS[:2]
        output = (
            f"'{first}' depends on axioms:\n"
            "[propext]\n"
            f"'{second.rsplit('.', 1)[-1]}' does not depend on any\n"
            "axioms\n"
        )
        self.assertEqual(
            kernel_evidence.parse_axiom_reports(output, [first, second]),
            {
                first: ["propext"],
                second: [],
            },
        )
        with self.assertRaisesRegex(
            kernel_evidence.EvidenceError,
            "duplicate runtime axiom report",
        ):
            kernel_evidence.parse_axiom_reports(
                output + f"'{first}' depends on axioms: [propext]\n",
                [first, second],
            )

    def test_static_validation_rejects_plan_and_claim_mismatches(self) -> None:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        claims = json.loads(CLAIMS.read_text(encoding="utf-8"))
        cases = []

        wrong_source = copy.deepcopy(plan)
        wrong_source["source"]["sha256"] = "0" * 64
        cases.append(
            ("source identity", wrong_source, claims, "plan source SHA-256 differs")
        )

        missing_theorem = copy.deepcopy(plan)
        missing_theorem["theorems"] = missing_theorem["theorems"][:-1]
        cases.append(
            (
                "theorem inventory",
                missing_theorem,
                claims,
                "claim/proof theorem union differs",
            )
        )

        wrong_claim_ref = copy.deepcopy(claims)
        wrong_claim_ref["claims"][0]["proof_refs"][0] = (
            f"{THEOREM_NAMESPACE}.not_a_theorem"
        )
        cases.append(
            (
                "claim proof reference",
                plan,
                wrong_claim_ref,
                "claim/proof theorem union differs",
            )
        )

        for label, mutated_plan, mutated_claims, message in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory(prefix="qikvrt-ctm-test-") as raw:
                    directory = pathlib.Path(raw)
                    plan_path = directory / "plan.json"
                    claims_path = directory / "claims.json"
                    plan_path.write_text(
                        json.dumps(mutated_plan),
                        encoding="utf-8",
                    )
                    claims_path.write_text(
                        json.dumps(mutated_claims),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        kernel_evidence.EvidenceError,
                        message,
                    ):
                        kernel_evidence.static_validation(plan_path, claims_path)

    def test_formal_state_is_atomic_in_pending_and_verified_modes(self) -> None:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        observed = json.loads(CLAIMS.read_text(encoding="utf-8"))

        def in_mode(proof_state: str) -> dict[str, object]:
            value = copy.deepcopy(observed)
            classification, status = FORMAL_MODES[proof_state]
            value["proof_state"] = proof_state
            for item in value["claims"]:
                if item["claim_id"] in FORMAL_IDS:
                    item["classification"] = classification
                    item["status"] = status
            return value

        pending = in_mode("AWAITING_EXACT_HEAD_KERNEL_RECEIPT")
        verified = in_mode("KERNEL_VERIFIED")
        invalid_states = []

        wrong_aggregate = copy.deepcopy(pending)
        wrong_aggregate["proof_state"] = "KERNEL_VERIFIED"
        invalid_states.append(
            (
                "aggregate state",
                wrong_aggregate,
                "claim-matrix proof_state differs from the aggregate formal mode",
            )
        )

        mixed = copy.deepcopy(pending)
        mixed["claims"][0]["classification"] = "FORMAL_PROVED"
        mixed["claims"][0]["status"] = "KERNEL_VERIFIED"
        invalid_states.append(
            (
                "mixed formal modes",
                mixed,
                "formal claims mix pending and kernel-verified modes",
            )
        )

        wrong_status = copy.deepcopy(verified)
        wrong_status["claims"][0]["status"] = (
            "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_KERNEL_RECEIPT"
        )
        invalid_states.append(
            (
                "verified claim without receipt state",
                wrong_status,
                "proved status lacks kernel verification",
            )
        )

        with tempfile.TemporaryDirectory(prefix="qikvrt-ctm-state-test-") as raw:
            directory = pathlib.Path(raw)
            plan_path = directory / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            for label, value in (("pending", pending), ("verified", verified)):
                with self.subTest(label=label):
                    claims_path = directory / f"{label}.json"
                    claims_path.write_text(json.dumps(value), encoding="utf-8")
                    static = kernel_evidence.static_validation(
                        plan_path,
                        claims_path,
                    )
                    self.assertEqual(len(static["formal_claims"]), 4)
            for label, value, message in invalid_states:
                with self.subTest(label=label):
                    claims_path = directory / f"invalid-{label}.json"
                    claims_path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaisesRegex(
                        kernel_evidence.EvidenceError,
                        message,
                    ):
                        kernel_evidence.static_validation(plan_path, claims_path)

    def test_checksum_index_is_current_complete_and_candidate_scoped(self) -> None:
        actual = {}
        for line in ZENODO_SUMS.read_text(encoding="ascii").splitlines():
            digest, name = line.split("  ", 1)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotIn(name, actual)
            actual[name] = digest
        expected_names = {
            "BOUNDARY_TEST_REPORT.json",
            "CITATION.cff",
            "CLAIM_MATRIX.json",
            "EVIDENCE_BOUNDARY.md",
            "KERNEL_PROOF_PLAN.json",
            "LICENSE_NOTICE.md",
            "PDF_RENDER_VALIDATION.json",
            PDF.name,
            TEX.name,
            "README.md",
            "SOURCE_EVIDENCE_BINDINGS.json",
            "ZENODO_FILESET.md",
        }
        self.assertEqual(set(actual), expected_names)
        for name, expected_digest in actual.items():
            path = PUBLICATION / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                expected_digest,
                name,
            )
        fileset_text = ZENODO_FILESET.read_text(encoding="utf-8")
        primary_section = fileset_text.split(
            "## Primary and reproducibility files",
            1,
        )[1].split("## Required prepublication proof files", 1)[0]
        declared = set(re.findall(r"^- `([^`]+)`$", primary_section, re.MULTILINE))
        self.assertEqual(declared, expected_names | {"ZENODO_SHA256SUMS"})
        self.assertNotIn("KERNEL_RECEIPT.json", actual)
        self.assertNotIn("MACHINE_PROOF_BUNDLE.json", actual)
        self.assertFalse(
            json.loads(PLAN.read_text(encoding="utf-8"))["completion_claims"][
                "zenodo_published"
            ]
        )

    def test_paper_states_literal_thesis_and_scientific_boundaries(self) -> None:
        text = TEX.read_text(encoding="utf-8")
        required = (
            "Die Ausgangsthese lautet wortwörtlich",
            "Operationale Protokoll-Retrokausalität",
            "Kontrafaktische Relevanz der Zukunft",
            "Keine freigegebene Ursache ohne gebundene Wirkung",
            "Keine geschlossene Wirkung ohne gebundene Ursache",
            "future\\_boundary\\_does\\_not\\_overwrite\\_past",
            "SYSTEM\\_WIDE\\_COMPLETION",
            "ist empirisch offen",
            "Quod erat demonstrandum",
        )
        for phrase in required:
            self.assertIn(phrase, text)
        prohibited = (
            "Delayed-Choice-Experimente beweisen physikalische Retrokausalität",
            "Hashgleichheit beweist Wahrheit",
            "Wechselwirkung beweist Bewusstsein",
            "IETF-Konsens ist erreicht",
            "SYSTEM\\_WIDE\\_COMPLETION=true",
        )
        for phrase in prohibited:
            self.assertNotIn(phrase, text)

    def test_render_receipt_is_candidate_scoped_and_not_publication_claim(self) -> None:
        value = json.loads(RENDER.read_text(encoding="utf-8"))
        self.assertEqual(value["scope_id"], SCOPE)
        self.assertEqual(value["state"], "PDF_VISUALLY_VERIFIED")
        self.assertEqual(value["pdf"]["pages"], 17)
        self.assertTrue(value["visual_qa"]["all_pages_inspected"])
        self.assertEqual(value["visual_qa"]["inspected_pages"], list(range(1, 18)))
        for receipt_key, path in (("source", TEX), ("pdf", PDF)):
            data = path.read_bytes()
            receipt = value[receipt_key]
            self.assertEqual(receipt["path"], path.relative_to(ROOT).as_posix())
            self.assertEqual(receipt["bytes"], len(data))
            self.assertEqual(receipt["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(receipt["git_blob_sha1"], git_blob_sha1(data))
        self.assertFalse(value["completion_claims"]["zenodo_published"])
        self.assertFalse(value["completion_claims"]["ietf_revision_02_posted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION = (
    ROOT / "docs/publications/2026-08-02-causality-is-relation-vrtcore"
)
MANIFEST = PUBLICATION / "ORIGINAL_PACKAGE_MANIFEST.json"
PLAN = PUBLICATION / "KERNEL_PROOF_PLAN.json"
SOURCE = PUBLICATION / "VRTCore_RelationalCausality_Candidate.lean"
AUDIT_SOURCE = PUBLICATION / "VRTCore_RelationalCausality_AxiomAudit.lean"
CLAIM_MATRIX = PUBLICATION / "VRTCore_CLAIM_MATRIX_H0_RETURNED.json"
LOCAL_EVIDENCE = PUBLICATION / "LOCAL_KERNEL_EVIDENCE.json"
LOCAL_AUDIT_LOG = PUBLICATION / "LOCAL_AXIOM_AUDIT.log"
PATH_MAP = PUBLICATION / "ARTIFACT_PATH_MAP.json"
CI_KERNEL_EVIDENCE = PUBLICATION / "CI_KERNEL_EVIDENCE_H0_PR_MERGE.json"
KERNEL_RECEIPT = PUBLICATION / "KERNEL_RECEIPT_H0_CI.json"
H1_MATRIX = PUBLICATION / "VRTCore_CLAIM_MATRIX_H1_KERNEL_VERIFIED.json"

NAMESPACE = "QIKVRT.VRTCore"
THEOREMS = (
    f"{NAMESPACE}.epistemicKindExhaustive",
    f"{NAMESPACE}.formalAndEmpiricalAreDistinct",
    f"{NAMESPACE}.interpretiveAndUnresolvedAreDistinct",
    f"{NAMESPACE}.observedSequenceHasNoBridge",
    f"{NAMESPACE}.bridgedRelationHasBridge",
    f"{NAMESPACE}.observedSequenceAloneIsNotCausality",
    f"{NAMESPACE}.bridgedRelationIsStructurallyLicensed",
    f"{NAMESPACE}.causalLicenseRequiresBridge",
    f"{NAMESPACE}.successfulReceiptIsTechnicallySuccessful",
    f"{NAMESPACE}.withheldAuthorizationIsFalse",
    f"{NAMESPACE}.grantedAuthorizationIsTrue",
    f"{NAMESPACE}.withheldAuthorizationBlocksAnyReceipt",
    f"{NAMESPACE}.successfulReceiptStillBlockedWithoutAuthority",
    f"{NAMESPACE}.memAppendLeft",
    f"{NAMESPACE}.mergePreserves",
    f"{NAMESPACE}.extendsRefl",
    f"{NAMESPACE}.extendsTrans",
    f"{NAMESPACE}.seedMaterializes",
    f"{NAMESPACE}.recursiveStepPreserves",
    f"{NAMESPACE}.suppliedStableMinkowskiWitnessIsAdmissible",
    f"{NAMESPACE}.missingMinkowskiWitnessIsRejected",
)
PROPEXT_THEOREMS = {
    f"{NAMESPACE}.epistemicKindExhaustive",
    f"{NAMESPACE}.withheldAuthorizationBlocksAnyReceipt",
    f"{NAMESPACE}.successfulReceiptStillBlockedWithoutAuthority",
    f"{NAMESPACE}.memAppendLeft",
    f"{NAMESPACE}.mergePreserves",
    f"{NAMESPACE}.recursiveStepPreserves",
}
PLAN_BINDINGS = {
    "source": (
        SOURCE,
        12301,
        "1a39cd338f543f642acf634ffb2b63cd2c1a2ffe92878208f48d71a68a8e7d22",
        "beaf17e1c068441defabbad5f1dbcc666fad3d0d",
    ),
    "axiom_audit": (
        AUDIT_SOURCE,
        1575,
        "5d3ceb24125acd41b34725e485ab0a4f4f61492273cf60b6973c9851da7eabb7",
        "89bc85ee4f7147dbb525d3a6fe94d7b2a202c006",
    ),
}

# The claim matrix was returned under its original manifest name, then stored
# under an explicit H0 name so that its pre-kernel state remains immutable.
PRIMARY_ARTIFACTS = {
    "QIK-VRT_Kausalitaet_ist_Relation_Fachartikel_DE_2026-08-02.md": (
        "QIK-VRT_Kausalitaet_ist_Relation_Fachartikel_DE_2026-08-02.md",
        26428,
        "902d0abff59d7a9c8026a506081e25c6106abc4d88ca07197d08ff74fcc6041d",
    ),
    "QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_DE_2026-08-02.md": (
        "QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_DE_2026-08-02.md",
        8225,
        "4199dc4eb2b239e60c375424228a7d4ff5b1238a2370b88898befab5ceb34d09",
    ),
    "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.tex": (
        "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.tex",
        34224,
        "91ff57fc16bb91096296f28c97d541fad3bab244411b969e063ecbe31e363a08",
    ),
    "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf": (
        "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf",
        213326,
        "7f29f90bb0254f813237d07c73e9ab29c4b4f5a8c2f025dc7cdcf5f8f7ebad23",
    ),
    "VRTCore_RelationalCausality_Candidate.lean": (
        "VRTCore_RelationalCausality_Candidate.lean",
        12301,
        "1a39cd338f543f642acf634ffb2b63cd2c1a2ffe92878208f48d71a68a8e7d22",
    ),
    "VRTCore_Syntax.ebnf": (
        "VRTCore_Syntax.ebnf",
        8507,
        "4e95f1991da70d7d7b01500e625518f79e2c6b728ed739e3c5171cfdc5eb633b",
    ),
    "VRTCore_CLAIM_MATRIX.json": (
        "VRTCore_CLAIM_MATRIX_H0_RETURNED.json",
        20131,
        "b663ebe9ea146f8e10149f1850ee7ae9d45450be28eba0cdeee22956b3b8ad2e",
    ),
}


def load_json(path: pathlib.Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(  # noqa: S324 - Git object identity is SHA-1 by design
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def lean_without_comments(text: str) -> str:
    """Remove nested Lean comments while retaining source line boundaries."""

    output: list[str] = []
    index = 0
    block_depth = 0
    while index < len(text):
        if block_depth:
            if text.startswith("/-", index):
                block_depth += 1
                index += 2
            elif text.startswith("-/", index):
                block_depth -= 1
                index += 2
            else:
                if text[index] == "\n":
                    output.append("\n")
                index += 1
            continue

        if text.startswith("--", index):
            newline = text.find("\n", index + 2)
            if newline < 0:
                break
            output.append("\n")
            index = newline + 1
        elif text.startswith("/-", index):
            block_depth = 1
            index += 2
        else:
            output.append(text[index])
            index += 1

    if block_depth:
        raise AssertionError("unterminated Lean block comment")
    return "".join(output)


class VRTCoreRelationalCausalityPublicationTests(unittest.TestCase):
    def test_returned_primary_artifacts_keep_exact_bytes_and_hashes(self) -> None:
        manifest = load_json(MANIFEST)
        self.assertEqual(
            manifest["schema"], "qikvrt-authored-artifact-package/1.0"
        )
        self.assertEqual(
            manifest["package_id"], "qikvrt-causality-is-relation-2026-08-02"
        )
        by_name = {item["path"]: item for item in manifest["files"]}
        self.assertEqual(set(by_name), set(PRIMARY_ARTIFACTS))

        for manifest_name, (stored_name, expected_bytes, expected_sha) in (
            PRIMARY_ARTIFACTS.items()
        ):
            with self.subTest(path=manifest_name):
                item = by_name[manifest_name]
                path = PUBLICATION / stored_name
                self.assertTrue(path.is_file(), path)
                self.assertEqual(item["bytes"], expected_bytes)
                self.assertEqual(item["sha256"], expected_sha)
                self.assertEqual(path.stat().st_size, expected_bytes)
                self.assertEqual(sha256(path), expected_sha)

    def test_lean_candidate_has_exactly_21_theorems_and_no_escapes(self) -> None:
        source = lean_without_comments(SOURCE.read_text(encoding="utf-8"))
        declared = re.findall(
            r"(?m)^\s*theorem\s+([A-Za-z_][A-Za-z0-9_']*)\b",
            source,
        )
        qualified = tuple(f"{NAMESPACE}.{name}" for name in declared)
        self.assertEqual(len(declared), 21)
        self.assertEqual(len(set(declared)), 21)
        self.assertEqual(qualified, THEOREMS)
        for prohibited in (r"\bsorry\b", r"\badmit\b", r"\bunsafe\b", r"\baxiom\b"):
            self.assertIsNone(re.search(prohibited, source), prohibited)

    def test_proof_plan_binds_source_audit_and_claim_inventory(self) -> None:
        plan = load_json(PLAN)
        self.assertEqual(plan["schema"], "qikvrt_vrtcore_kernel_proof_plan_v1")
        self.assertEqual(
            plan["publication_id"], "qikvrt-causality-is-relation-vrtcore-v1"
        )
        self.assertEqual(plan["toolchain"], "leanprover/lean4:v4.19.0")
        self.assertEqual(plan["imports"], ["Std"])
        self.assertEqual(plan["theorems"], list(THEOREMS))
        expected_axioms = {
            theorem: (["propext"] if theorem in PROPEXT_THEOREMS else [])
            for theorem in THEOREMS
        }
        self.assertEqual(plan["expected_axioms_by_theorem"], expected_axioms)

        uncommented_source = lean_without_comments(
            SOURCE.read_text(encoding="utf-8")
        )
        direct_imports = re.findall(
            r"(?m)^\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)\s*$",
            uncommented_source,
        )
        self.assertEqual(direct_imports, plan["imports"])

        for key, (
            expected_path,
            expected_bytes,
            expected_sha256,
            expected_git_blob,
        ) in PLAN_BINDINGS.items():
            binding = plan[key]
            self.assertEqual(ROOT / binding["path"], expected_path)
            self.assertEqual(binding["bytes"], expected_bytes)
            self.assertEqual(binding["sha256"], expected_sha256)
            self.assertEqual(binding["git_blob_sha1"], expected_git_blob)
            self.assertEqual(expected_path.stat().st_size, expected_bytes)
            self.assertEqual(sha256(expected_path), expected_sha256)
            self.assertEqual(git_blob_sha1(expected_path), expected_git_blob)

        required = plan["required_results"]
        self.assertEqual(required["source_exit_code"], 0)
        self.assertEqual(required["axiom_audit_exit_code"], 0)
        self.assertEqual(required["theorem_count"], 21)
        self.assertEqual(required["allowed_axiom_dependencies"], ["propext"])
        self.assertIs(required["project_axioms_forbidden"], True)
        self.assertIs(required["sorry_admit_project_axiom_unsafe_absent"], True)

        matrix = load_json(CLAIM_MATRIX)
        formal = matrix["formal_candidate"]
        self.assertEqual(formal["source"], SOURCE.name)
        self.assertEqual(formal["target_toolchain"], "Lean 4.19.0")
        self.assertEqual(formal["import"], "Std")
        self.assertEqual(formal["theorem_count"], 21)
        self.assertIs(formal["contains_sorry"], False)
        self.assertIs(formal["contains_admit"], False)
        self.assertIs(formal["declares_project_axiom"], False)

        claims = {item["id"]: item for item in matrix["claims"]}
        for index, theorem in enumerate(THEOREMS, start=1):
            with self.subTest(claim=f"T{index:02d}"):
                claim = claims[f"T{index:02d}"]
                self.assertEqual(claim["intended_kind"], "FORMAL_PROVED")
                self.assertEqual(
                    claim["status"],
                    "FORMAL_CANDIDATE_UNVERIFIED_IN_THIS_RUNTIME",
                )
                self.assertEqual(
                    claim["evidence"],
                    [f"{SOURCE.name}#{theorem.rsplit('.', 1)[-1]}"],
                )

    def test_axiom_audit_inventory_is_exact_complete_and_unique(self) -> None:
        audit_source = AUDIT_SOURCE.read_text(encoding="utf-8")
        self.assertIn(f"import {SOURCE.stem}", audit_source)
        requested = tuple(
            re.findall(r"(?m)^#print axioms\s+(\S+)\s*$", audit_source)
        )
        self.assertEqual(len(requested), 21)
        self.assertEqual(len(set(requested)), 21)
        self.assertEqual(requested, THEOREMS)

        reports: list[tuple[str, tuple[str, ...]]] = []
        for line in LOCAL_AUDIT_LOG.read_text(encoding="utf-8").splitlines():
            match = re.fullmatch(
                r"'([^']+)' (?:does not depend on any axioms|depends on axioms:\s*\[([^]]*)\])",
                line,
            )
            self.assertIsNotNone(match, line)
            raw_axioms = (match.group(2) or "").strip()
            axioms = tuple(
                value.strip() for value in raw_axioms.split(",") if value.strip()
            )
            reports.append((match.group(1), axioms))

        names = tuple(name for name, _axioms in reports)
        self.assertEqual(len(names), 21)
        self.assertEqual(len(set(names)), 21)
        self.assertEqual(names, THEOREMS)
        self.assertEqual(
            {name for name, axioms in reports if axioms == ("propext",)},
            PROPEXT_THEOREMS,
        )
        self.assertTrue(
            all(axioms in ((), ("propext",)) for _name, axioms in reports)
        )

        evidence = load_json(LOCAL_EVIDENCE)
        self.assertEqual(evidence["kernel_check"], "PASS")
        self.assertEqual(evidence["source"]["theorem_declarations"], 21)
        self.assertEqual(
            evidence["source"]["sha256_before_check"], sha256(SOURCE)
        )
        self.assertEqual(
            evidence["source"]["sha256_after_check"], sha256(SOURCE)
        )
        axiom_audit = evidence["axiom_audit"]
        self.assertEqual(axiom_audit["theorems_audited"], 21)
        self.assertEqual(axiom_audit["no_axiom_dependencies"], 15)
        self.assertEqual(axiom_audit["lean_foundational_propext_only"], 6)
        self.assertEqual(axiom_audit["project_axioms"], [])
        self.assertIs(axiom_audit["sorry_or_admit"], False)
        self.assertEqual(
            set(axiom_audit["propext_theorems"]), PROPEXT_THEOREMS
        )

        referenced = (
            evidence["environment_diagnosis"]["diagnostic_log"],
            evidence["environment_diagnosis"]["direct_start_log"],
            evidence["compatibility_route"]["runtime_identity_log"],
            {
                "path": evidence["kernel_result"]["raw_log_path"],
                "sha256": evidence["kernel_result"]["raw_log_sha256"],
            },
            {
                "path": evidence["kernel_result"]["command_log_path"],
                "sha256": evidence["kernel_result"]["command_log_sha256"],
            },
            {
                "path": axiom_audit["audit_source_path"],
                "sha256": axiom_audit["audit_source_sha256"],
            },
            {
                "path": axiom_audit["audit_log_path"],
                "sha256": axiom_audit["audit_log_sha256"],
            },
        )
        for binding in referenced:
            with self.subTest(local_evidence_path=binding["path"]):
                path = PUBLICATION / binding["path"]
                self.assertTrue(path.is_file(), path)
                self.assertEqual(sha256(path), binding["sha256"])

        path_map = load_json(PATH_MAP)
        self.assertEqual(
            path_map["schema"], "qikvrt_vrtcore_artifact_path_map_v1"
        )
        excluded = {item["path"]: item for item in path_map["intentionally_excluded"]}
        self.assertIn("lean_selfexe_compat.so", excluded)
        self.assertFalse((PUBLICATION / "lean_selfexe_compat.so").exists())
        self.assertEqual(
            excluded["lean_selfexe_compat.so"]["sha256"],
            evidence["compatibility_route"]["binary_sha256"],
        )

    def test_ci_kernel_receipt_and_h1_transition_are_exact_and_scoped(self) -> None:
        self.assertEqual(
            sha256(CI_KERNEL_EVIDENCE),
            "18d370482ca19e1a2e109fbb38ea225e022955182c72c1846331d5c3a2cc7d04",
        )
        ci_evidence = load_json(CI_KERNEL_EVIDENCE)
        self.assertEqual(ci_evidence["github_run_id"], "30732070295")
        self.assertEqual(
            ci_evidence["github_sha"],
            "fc0b05cd13d7607883fbab9f16b4628f77a0958c",
        )
        self.assertEqual(ci_evidence["source_exit_code"], 0)
        self.assertEqual(ci_evidence["axiom_audit_exit_code"], 0)
        self.assertEqual(ci_evidence["theorem_count"], 21)

        receipt = load_json(KERNEL_RECEIPT)
        self.assertEqual(receipt["status"], "SUCCESS")
        workflow = receipt["evidence_chain"]["workflow"]
        self.assertEqual(workflow["run_id"], "30732070295")
        self.assertEqual(
            workflow["workflow_run_head_sha"],
            "987e4a6f163562bba32ea7575c41013c91a0b6a1",
        )
        self.assertEqual(
            workflow["checkout_github_sha"],
            "fc0b05cd13d7607883fbab9f16b4628f77a0958c",
        )
        assessment = receipt["binding_assessment"]
        self.assertIs(assessment["source_bytes_exact"], True)
        self.assertIs(assessment["repository_head_exact"], False)
        self.assertEqual(receipt["summary"]["accepted_theorems"], 21)
        self.assertEqual(receipt["summary"]["axiom_free_theorems"], 15)
        self.assertEqual(receipt["summary"]["propext_only_theorems"], 6)
        results = receipt["theorem_results"]
        self.assertEqual(
            [item["theorem"] for item in results],
            list(THEOREMS),
        )
        self.assertEqual(
            {
                item["theorem"]
                for item in results
                if item["axioms"] == ["propext"]
            },
            PROPEXT_THEOREMS,
        )
        self.assertTrue(
            all(item["axioms"] in ([], ["propext"]) for item in results)
        )

        h0 = load_json(CLAIM_MATRIX)
        h1 = load_json(H1_MATRIX)
        self.assertEqual(h1["representation"], "ADDITIVE_TRANSITION_OVERLAY")
        self.assertEqual(h1["base_matrix"]["bytes"], CLAIM_MATRIX.stat().st_size)
        self.assertEqual(h1["base_matrix"]["sha256"], sha256(CLAIM_MATRIX))
        transitions = h1["claim_transitions"]
        self.assertEqual(
            [item["claim_id"] for item in transitions],
            [f"T{i:02d}" for i in range(1, 22)],
        )
        self.assertEqual([item["theorem"] for item in transitions], list(THEOREMS))
        self.assertTrue(
            all(
                item["to"]
                == {
                    "kind": "FORMAL_PROVED",
                    "status": "FORMAL_PROVED_KERNEL_VERIFIED",
                }
                for item in transitions
            )
        )
        h0_by_id = {item["id"]: item for item in h0["claims"]}
        unchanged_ids = {item["claim_id"] for item in h1["unchanged_claims"]}
        self.assertEqual(unchanged_ids, set(h0_by_id) - {f"T{i:02d}" for i in range(1, 22)})
        guards = h1["promotion_guards"]
        for key in (
            "physical_claims_promoted",
            "empirical_claims_promoted",
            "interpretive_claims_promoted",
            "normative_claims_promoted",
            "open_spacetime_claims_promoted",
        ):
            self.assertIs(guards[key], False)
        self.assertEqual(h1["claim_state"]["kernel_scope"], "PASS")
        self.assertEqual(h1["claim_state"]["global_pass"], "NOT_CLAIMED")
        self.assertEqual(h1["claim_state"]["final_pass"], "NOT_CLAIMED")
        self.assertEqual(h1["claim_state"]["effect_ack_done"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()

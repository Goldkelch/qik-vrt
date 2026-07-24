from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from materialize_completion import (  # noqa: E402
    ALL_FORMAL_BINDINGS,
    CLOSED_STATUSES,
    DEFAULT_PROVENANCE,
    generate,
)
from audit_proof_escapes import FORBIDDEN_CODE, strip_comments_and_strings  # noqa: E402
from validate_completion_claim_graph import validate  # noqa: E402
from verify_source_lock import verify_source_lock  # noqa: E402


class ClaimPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.environments_path = PROJECT_ROOT / "claims" / "TEX_ENVIRONMENTS.json"
        cls.matrix_path = PROJECT_ROOT / "claims" / "APPENDIX_MATRIX.json"
        cls.graph_path = PROJECT_ROOT / "claims" / "CLAIM_GRAPH.json"
        cls.environments = json.loads(cls.environments_path.read_text(encoding="utf-8"))
        cls.matrix = json.loads(cls.matrix_path.read_text(encoding="utf-8"))
        cls.graph = json.loads(cls.graph_path.read_text(encoding="utf-8"))

    def assertHasError(self, errors: list[str], fragment: str) -> None:
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected an error containing {fragment!r}; got {errors}",
        )

    def test_positive_locked_source_and_fresh_completion_materialization(self) -> None:
        self.assertEqual(verify_source_lock(DEFAULT_PROVENANCE), [])
        environments, matrix, graph = generate(DEFAULT_PROVENANCE)
        self.assertEqual(environments, self.environments)
        self.assertEqual(matrix, self.matrix)
        self.assertEqual(graph, self.graph)
        self.assertEqual(validate(graph, environments, matrix), [])

    def test_inventory_exact_counts_and_proof_associations(self) -> None:
        self.assertEqual(
            self.environments["counts"],
            {
                "definitions": 20,
                "theoremLike": 20,
                "formal": 40,
                "remarks": 5,
                "proofBlocks": 17,
            },
        )
        associations = [
            proof["associatedEnvironmentId"]
            for proof in self.environments["proofBlocks"]
        ]
        self.assertEqual(len(associations), 17)
        self.assertEqual(len(set(associations)), 17)
        formal = [item for item in self.environments["environments"] if item["formal"]]
        self.assertEqual(len(formal), 40)
        self.assertTrue(all(item["claimIds"] for item in formal))

    def test_matrix_exactly_34_epistemically_classified_rows(self) -> None:
        self.assertEqual(len(self.matrix["rows"]), 34)
        self.assertTrue(all(row["epistemicCategory"] for row in self.matrix["rows"]))
        for row in self.matrix["rows"]:
            if row["epistemicCategory"] in {"EMPIRICAL", "INTERPRETIVE", "NORMATIVE"}:
                self.assertFalse(row["machineProofBindingAllowed"])

    def test_proof_escape_scanner_ignores_comments_and_strings(self) -> None:
        source = '-- sorry\n/- axiom hidden : Prop -/\ndef label := "admit constant"\n'
        stripped = strip_comments_and_strings(source)
        self.assertIsNone(FORBIDDEN_CODE.search(stripped))

    def test_proof_escape_scanner_finds_inline_placeholder(self) -> None:
        stripped = strip_comments_and_strings("theorem bad : True := by exact sorry\n")
        match = FORBIDDEN_CODE.search(stripped)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), "sorry")

    def test_legacy_batch01_bindings_are_preserved(self) -> None:
        nodes = {node["id"]: node for node in self.graph["nodes"]}
        expected = {"MAP-003", "GAT-004", "GAT-005", "GAT-006", "RET-011"}
        actual = {
            node_id
            for node_id, node in nodes.items()
            if node.get("formalBinding") is not None
            if node["formalBinding"].get("batch") == "Batch01A"
        }
        self.assertEqual(actual, expected)
        for node_id in expected:
            self.assertEqual(nodes[node_id]["formalizationStatus"], "KERNEL_CHECKED")
            self.assertEqual(nodes[node_id]["formalBinding"]["bindingStrength"], "STRONG")
        self.assertEqual(len(nodes["RET-011"]["sourceSpanIds"]), 3)

    def test_legacy_batch02_subclaims_remain_distinct(self) -> None:
        nodes = {node["id"]: node for node in self.graph["nodes"]}
        expected_full = {"SET-001", "MAP-001", "SET-003", "GAT-002"}
        expected_subclaims = {"QUA-003A", "DIM-006A", "DIM-007A"}
        for node_id in expected_full:
            self.assertEqual(nodes[node_id]["formalBinding"]["claimScope"], "FULL_ENVIRONMENT")
        for node_id in expected_subclaims:
            self.assertEqual(nodes[node_id]["formalBinding"]["claimScope"], "SOURCE_SUBCLAIM")
        for parent_id in {"QUA-003", "DIM-006", "DIM-007"}:
            self.assertIn(nodes[parent_id]["formalizationStatus"], CLOSED_STATUSES)
            self.assertIsNotNone(nodes[parent_id]["formalBinding"])
            self.assertNotEqual(
                nodes[parent_id]["formalBinding"]["proofConstant"],
                nodes[parent_id + "A"]["formalBinding"]["proofConstant"],
            )

    def test_all_twenty_definitions_have_strong_kernel_bindings(self) -> None:
        nodes = {node["id"]: node for node in self.graph["nodes"]}
        for index in range(1, 21):
            node = nodes[f"DEF-{index:03d}"]
            self.assertEqual(node["formalizationStatus"], "KERNEL_CHECKED")
            self.assertEqual(node["formalBinding"]["claimScope"], "DEFINITION_BINDING")
            self.assertEqual(node["formalBinding"]["bindingStrength"], "STRONG")

    def test_all_twenty_theorem_environments_are_closed(self) -> None:
        nodes = {node["id"]: node for node in self.graph["nodes"]}
        theorem_environments = [
            item for item in self.environments["environments"]
            if item["group"] == "theoremLike"
        ]
        self.assertEqual(len(theorem_environments), 20)
        for environment in theorem_environments:
            self.assertTrue(
                all(nodes[claim_id]["formalizationStatus"] in CLOSED_STATUSES
                    for claim_id in environment["claimIds"]),
                environment["id"],
            )

    def test_completion_scope_and_status_are_explicit(self) -> None:
        nodes = {node["id"]: node for node in self.graph["nodes"]}
        conditional = {"ESC-004", "ESC-005", "ESC-003", "QUA-004", "QUA-005", "DIM-006"}
        exact = {"QUA-003", "GAT-003", "GAT-007", "DIM-007"}
        for claim_id in conditional:
            self.assertEqual(nodes[claim_id]["formalizationStatus"], "CONDITIONAL_CHECKED")
            self.assertEqual(
                nodes[claim_id]["formalBinding"]["claimScope"],
                "CONDITIONAL_ENVIRONMENT",
            )
        for claim_id in exact:
            self.assertEqual(nodes[claim_id]["formalizationStatus"], "KERNEL_CHECKED")
            self.assertEqual(nodes[claim_id]["formalBinding"]["claimScope"], "FULL_ENVIRONMENT")

    def test_graph_completion_counts_are_explicit(self) -> None:
        self.assertEqual(
            self.graph["counts"],
            {
                "nodes": 43,
                "definitionNodes": 20,
                "strongBindings": 42,
                "kernelCheckedClaims": 42,
                "conditionalCheckedClaims": 6,
                "pendingNodes": 0,
            },
        )
        self.assertEqual(set(ALL_FORMAL_BINDINGS), {
            node["id"] for node in self.graph["nodes"] if node.get("formalBinding")
        })

    def test_no_formal_obligation_remains_pending(self) -> None:
        for node in self.graph["nodes"]:
            if node["epistemicCategory"] in {"DEFINITION", "MATHEMATICAL", "CONDITIONAL"}:
                self.assertIn(node["formalizationStatus"], CLOSED_STATUSES, node["id"])
                self.assertIsNotNone(node["formalBinding"], node["id"])

    def test_negative_wrong_source_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.tex"
            source.write_bytes(b"locked source\n")
            provenance = root / "SOURCE_PROVENANCE.json"
            provenance.write_text(
                json.dumps({
                    "sourceFiles": {"tex": {
                        "path": "source.tex", "sha256": "0" * 64, "lineCount": 1,
                    }},
                    "policy": {"sourceBytesImmutable": True, "lineSpanHashesAreNormative": True},
                }),
                encoding="utf-8",
            )
            errors = verify_source_lock(provenance)
            self.assertHasError(errors, "sha256 mismatch")
            self.assertNotEqual(hashlib.sha256(source.read_bytes()).hexdigest(), "0" * 64)

    def test_negative_missing_environment_is_rejected(self) -> None:
        environments = copy.deepcopy(self.environments)
        environments["environments"] = environments["environments"][:-1]
        errors = validate(self.graph, environments, self.matrix)
        self.assertHasError(errors, "formal: expected 40")

    def test_negative_dependency_cycle_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        nodes = {node["id"]: node for node in graph["nodes"]}
        nodes["DEF-001"]["dependencies"] = ["DEF-002"]
        nodes["DEF-002"]["dependencies"] = ["DEF-001"]
        errors = validate(graph, self.environments, self.matrix)
        self.assertHasError(errors, "claim dependency cycle")

    def test_negative_stale_lean_type_binding_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "ESC-004")
        node["formalBinding"]["leanSourceSha256"] = "0" * 64
        errors = validate(graph, self.environments, self.matrix)
        self.assertHasError(errors, "stale Lean source fingerprint")

    def test_negative_stale_indexed_registry_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "DEF-001")
        node["formalBinding"]["registrySourceSha256"] = "f" * 64
        errors = validate(graph, self.environments, self.matrix)
        self.assertHasError(errors, "stale registry source fingerprint")

    def test_negative_subclaim_cannot_substitute_for_parent_binding(self) -> None:
        graph = copy.deepcopy(self.graph)
        nodes = {node["id"]: node for node in graph["nodes"]}
        nodes["QUA-003"]["formalBinding"] = copy.deepcopy(nodes["QUA-003A"]["formalBinding"])
        errors = validate(graph, self.environments, self.matrix)
        self.assertHasError(errors, "QUA-003 binding")

    def test_negative_forbidden_empirical_promotion_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["nodes"].append({
            "id": "EMP-TEST",
            "statement": "Synthetic empirical hypothesis.",
            "epistemicCategory": "EMPIRICAL",
            "formalizationStatus": "KERNEL_CHECKED",
            "dependencies": ["SRC-001"],
            "environmentIds": [],
            "sourceSpanIds": ["SPAN-TEX-3469-3469"],
            "proofBlockIds": [],
            "formalBinding": copy.deepcopy(graph["nodes"][1]["formalBinding"]),
        })
        errors = validate(graph, self.environments, self.matrix)
        self.assertHasError(errors, "proof binding forbidden for EMPIRICAL")


if __name__ == "__main__":
    unittest.main()

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

from extract_tex_inventory import (  # noqa: E402
    DEFAULT_PROVENANCE,
    generate,
)
from audit_proof_escapes import FORBIDDEN_CODE, strip_comments_and_strings  # noqa: E402
from validate_claim_graph import validate_claim_graph  # noqa: E402
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

    def test_positive_locked_source_and_fresh_extraction(self) -> None:
        self.assertEqual(verify_source_lock(DEFAULT_PROVENANCE), [])
        environments, matrix, graph = generate(DEFAULT_PROVENANCE)
        self.assertEqual(environments, self.environments)
        self.assertEqual(matrix, self.matrix)
        self.assertEqual(graph, self.graph)
        self.assertEqual(validate_claim_graph(graph, environments, matrix), [])

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

    def test_batch01a_has_five_strong_multi_span_bindings(self) -> None:
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
            self.assertEqual(
                nodes[node_id]["formalBinding"]["bindingStrength"], "STRONG"
            )
        self.assertEqual(len(nodes["RET-011"]["sourceSpanIds"]), 3)
        self.assertEqual(nodes["GAT-005"]["sourceSpanIds"], nodes["GAT-006"]["sourceSpanIds"])

    def test_batch02_has_seven_exactly_scoped_strong_bindings(self) -> None:
        nodes = {node["id"]: node for node in self.graph["nodes"]}
        expected_full = {"SET-001", "MAP-001", "SET-003", "GAT-002"}
        expected_subclaims = {"QUA-003A", "DIM-006A", "DIM-007A"}
        actual = {
            node_id
            for node_id, node in nodes.items()
            if node.get("formalBinding") is not None
            if node["formalBinding"].get("batch", "").startswith("Batch02")
        }
        self.assertEqual(actual, expected_full | expected_subclaims)
        for node_id in expected_full:
            self.assertEqual(
                nodes[node_id]["formalBinding"]["claimScope"],
                "FULL_ENVIRONMENT",
            )
        for node_id in expected_subclaims:
            self.assertEqual(
                nodes[node_id]["formalBinding"]["claimScope"],
                "SOURCE_SUBCLAIM",
            )
        for parent_id in {"QUA-003", "DIM-006", "DIM-007"}:
            self.assertEqual(nodes[parent_id]["formalizationStatus"], "PENDING")
            self.assertIsNone(nodes[parent_id]["formalBinding"])

    def test_graph_coverage_counts_are_explicit(self) -> None:
        self.assertEqual(
            self.graph["counts"],
            {
                "nodes": 43,
                "definitionNodes": 20,
                "kernelCheckedClaims": 12,
                "pendingNodes": 30,
            },
        )

    def test_non_batch_formal_obligations_remain_pending(self) -> None:
        for node in self.graph["nodes"]:
            if node["epistemicCategory"] not in {"DEFINITION", "MATHEMATICAL", "CONDITIONAL"}:
                continue
            binding = node.get("formalBinding")
            if binding is None:
                self.assertEqual(node["formalizationStatus"], "PENDING", node["id"])

    def test_negative_wrong_source_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.tex"
            source.write_bytes(b"locked source\n")
            provenance = root / "SOURCE_PROVENANCE.json"
            provenance.write_text(
                json.dumps(
                    {
                        "sourceFiles": {
                            "tex": {
                                "path": "source.tex",
                                "sha256": "0" * 64,
                                "lineCount": 1,
                            }
                        },
                        "policy": {
                            "sourceBytesImmutable": True,
                            "lineSpanHashesAreNormative": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            errors = verify_source_lock(provenance)
            self.assertHasError(errors, "sha256 mismatch")
            self.assertNotEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(),
                "0" * 64,
            )

    def test_negative_missing_environment_is_rejected(self) -> None:
        environments = copy.deepcopy(self.environments)
        environments["environments"] = environments["environments"][:-1]
        errors = validate_claim_graph(self.graph, environments, self.matrix)
        self.assertHasError(errors, "formal: expected 40")

    def test_negative_dependency_cycle_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        nodes = {node["id"]: node for node in graph["nodes"]}
        nodes["DEF-001"]["dependencies"] = ["DEF-002"]
        nodes["DEF-002"]["dependencies"] = ["DEF-001"]
        errors = validate_claim_graph(graph, self.environments, self.matrix)
        self.assertHasError(errors, "claim dependency cycle")

    def test_negative_stale_lean_type_binding_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "MAP-003")
        node["formalBinding"]["leanSourceSha256"] = "0" * 64
        errors = validate_claim_graph(graph, self.environments, self.matrix)
        self.assertHasError(errors, "stale Lean source fingerprint")

    def test_negative_stale_indexed_registry_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        node = next(item for item in graph["nodes"] if item["id"] == "GAT-004")
        node["formalBinding"]["registrySourceSha256"] = "f" * 64
        errors = validate_claim_graph(graph, self.environments, self.matrix)
        self.assertHasError(errors, "stale registry source fingerprint")

    def test_negative_subclaim_cannot_promote_pending_parent(self) -> None:
        graph = copy.deepcopy(self.graph)
        parent = next(item for item in graph["nodes"] if item["id"] == "QUA-003")
        child = next(item for item in graph["nodes"] if item["id"] == "QUA-003A")
        parent["formalizationStatus"] = "KERNEL_CHECKED"
        parent["formalBinding"] = copy.deepcopy(child["formalBinding"])
        errors = validate_claim_graph(graph, self.environments, self.matrix)
        self.assertHasError(errors, "parent claim QUA-003 must remain pending")

    def test_negative_forbidden_empirical_promotion_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["nodes"].append(
            {
                "id": "EMP-TEST",
                "statement": "Synthetic empirical hypothesis for a negative test.",
                "epistemicCategory": "EMPIRICAL",
                "formalizationStatus": "PENDING",
                "dependencies": ["SRC-001"],
                "environmentIds": [],
                "sourceSpanIds": [],
                "proofBlockIds": [],
                "formalBinding": None,
            }
        )
        node = next(item for item in graph["nodes"] if item["id"] == "SET-001")
        node["dependencies"].append("EMP-TEST")
        errors = validate_claim_graph(graph, self.environments, self.matrix)
        self.assertHasError(errors, "forbidden dependency/promotion")

    def test_negative_proof_binding_on_interpretation_is_rejected(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["nodes"].append(
            {
                "id": "INT-TEST",
                "statement": "Synthetic interpretation for a negative test.",
                "epistemicCategory": "INTERPRETIVE",
                "formalizationStatus": "KERNEL_CHECKED",
                "dependencies": ["SRC-001"],
                "environmentIds": [],
                "sourceSpanIds": ["SPAN-TEX-3469-3469"],
                "proofBlockIds": [],
                "formalBinding": {
                    "proofSystem": "Lean4",
                    "bindingStrength": "STRONG",
                    "batch": "NEGATIVE-TEST",
                    "module": "Forbidden",
                    "statementConstant": "Forbidden.statement",
                    "proofConstant": "Forbidden.checked",
                },
            }
        )
        errors = validate_claim_graph(graph, self.environments, self.matrix)
        self.assertHasError(errors, "proof binding forbidden for INTERPRETIVE")


if __name__ == "__main__":
    unittest.main()

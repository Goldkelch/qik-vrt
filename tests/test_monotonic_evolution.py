# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Synthetic contract tests, never represented as real capability/performance evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.qikvrt_monotonic_evolution import GateError, SCHEMA, assess, read_bound


def h(label):
    return hashlib.sha256(label.encode()).hexdigest()


def fixture():
    a = {"repository": "Goldkelch/qik-vrt", "head": "a" * 40, "tree": "b" * 40}
    b = {"repository": "Goldkelch/qik-vrt", "head": "c" * 40, "tree": "d" * 40}
    def witness(subject, name):
        return {"subject": copy.deepcopy(subject), "execution_id": name, "sha256": h(name)}
    old = {"schema": SCHEMA, "subject": a,
           "nodes": {"n1": h("n1"), "n2": h("n2")},
           "edges": {"e1": {"source": "n1", "target": "n2", "relation": "supports", "sha256": h("e1")}},
           "capabilities": {"transcribe.de": {"contract_sha256": h("quality-and-cold-restore-contract"), "status": "PASS", "witness": witness(a, "old-cap")}},
           "performance": {"latency.ns": {"direction": "min", "unit": "ns", "workload_sha256": h("fixed-workload"), "environment_sha256": h("fixed-machine"), "protocol_sha256": h("five-sorted-samples-v1"), "samples": [10, 20, 30, 40, 50], "witness": witness(a, "old-perf")}}}
    new = copy.deepcopy(old)
    new["subject"] = b
    new["nodes"]["n3"] = h("n3")
    new["capabilities"]["transcribe.de"]["witness"] = witness(b, "new-cap")
    new["performance"]["latency.ns"]["witness"] = witness(b, "new-perf")
    return old, new, copy.deepcopy(a), copy.deepcopy(b)


class MonotonicEvolutionTests(unittest.TestCase):
    def setUp(self):
        self.old, self.new, self.a, self.b = fixture()

    def result(self):
        return assess(self.old, self.new, self.a, self.b)

    def blocked(self, reason):
        result = self.result()
        self.assertFalse(result["eligible"], result)
        self.assertIn(reason, result["reason"])
        self.assertFalse(result["promotion_executed"])
        self.assertFalse(result["effect_ack_done"])

    def test_equal_performance_with_new_evidence_not_claimed_as_improvement(self):
        result = self.result()
        self.assertTrue(result["eligible"])
        self.assertFalse(result["strict_capability_or_performance_improvement"])
        self.assertEqual(result["disposition"], "NON_REGRESSING_EVIDENCE_EXTENSION")

    def test_strict_latency_improvement_uses_existing_classifier(self):
        self.new["performance"]["latency.ns"]["samples"] = [9, 19, 29, 39, 49]
        result = self.result()
        self.assertTrue(result["eligible"])
        self.assertEqual(result["performance"], "NON_REGRESSING_GATE_IMPROVEMENT")

    def test_better_mean_cannot_mask_worse_tail(self):
        self.new["performance"]["latency.ns"]["samples"] = [1, 2, 3, 4, 51]
        self.blocked("PERFORMANCE_REGRESSION")

    def test_higher_is_better_orientation(self):
        for state in (self.old, self.new):
            state["performance"]["latency.ns"]["direction"] = "max"
        self.new["performance"]["latency.ns"]["samples"] = [11, 21, 31, 41, 51]
        self.assertTrue(self.result()["eligible"])
        self.new["performance"]["latency.ns"]["samples"][0] = 9
        self.blocked("PERFORMANCE_REGRESSION")

    def test_no_metric_tradeoff(self):
        for state in (self.old, self.new):
            state["performance"]["memory.bytes"] = copy.deepcopy(state["performance"]["latency.ns"])
            state["performance"]["memory.bytes"]["unit"] = "bytes"
        self.new["performance"]["latency.ns"]["samples"] = [1, 2, 3, 4, 5]
        self.new["performance"]["memory.bytes"]["samples"] = [10, 20, 30, 40, 51]
        self.blocked("PERFORMANCE_REGRESSION")

    def test_node_deletion(self):
        del self.new["nodes"]["n2"]
        self.blocked("DANGLING_EDGE")

    def test_node_rewrite(self):
        self.new["nodes"]["n1"] = h("revision")
        self.blocked("NODES_REMOVED_OR_REWRITTEN")

    def test_edge_deletion(self):
        self.new["edges"] = {}
        self.blocked("EDGES_REMOVED_OR_REWRITTEN")

    def test_edge_rewrite(self):
        self.new["edges"]["e1"]["relation"] = "contradicts"
        self.blocked("EDGES_REMOVED_OR_REWRITTEN")

    def test_append_correction_preserves_history(self):
        self.new["edges"]["e2"] = {"source": "n3", "target": "n1", "relation": "contradicts", "sha256": h("e2")
        }
        self.assertTrue(self.result()["eligible"])

    def test_capability_failure_or_skip(self):
        for status in ("FAIL", "SKIP", "UNAVAILABLE"):
            with self.subTest(status=status):
                self.new["capabilities"]["transcribe.de"]["status"] = status
                self.blocked("CAPABILITY_NOT_PASSED")

    def test_removed_capability_not_hidden_by_new_one(self):
        self.new["capabilities"]["another"] = self.new["capabilities"].pop("transcribe.de")
        self.blocked("CAPABILITY_REMOVED")

    def test_weakened_capability_contract(self):
        self.new["capabilities"]["transcribe.de"]["contract_sha256"] = h("help-instead-of-inference")
        self.blocked("CAPABILITY_CONTRACT_CHANGED")

    def test_previous_head_witness(self):
        self.new["capabilities"]["transcribe.de"]["witness"]["subject"] = self.a
        self.blocked("WITNESS_SUBJECT_MISMATCH")

    def test_previous_execution_or_receipt_reuse(self):
        self.new["performance"]["latency.ns"]["witness"]["sha256"] = self.old["capabilities"]["transcribe.de"]["witness"]["sha256"]
        self.blocked("PREDECESSOR_RECEIPT_REUSED")

    def test_environment_workload_protocol_or_unit_change_holds(self):
        for field in ("environment_sha256", "workload_sha256", "protocol_sha256", "unit", "direction"):
            _, self.new, _, _ = fixture()
            with self.subTest(field=field):
                self.new["performance"]["latency.ns"][field] = "max" if field == "direction" else h("changed")
                self.blocked("INCOMPARABLE_")

    def test_metric_removed_not_hidden_by_another(self):
        self.new["performance"]["new"] = self.new["performance"].pop("latency.ns")
        self.blocked("METRIC_REMOVED")

    def test_sample_count_changed(self):
        self.new["performance"]["latency.ns"]["samples"].append(60)
        self.blocked("SAMPLE_COUNT_CHANGED")

    def test_nan_bool_and_negative_not_measurements(self):
        for sample in (True, float("nan"), float("inf"), -1, "1"):
            with self.subTest(sample=sample):
                self.new["performance"]["latency.ns"]["samples"][0] = sample
                self.blocked("INVALID_SAMPLE")

    def test_invalid_baseline_is_not_candidate_regression(self):
        self.old["capabilities"]["transcribe.de"]["status"] = "FAIL"
        self.assertEqual(self.result()["disposition"], "HOLD")

    def test_missing_real_observations_holds(self):
        self.new["performance"] = {}
        self.blocked("MISSING_PERFORMANCE")

    def test_no_evidence_growth_does_not_count_as_progress(self):
        del self.new["nodes"]["n3"]
        self.blocked("NO_NEW_EVIDENCE")

    def test_wrong_candidate_head_or_tree(self):
        self.new["subject"]["tree"] = "e" * 40
        self.blocked("OBSERVATION_SUBJECT_MISMATCH")

    def test_new_capability_requires_pass(self):
        self.new["capabilities"]["new"] = copy.deepcopy(self.new["capabilities"]["transcribe.de"])
        self.new["capabilities"]["new"]["status"] = "FAIL"
        self.blocked("CAPABILITY_NOT_PASSED")

    def test_bound_input_rejects_digest_drift_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.json"
            p.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(GateError, "INPUT_DIGEST_MISMATCH"):
                read_bound(p, "0" * 64)
            with self.assertRaisesRegex(GateError, "DUPLICATE_JSON_KEY"):
                read_bound(p, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_cli_real_files_and_exit_codes(self):
        script = Path(__file__).resolve().parents[1] / "tools/qikvrt_monotonic_evolution.py"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for scenario, expected in (("accept", 0), ("reject", 1), ("unknown", 2)):
                _, candidate, _, _ = fixture()
                if scenario == "reject": candidate["performance"]["latency.ns"]["samples"][-1] = 51
                if scenario == "unknown": candidate["performance"] = {}
                argv = [sys.executable, str(script)]
                for name, value in (("baseline", self.old), ("candidate", candidate), ("bindings", {"baseline": self.a, "candidate": self.b})):
                    p = root / f"{name}.json"
                    p.write_text(json.dumps(value))
                    argv += [f"--{name}", str(p), f"--{name}-sha256", hashlib.sha256(p.read_bytes()).hexdigest()]
                result = subprocess.run(argv, text=True, capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
                self.assertFalse(json.loads(result.stdout)["promotion_executed"])


if __name__ == "__main__":
    unittest.main()

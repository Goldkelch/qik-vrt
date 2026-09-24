import hashlib
import unittest

from src.qikvrt_temdd_semantic_ir import (
    SemanticIRHold,
    evidence_admitted,
    project_event,
    project_evidence,
    subject_id,
)


SUBJECT = {
    "repository": "Goldkelch/qik-vrt",
    "pr": 1103,
    "head": "1" * 40,
    "tree": "2" * 40,
}


def persisted():
    return {
        "schema": "qikvrt_temdd_event_v1",
        "kind": "READBACK",
        "subject": dict(SUBJECT),
        "provenance": {
            "source": "repository",
            "native_event_id": "review:123",
            "source_order": 7,
        },
        "emitted_at": "2026-09-18T12:00:00Z",
        "observed_at": "2026-09-18T12:00:01Z",
        "message": "fresh exact-subject readback",
        "payload": {
            "cause_event_ids": ["epoch:1"],
            "inputs": ["artifact:a"],
            "outputs": ["receipt:b"],
            "evidence_refs": ["evidence:c"],
            "decision": "HOLD_UNVERIFIED",
        },
        "recorded_at": "2026-09-18T12:00:02Z",
        "payload_digest": "3" * 64,
        "evidence_transfer": "DENY",
        "dod": False,
        "id": "a" * 32 + ":2",
        "observation_order": 2,
        "ledger_digest": "4" * 64,
    }


class TEMDDSemanticIRTests(unittest.TestCase):
    def test_event_projection_preserves_subject_causality_and_provenance(self):
        event = project_event(persisted())
        self.assertEqual(event["subject_id"], subject_id(SUBJECT))
        self.assertEqual(event["cause_event_ids"], ["epoch:1"])
        self.assertEqual(event["source_order"], 7)
        self.assertEqual(event["observation_order"], 2)
        self.assertEqual(event["decision"], "HOLD_UNVERIFIED")
        self.assertEqual(event["evidence_transfer"], "DENY")

    def test_sequence_does_not_invent_cause(self):
        row = persisted()
        row["payload"] = {}
        event = project_event(row)
        self.assertEqual(event["cause_event_ids"], [])
        self.assertEqual(event["observation_order"], 2)

    def test_predecessor_evidence_is_rejected(self):
        event = project_event(persisted())
        evidence = project_evidence(
            event,
            evidence_id="evidence:1",
            evidence_type="READBACK",
            content_digest=hashlib.sha256(b"receipt").hexdigest(),
            freshness="FRESH",
            epistemic="TRUE",
        )
        self.assertTrue(evidence_admitted(evidence, SUBJECT))
        successor = dict(SUBJECT, head="5" * 40)
        self.assertFalse(evidence_admitted(evidence, successor))

    def test_stale_evidence_is_rejected(self):
        event = project_event(persisted())
        evidence = project_evidence(
            event,
            evidence_id="evidence:stale",
            evidence_type="NODE_HEALTH",
            content_digest=hashlib.sha256(b"old").hexdigest(),
            freshness="STALE",
            epistemic="STALE",
        )
        self.assertFalse(evidence_admitted(evidence, SUBJECT))

    def test_unknown_or_malformed_required_semantics_fail_closed(self):
        row = persisted()
        row["evidence_transfer"] = "ALLOW"
        with self.assertRaises(SemanticIRHold):
            project_event(row)


if __name__ == "__main__":
    unittest.main()

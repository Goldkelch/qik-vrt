# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools import qikvrt_io_roundtrip as roundtrip


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class IoRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "requests" / "io").mkdir(parents=True)
        self.request_path = (
            self.root / "requests" / "io" / "io-turn-20260807-162149-v1.json"
        )
        self.user_raw = (
            "QIK-VRT ist der kanonische Arbeits- und Evidenzraum.\n"
            "Repository-Wahrheit entsteht durch Materialisierung und Beleg."
        )
        self.assistant_raw = (
            "Der Turn wurde metadata-only gebunden; Publikation bleibt gesperrt."
        )
        self.request = self.make_request()
        self.write_request()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_event(
        self,
        *,
        event_id: str,
        sequence: int,
        role: str,
        raw: str,
        scope: str,
        semantic_projection: dict[str, object],
        references: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {
            "event_id": event_id,
            "sequence": sequence,
            "role": role,
            "created_at": f"2026-08-07T16:2{sequence}:49+02:00",
            "purpose": "qikvrt_canonical_evidence_roundtrip",
            "consent_id": "OWNER_IO_ROUNDTRIP_PERSISTENCE_AUTOMATION_V1",
            "retention_until": "2036-08-07T00:00:00+02:00",
            "media_type": "text/markdown; charset=utf-8",
            "content_binding": {
                "scope": scope,
                "normalization": "NONE",
                "bytes": len(raw.encode("utf-8")),
                "sha256": digest(raw),
                "transport_exact_bytes_available": scope
                == "APPLICATION_VISIBLE_UTF8",
                "raw_content_persisted": False,
                "raw_content_absence_reason": (
                    "METADATA_ONLY retention; exact application-visible digest "
                    "and semantic projection retained."
                ),
            },
            "semantic_projection": semantic_projection,
            "external_references": references or [],
            "epistemic_class": (
                "HUMAN_ASSERTION_AND_REFERENCE_CONTEXT"
                if role == "user"
                else "ARTIFICIAL_COGNITIVE_STATUS_REPORT"
            ),
        }

    def make_request(self) -> dict[str, object]:
        user_event_id = "event-user-20260807-162149-v1"
        assistant_event_id = "event-assistant-20260807-162249-v1"
        return {
            "_license": {
                "classification": "machine_readable_capture_request",
                "copyright": "Copyright 2026 Ingolf Lohmann",
                "license": "CC-BY-NC-ND-4.0",
                "rights_holder": "Ingolf Lohmann",
            },
            "schema": roundtrip.REQUEST_SCHEMA,
            "request_id": "io-turn-20260807-162149-v1",
            "work_unit_id": "IO-TURN-20260807-162149-V1",
            "conversation_id": "conversation-qikvrt-20260807-v1",
            "created_at": "2026-08-07T16:21:49+02:00",
            "retention_mode": "METADATA_ONLY",
            "source": {
                "repository": "Goldkelch/qik-vrt",
                "ref": "refs/heads/agent/io-roundtrip-persistence-requirement-v1",
                "commit": "1" * 40,
                "tree": "2" * 40,
            },
            "authorization": {
                "owner_authorization_id": (
                    "OWNER_IO_ROUNDTRIP_PERSISTENCE_AUTOMATION_V1"
                ),
                "repository_continuation_delegation_id": (
                    "OWNER-AUTONOMOUS-REPOSITORY-CONTINUATION-V2"
                ),
                "persistence_confirmation": roundtrip.CONFIRM_CAPTURE,
                "external_effects_default": "FORBIDDEN",
            },
            "actors": {
                "human": {
                    "attribution_id": "Ingolf Lohmann",
                    "role": "Product Owner and author",
                },
                "artificial_cognitive_system": {
                    "attribution_id": "OpenAI/ChatGPT/GPT-5.6-Pro",
                    "role": "analysis, implementation and verification",
                    "session_or_run_id": "UNAVAILABLE",
                },
            },
            "events": [
                self.make_event(
                    event_id=user_event_id,
                    sequence=1,
                    role="user",
                    raw=self.user_raw,
                    scope="APPLICATION_VISIBLE_UTF8",
                    semantic_projection={
                        "assertions": [
                            "QIK-VRT is the canonical working and evidence space.",
                            (
                                "Repository truth requires materialization, exact "
                                "binding, verification and receipt."
                            ),
                        ],
                        "symbolic_marker": ".o8∞8o.",
                    },
                    references=[
                        {
                            "uri": "https://open.spotify.com/track/example-one",
                            "relation": "musical resonance reference",
                            "retrieval_state": "NOT_RETRIEVED",
                            "evidence_status": "REFERENCE_ONLY",
                            "content_digest": None,
                        }
                    ],
                ),
                self.make_event(
                    event_id=assistant_event_id,
                    sequence=2,
                    role="assistant",
                    raw=self.assistant_raw,
                    scope="PREPARED_ASSISTANT_MARKDOWN",
                    semantic_projection={
                        "status": "MATERIALIZED_CONTINUE",
                        "boundaries": [
                            "No Zenodo publication executed.",
                            "No IETF submission executed.",
                            "Exact-head CI remains required.",
                        ],
                    },
                ),
            ],
            "publication_disposition": {
                "candidate_knowledge": [
                    {
                        "claim_id": "claim-canonical-evidence-space-v1",
                        "summary": (
                            "QIK-VRT and /AI are the Product-Owner-declared "
                            "canonical working and evidence entrypoint."
                        ),
                        "epistemic_class": (
                            "OWNER_ASSERTION_AND_REPOSITORY_NORMATIVE_CONTRACT"
                        ),
                        "verification_state": (
                            "REPOSITORY_ENTRYPOINT_REOBSERVED; BROADER_CLAIM_NOT_INFERRED"
                        ),
                        "source_event_ids": [user_event_id],
                    },
                    {
                        "claim_id": "claim-materialization-boundary-v1",
                        "summary": (
                            "Repository truth requires materialization, exact "
                            "binding, verification and receipt."
                        ),
                        "epistemic_class": "NORMATIVE_REPOSITORY_POLICY",
                        "verification_state": "MACHINE_READABLE_POLICY_CANDIDATE",
                        "source_event_ids": [user_event_id],
                    },
                ],
                "zenodo": {
                    "state": "HOLD",
                    "reason_codes": [
                        "NO_STANDALONE_PROOF_BEARING_PUBLICATION_CANDIDATE",
                        "EXACT_ARTIFACT_AUTHORIZATION_ABSENT",
                    ],
                    "next_gate": (
                        "CLASSIFY_DERIVED_KNOWLEDGE_AND_BUILD_MACHINE_PROOF_BUNDLE"
                    ),
                    "external_effect_authorized": False,
                    "external_effect_executed": False,
                },
                "ietf": {
                    "state": "NOT_APPLICABLE",
                    "reason_codes": [
                        "MUSICAL_REFERENCE_IS_NOT_AN_INTERNET_STANDARDIZATION_SUBJECT",
                        "NO_NEW_PROTOCOL_DELTA_CLASSIFIED",
                    ],
                    "next_gate": (
                        "RECLASSIFY_ONLY_IF_A_CONCRETE_INTEROPERABILITY_DELTA_EXISTS"
                    ),
                    "external_effect_authorized": False,
                    "external_effect_executed": False,
                },
            },
            "integration_gaps": [
                {
                    "gap_id": "gap-host-automatic-capture-hook-v1",
                    "state": "OPEN_EXTERNAL_INTEGRATION_BOUNDARY",
                    "reason": (
                        "The repository cannot observe an opaque chat host unless "
                        "the client invokes this controller with event bindings."
                    ),
                    "required_closure": (
                        "Integrate capture invocation into every conforming client "
                        "before user return and verify the resulting receipt."
                    ),
                }
            ],
            "release_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }

    def write_request(self) -> None:
        self.request_path.write_text(
            json.dumps(
                self.request,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def capture(self) -> dict[str, object]:
        return roundtrip.capture(
            self.root,
            self.request_path,
            confirm=roundtrip.CONFIRM_CAPTURE,
        )

    def test_capture_verify_and_idempotent_round_trip(self) -> None:
        first = self.capture()
        self.assertEqual(first["state"], "VERIFIED_CONTINUE")
        self.assertEqual(first["event_count"], 2)
        self.assertFalse(first["raw_content_persisted"])
        self.assertEqual(first["zenodo_effect"], "NOT_EXECUTED")
        self.assertEqual(first["ietf_effect"], "NOT_EXECUTED")

        verified = roundtrip.verify(self.root, self.request_path)
        self.assertEqual(verified["state"], "VERIFIED_CONTINUE")
        second = self.capture()
        self.assertEqual(second["write_status"], "NOOP_ALREADY_MATERIALIZED")
        self.assertEqual(second["receipt_sha256"], verified["receipt_sha256"])

    def test_metadata_only_never_persists_raw_messages(self) -> None:
        self.capture()
        persisted = b"".join(
            path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file() and path != self.request_path
        )
        self.assertNotIn(self.user_raw.encode("utf-8"), persisted)
        self.assertNotIn(self.assistant_raw.encode("utf-8"), persisted)
        self.assertIn(digest(self.user_raw).encode("ascii"), persisted)
        self.assertIn(digest(self.assistant_raw).encode("ascii"), persisted)

    def test_tamper_breaks_verification(self) -> None:
        self.capture()
        event_path = (
            self.root
            / "state"
            / "interaction_archive"
            / "io-roundtrip"
            / "events"
            / "event-user-20260807-162149-v1.json"
        )
        value = json.loads(event_path.read_text(encoding="utf-8"))
        value["semantic_projection"]["assertions"].append("tampered")
        event_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(roundtrip.archive.ArchiveError):
            roundtrip.verify(self.root, self.request_path)

    def test_full_transcript_mode_is_fail_closed(self) -> None:
        self.request["retention_mode"] = "FULL_TRANSCRIPT"
        self.write_request()
        with self.assertRaises(roundtrip.RoundTripError):
            self.capture()

    def test_raw_content_field_is_rejected(self) -> None:
        self.request["events"][0]["semantic_projection"]["raw_content"] = "secret"
        self.write_request()
        with self.assertRaises(roundtrip.RoundTripError):
            self.capture()

    def test_partial_final_outputs_recover_write_once(self) -> None:
        first = self.capture()
        receipt = self.root / first["receipt_path"]
        work_unit = self.root / first["work_unit_path"]
        disposition = self.root / first["disposition_path"]
        receipt.unlink()
        work_unit.unlink()
        result = self.capture()
        self.assertEqual(result["state"], "VERIFIED_CONTINUE")
        self.assertTrue(receipt.is_file())
        self.assertTrue(work_unit.is_file())
        self.assertTrue(disposition.is_file())


if __name__ == "__main__":
    unittest.main()

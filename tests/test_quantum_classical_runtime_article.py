#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_zenodo_publish as zenodo_publish

DIR = ROOT / "docs/publications/2026-07-28-verantwortungsgebundener-erkenntnisprozess-quantenklassische-wirkungsmaschine"
ARTICLE = DIR / "ARTICLE_DE.md"
MANIFEST = DIR / "ARTICLE_MANIFEST.json"
CLAIMS = DIR / "CLAIM_MATRIX.json"
PLAN = DIR / "KERNEL_PROOF_PLAN.json"
AUTHORIZATION = DIR / "OWNER_EFFECT_AUTHORIZATION.json"
KERNEL_RECEIPT = DIR / "KERNEL_RECEIPT.json"
LEAN = ROOT / "formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck/QuantumClassicalRuntime.lean"
ENTRY = ROOT / "formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck.lean"
REQUEST = ROOT / "release/quantum-classical-runtime-article-2026-07-28/publish-request.json"
EVIDENCE = ROOT / "release/quantum-classical-runtime-article-2026-07-28/zenodo-publication.json"
SCOPE = "qikvrt-quantum-classical-runtime-article-v1"

EXPECTED = {
    ARTICLE: ("1fade850374cba0dc714dc8ecc842f15d80a62e9cfb7f3cedfd9e736ab1352e1", "783d8eb88103ecd4fbf60d293dd64bf96d49cad5"),
    MANIFEST: ("fa9c5bca235b6326c43fbe02b1d0235923658dcf8616f3dc8db294e987614797", "6e942f06af3d251e911ef8662855a1c9526792c4"),
    CLAIMS: ("efdf603f0018620924cd55aab2470117ad7ded32bf5cd9a679246a122bde5527", "31e1aad06661680b46a89821c272649533491a07"),
    PLAN: ("c91daf74fc2fef41ad487599ae88d6f7de651520d2e1648e1c787638b552eb7c", "9e6f71e09dd461797994e8e2a9bd9ca93537a8ef"),
    AUTHORIZATION: ("ef73396776137395422c53e55b0d320063ce454082fa90f24ea0ece0913d2923", "768e4f645fc4cd69ed1c4058b7fc51dbd08bd1a5"),
    KERNEL_RECEIPT: ("14245a79966e4667ddd931c59510370032ebffefe4b2421401404dd5c22a6c1a", "adfda684598313af8070077aa6bbe04ca7a11977"),
    LEAN: ("9a02bb3ba762063646aa22af4c05467b52ac49ef05773bfc067f3a3c2be22465", "1d0f806a62e1729893b4688e2322f7403a1cb931"),
}

THEOREMS = (
    "QIKVRT.QuantumClassicalRuntime.V1.responsibleRelease_eq_true_iff",
    "QIKVRT.QuantumClassicalRuntime.V1.responsibleRelease_requires_uncertainty",
    "QIKVRT.QuantumClassicalRuntime.V1.responsibleRelease_requires_gate",
    "QIKVRT.QuantumClassicalRuntime.V1.responsibleRelease_requires_effect_observation",
    "QIKVRT.QuantumClassicalRuntime.V1.responsibility_does_not_force_deterministic_measurement",
    "QIKVRT.QuantumClassicalRuntime.V1.measurement_alone_does_not_authorize_release",
    "QIKVRT.QuantumClassicalRuntime.V1.backend_replacement_preserves_shape",
    "QIKVRT.QuantumClassicalRuntime.V1.simulator_and_qpu_share_complete_shape",
    "QIKVRT.QuantumClassicalRuntime.V1.selectState_effect_ack_iff",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class QuantumClassicalRuntimeArticleTests(unittest.TestCase):
    def test_exact_source_identities(self) -> None:
        for path, (digest, blob) in EXPECTED.items():
            self.assertEqual(sha256(path), digest)
            self.assertEqual(git_blob(path), blob)

    def test_article_contains_core_claim_and_boundaries(self) -> None:
        text = ARTICLE.read_text(encoding="utf-8")
        required = (
            "Nicht weniger Prüfung erzeugte die Geschwindigkeit.",
            "Der Übergang von der Methode zur Maschine",
            "Die Quantenberechnung bleibt probabilistisch. Der Umgang mit ihrer Bedeutung wird deterministisch geregelt.",
            "Verified Effect Transaction",
            "QIK-VRT virtualisiert nicht das Qubit.",
            SCOPE,
            "Eine reale QPU-End-to-End-Integration wird in diesem Artikel nicht als bereits ausgeführt behauptet.",
        )
        for phrase in required:
            self.assertIn(phrase, text)
        for prohibited in (
            "QIK-VRT ersetzt den Quantenprozessor",
            "eine reale QPU-End-to-End-Ausführung ist abgeschlossen",
            "alle Quantenberechnungen sind deterministisch",
            "jede andere Person oder Institution der Welt ist langsamer",
        ):
            self.assertNotIn(prohibited, text)

    def test_manifest_and_claim_matrix_are_complete_and_fail_closed(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        matrix = json.loads(CLAIMS.read_text(encoding="utf-8"))
        self.assertEqual(manifest["scope_id"], SCOPE)
        self.assertEqual(manifest["claim_inventory"]["claims_total"], 26)
        self.assertEqual(manifest["claim_inventory"]["formal_theorems"], 9)
        self.assertEqual(manifest["claim_inventory"]["implementation_open"], ["QRT-018"])
        self.assertEqual(manifest["proof_state"]["state"], "KERNEL_VERIFIED")
        self.assertTrue(manifest["proof_state"]["kernel_receipt_present"])
        self.assertFalse(manifest["completion_claims"]["pass"])
        self.assertFalse(manifest["completion_claims"]["final_pass"])
        self.assertFalse(manifest["completion_claims"]["effect_ack_done"])
        self.assertEqual(matrix["claim_count"], 26)
        self.assertEqual(len(matrix["claims"]), 26)
        self.assertEqual(len({c["claim_id"] for c in matrix["claims"]}), 26)
        formal = [c for c in matrix["claims"] if c["classification"] == "FORMAL_KERNEL_PROVED"]
        self.assertEqual(len(formal), 8)
        self.assertEqual({ref for c in formal for ref in c["proof_refs"]}, set(THEOREMS))
        open_claim = next(c for c in matrix["claims"] if c["claim_id"] == "QRT-018")
        self.assertEqual((open_claim["classification"], open_claim["status"]), ("IMPLEMENTATION_OPEN", "OPEN"))

    def test_kernel_plan_and_source_are_exact_and_escape_free(self) -> None:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(plan["scope_id"], SCOPE)
        self.assertEqual(plan["source"]["sha256"], EXPECTED[LEAN][0])
        self.assertEqual(plan["source"]["git_blob_sha1"], EXPECTED[LEAN][1])
        self.assertEqual(plan["receipt"]["sha256"], EXPECTED[KERNEL_RECEIPT][0])
        self.assertEqual(plan["receipt"]["git_blob_sha1"], EXPECTED[KERNEL_RECEIPT][1])
        self.assertEqual(plan["theorems"], list(THEOREMS))
        self.assertEqual(plan["state"], "KERNEL_VERIFIED")
        source = LEAN.read_text(encoding="utf-8")
        self.assertIn("import QIKVRTEffectAck.QuantumClassicalRuntime", ENTRY.read_text(encoding="utf-8"))
        for theorem in THEOREMS:
            self.assertIn("theorem " + theorem.rsplit(".", 1)[-1], source)
        for prohibited in (r"\bsorry\b", r"\badmit\b", r"\baxiom\b", r"unsafe"):
            self.assertIsNone(re.search(prohibited, source))

    def test_owner_authorization_is_concrete_and_fail_closed(self) -> None:
        value = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
        self.assertEqual(value["principal"], {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"})
        self.assertIn("PUBLISH_ARTICLE_AND_MACHINE_EVIDENCE_TO_PRODUCTION_ZENODO", value["authorized_effects"])
        self.assertTrue(value["fail_closed"])
        self.assertEqual(value["claims"], {"effect_ack_done": False, "final_pass": False, "pass": False})

    def test_kernel_receipt_is_strict(self) -> None:
        value = json.loads(KERNEL_RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], "qikvrt_quantum_classical_runtime_kernel_receipt_v1")
        self.assertEqual(value["scope_id"], SCOPE)
        self.assertEqual(value["state"], "KERNEL_VERIFIED")
        self.assertEqual(value["source"]["sha256"], EXPECTED[LEAN][0])
        self.assertEqual(value["theorems"], list(THEOREMS))
        self.assertTrue(value["workflow"]["exact_head_bound"])
        self.assertEqual(value["workflow"]["conclusion"], "success")
        self.assertEqual(value["verified_candidate"]["head"], "2d5fdead6415790a617f3c855385ad623ba3c367")
        self.assertEqual(value["promoted_authority_commit"], "f601896ecd48907de80a099210bc0c51023b846c")
        self.assertFalse(value["completion_claims"]["final_pass"])

    def test_optional_zenodo_request_is_git_blob_bound(self) -> None:
        if not REQUEST.exists():
            return
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"}):
            materialized = zenodo_publish.load_manifest(REQUEST, ROOT)
        paths = [ARTICLE, MANIFEST, CLAIMS, PLAN, KERNEL_RECEIPT, LEAN, AUTHORIZATION]
        self.assertEqual([x["path"] for x in materialized["files"]], [x.relative_to(ROOT).as_posix() for x in paths])
        self.assertEqual([x["git_blob_sha"] for x in materialized["files"]], [git_blob(x) for x in paths])
        self.assertEqual(materialized["metadata"]["publication_type"], "article")

    def test_optional_zenodo_evidence_requires_public_byte_identity(self) -> None:
        if not EVIDENCE.exists():
            return
        value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], "qikvrt_zenodo_publication_evidence_v1")
        self.assertEqual(value["state"], "published")
        self.assertRegex(value["doi"], r"^10\.5281/zenodo\.[1-9][0-9]*$")
        self.assertRegex(value["conceptdoi"], r"^10\.5281/zenodo\.[1-9][0-9]*$")
        for item in value["files"]:
            source = ROOT / item["path"]
            self.assertEqual(item["git_blob_sha"], git_blob(source))
            self.assertEqual(item["sha256"], sha256(source))
            self.assertEqual(item["size"], source.stat().st_size)
        recovery = value.get("recovery", {})
        self.assertTrue(recovery.get("public_record_reverified", False))
        self.assertTrue(recovery.get("all_public_files_byte_exact", False))
        self.assertFalse(recovery.get("duplicate_publication_performed", True))


if __name__ == "__main__":
    unittest.main(verbosity=2)

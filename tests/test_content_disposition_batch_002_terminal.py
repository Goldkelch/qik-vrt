#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/"tools/qikvrt_content_disposition_batch_002_terminal.py"
BASE=ROOT/"release/zenodo-corpus-proof-2026-07-28/canonical-union"
OUT=BASE/"content-disposition-batch-002/terminal-disposition"
spec=importlib.util.spec_from_file_location("b2",P)
m=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


def load(path:pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=load(OUT/"CONTENT_DISPOSITION_BATCH_002_RECEIPT.json")
        cls.queue=load(BASE/"CONTENT_CLAIM_DISPOSITION_QUEUE.json")
        cls.index=load(BASE/"CONTENT_CLAIM_DISPOSITION_INDEX.json")
        cls.union_receipt=load(BASE/"CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json")
        cls.progress=load(ROOT/"AI_PROGRESS.json")

    def test_open_boundary(self):
        self.assertEqual(m.classify("Diese Frage bleibt offen."),"OPEN")

    def test_normative(self):
        self.assertEqual(m.classify("Jede Veröffentlichung muss geprüft werden."),"NORMATIVE")

    def test_interpretative(self):
        self.assertEqual(m.classify("Dies ist eine ontologische Interpretation."),"INTERPRETATIVE")

    def test_empirical(self):
        self.assertEqual(m.classify("Der SHA-256-Redownload wurde verifiziert."),"EMPIRICALLY_EVIDENCED")

    def test_plain_source(self):
        self.assertEqual(m.classify("Das Dokument enthält sieben Dateien."),"SOURCE_BOUND")

    def test_formal_requires_binding(self):
        self.assertNotEqual(m.classify("Satz","KERNEL_PROVED","",[]),"FORMAL_PROVED")
        self.assertEqual(m.classify("Satz","KERNEL_PROVED","",["Theorem.x"]),"FORMAL_PROVED")

    def test_overclaim_detector(self):
        self.assertTrue(m.OVERCLAIM.search("Damit ist alles vollständig bewiesen."))

    def test_false_completion_constants(self):
        text=P.read_text(encoding="utf-8")
        self.assertIn('"pass":False',text)
        self.assertIn('"final_pass":False',text)
        self.assertIn('"effect_ack_done":False',text)

    def test_terminal_receipt_is_truth_bounded(self):
        r=self.receipt
        self.assertEqual(r["batch_id"],m.BATCH_ID)
        self.assertEqual(r["state"],"TERMINALLY_DISPOSITIONED")
        self.assertEqual(r["subject_count"],6)
        self.assertEqual(r["claim_count"],1489)
        self.assertEqual(r["content_change_required_count"],1)
        self.assertEqual(r["observed_at"],m.OBSERVED_AT)
        self.assertEqual([x["subject_id"] for x in r["subjects"]],m.SUBJECT_IDS)
        for key in ("all_content_claims_dispositioned","proof_corpus_published_on_zenodo","pass","final_pass","effect_ack_done"):
            self.assertIs(r["completion_claims"][key],False,key)
        m.validate_terminal_receipt(r,self.index)

    def test_terminal_receipt_validation_fails_closed(self):
        bad=copy.deepcopy(self.receipt)
        bad["validation"]["all_public_files_byte_reverified"]=False
        with self.assertRaises(m.E):
            m.validate_terminal_receipt(bad,self.index)
        bad=copy.deepcopy(self.receipt)
        bad["subjects"][0]["claim_matrix_sha256"]="0"*64
        with self.assertRaises(m.E):
            m.validate_terminal_receipt(bad,self.index)
        bad=copy.deepcopy(self.receipt)
        correction=next(
            row for row in bad["subjects"] if row["content_change_required"]
        )
        correction["content_change_required"]=False
        correction["state"]="DISPOSITIONED_NO_CONTENT_CHANGE"
        bad["content_change_required_count"]=0
        with self.assertRaises(m.E):
            m.validate_terminal_receipt(bad,self.index)

    def test_queue_index_receipts_are_one_projection(self):
        expected_next=self.receipt["next_deterministic_effect"]
        self.assertEqual(expected_next,"CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002")
        self.assertEqual(self.queue["next_deterministic_effect"],expected_next)
        self.assertEqual(self.index["next_deterministic_effect"],expected_next)
        self.assertEqual(self.union_receipt["next_deterministic_effect"],expected_next)
        self.assertEqual(self.queue["state"],"BATCH_002_CORRECTION_REQUIRED_BATCH_003_READY")
        self.assertEqual(self.index["state"],"BATCH_002_TERMINALLY_DISPOSITIONED_CORRECTION_REQUIRED_BATCH_003_READY")
        self.assertEqual(self.queue["observed_at"],m.PROJECTION_UPDATED_AT)
        self.assertEqual(self.index["observed_at"],m.PROJECTION_UPDATED_AT)
        self.assertEqual(self.union_receipt["observed_at"],m.UNION_OBSERVED_AT)
        self.assertEqual(self.union_receipt["status_updated_at"],m.PROJECTION_UPDATED_AT)
        self.assertEqual(
            self.union_receipt["state"],
            "CONTENT_DISPOSITION_BATCH_002_TERMINALLY_DISPOSITIONED_CORRECTION_REQUIRED",
        )
        self.assertNotIn("EXECUTE_CONTENT_DISPOSITION_BATCH_002",json.dumps({
            "queue":self.queue["next_deterministic_effect"],
            "index":self.index["next_deterministic_effect"],
            "union":self.union_receipt["next_deterministic_effect"],
        }))

    def test_batch_counts_and_queue_partition_are_exact(self):
        complete=[x for x in self.index["claim_subjects"] if x["claim_disposition_complete"]]
        pending=[x for x in self.index["claim_subjects"] if not x["claim_disposition_complete"]]
        self.assertEqual((len(complete),len(pending)),(12,7))
        self.assertEqual(sum(x["claim_count"] for x in complete),1747)
        self.assertEqual(self.queue["active_batch"]["batch_id"],"CONTENT-DISPOSITION-BATCH-003")
        self.assertEqual(self.queue["active_batch"]["state"],"READY")
        self.assertEqual(self.queue["active_batch"]["subject_count"],6)
        self.assertEqual(self.queue["remaining_subject_count"],1)
        self.assertEqual(self.queue["active_batch"]["subject_count"]+self.queue["remaining_subject_count"],len(pending))
        batch2=[x for x in self.queue["completed_batches"] if x["batch_id"]==m.BATCH_ID]
        self.assertEqual(len(batch2),1)
        self.assertEqual(batch2[0]["claim_count"],self.receipt["claim_count"])
        self.assertEqual(batch2[0]["content_change_required_count"],1)

    def test_index_batch_summary_matches_terminal_receipt(self):
        batch=self.index["batch_002"]
        self.assertEqual(batch["state"],"TERMINALLY_DISPOSITIONED")
        self.assertEqual(batch["subject_count"],self.receipt["subject_count"])
        self.assertEqual(batch["claim_count"],self.receipt["claim_count"])
        self.assertEqual(batch["content_change_required_count"],self.receipt["content_change_required_count"])
        self.assertEqual(batch["subjects"],self.receipt["subjects"])
        self.assertIs(self.index["completion_claims"]["second_batch_executed"],True)
        self.assertIs(self.index["completion_claims"]["second_batch_terminal_disposition_complete"],True)
        self.assertIs(self.index["completion_claims"]["all_content_claims_dispositioned"],False)

    def test_complete_subjects_and_record_rows_agree(self):
        records={int(x["record_id"]):x for x in self.index["records"]}
        for subject in self.index["claim_subjects"]:
            if not subject["claim_disposition_complete"]:
                continue
            for rid in subject["record_ids"]:
                record=records[int(rid)]
                for key in ("claim_disposition_complete","content_change_required","disposition_state","required_action"):
                    self.assertEqual(record[key],subject[key],f"{rid}:{key}")

    def test_union_receipt_digest_and_false_completion_are_current(self):
        payload={key:self.union_receipt[key] for key in m.UNION_RECEIPT_PAYLOAD_KEYS}
        self.assertEqual(self.union_receipt["receipt_payload_sha256"],m.sha(m.canon(payload)))
        status_payload={key:self.union_receipt[key] for key in m.UNION_STATUS_KEYS}
        self.assertEqual(self.union_receipt["status_projection_sha256"],m.sha(m.canon(status_payload)))
        changed=copy.deepcopy(status_payload)
        changed["state"]="MUTATED"
        self.assertNotEqual(
            self.union_receipt["status_projection_sha256"],
            m.sha(m.canon(changed)),
        )
        completion=self.union_receipt["completion_claims"]
        self.assertIs(completion["content_disposition_batch_002_terminal_disposition_complete"],True)
        self.assertIs(completion["content_disposition_batch_002_correction_required"],True)
        for key in ("all_content_claims_dispositioned","content_correction_review_complete","all_required_corrected_candidates_returned_to_owner","proof_corpus_published_on_zenodo","mirror_synchronized","pass","final_pass","effect_ack_done"):
            self.assertIs(completion[key],False,key)

    def test_multiscope_progress_never_inflates_pass(self):
        p=self.progress
        required={"schema","operation_id","repository","ref_name","source_sha","state","percent","current_action","completed_steps","pending_steps","blockers","next_action","updated_at"}
        self.assertTrue(required.issubset(p))
        self.assertEqual(p["schema"],"qikvrt-ai-progress/3.1")
        self.assertEqual(p["state"],"IDLE")
        self.assertEqual(p["effect_state"],"EFFECT_ACK_CONTINUE")
        self.assertEqual(p["next_action"],self.queue["next_deterministic_effect"])
        self.assertTrue(all(p["claims"][key] is False for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE")))
        self.assertEqual(set(p["scopes"]),{"qikvrt-global-claim-scope-v1",self.index["union_id"]})
        global_scope=p["scopes"]["qikvrt-global-claim-scope-v1"]
        corpus=p["scopes"][self.index["union_id"]]
        self.assertTrue(all(global_scope["claims"][key] is True for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE")))
        self.assertTrue(all(corpus["claims"][key] is False for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE")))
        self.assertEqual(corpus["counts"],{"subjects":19,"dispositioned_subjects":12,"open_subjects":7,"dispositioned_claims":1747})
        effects=p["repository_effects"]
        self.assertNotIn("authority_pr",effects)
        self.assertTrue(all(value=="NOT_EVALUATED" for key,value in effects.items() if key!="scope"))
        self.assertEqual(p["source_evidence"],m.build_source_evidence())
        self.assertEqual(
            p["source_evidence"]["verification_mode"],
            "portable-git-object-closure",
        )
        self.assertEqual(p["source_evidence"]["source_repository"],m.AUTH_REPO)
        self.assertEqual(p["source_evidence"]["root_tree"],m.SOURCE_TREE)
        capsule=m.source_capsule()
        self.assertEqual(len(capsule.objects),13)
        self.assertEqual(len(capsule.files),6)
        self.assertEqual(sum(len(value) for value in capsule.files.values()),62594)
        self.assertEqual(
            p["source_evidence"]["capsule"],
            {
                "path":m.SOURCE_CAPSULE_RELATIVE,
                "bytes":capsule.capsule_bytes,
                "sha256":capsule.capsule_sha256,
                "git_blob_sha1":capsule.capsule_git_blob_sha1,
            },
        )
        self.assertEqual(
            set(p["source_evidence"]["blobs"]),
            set(m.source_evidence_paths()),
        )
        self.assertIn("pass_evidence",global_scope)
        m.validate_ai_progress(p)

    def test_progress_contract_rejects_scope_and_release_inflation(self):
        bad=copy.deepcopy(self.progress)
        bad["claims"]["PASS"]=True
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)
        bad=copy.deepcopy(self.progress)
        bad["incomplete_scope_count"]=0
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)
        bad=copy.deepcopy(self.progress)
        del bad["scopes"]["qikvrt-global-claim-scope-v1"]["pass_evidence"]
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)
        bad=copy.deepcopy(self.progress)
        bad["source_evidence"]["blobs"][next(iter(bad["source_evidence"]["blobs"]))]="0"*40
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)
        bad=copy.deepcopy(self.progress)
        bad["source_evidence"]["capsule"]["sha256"]="0"*64
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)
        bad=copy.deepcopy(self.progress)
        bad["source_evidence"]["root_tree"]="0"*40
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)
        bad=copy.deepcopy(self.progress)
        bad["scopes"]["qikvrt-global-claim-scope-v1"]["pass_evidence"]["checks"]["receipt_gate_matrix"]["authority"]["global_completion"]="failure"
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)
        bad=copy.deepcopy(self.progress)
        del bad["scopes"][self.index["union_id"]]
        bad["incomplete_scope_count"]=0
        bad["percent_scope"]="qikvrt-global-claim-scope-v1"
        bad["percent"]=100
        bad["state"]="PASS"
        bad["effect_state"]="EFFECT_ACK_DONE"
        bad["claims"].update({
            "PASS":True,
            "FINAL_PASS":True,
            "EFFECT_ACK_DONE":True,
        })
        m.validate_ai_progress(bad)
        bad["effect_state"]="EFFECT_ACK_CONTINUE"
        with self.assertRaises(m.E):
            m.validate_ai_progress(bad)

    def test_global_pass_builder_rejects_failed_receipt_gate(self):
        receipt=load(ROOT/"GLOBAL_COMPLETION_RECEIPT.json")
        receipt["exact_head_gates"]["authority"]["global_completion"]="failure"
        with self.assertRaises(m.E):
            m.build_global_pass_evidence(receipt)

    def test_projection_is_idempotent_and_refuses_later_evidence(self):
        args=(
            copy.deepcopy(self.queue),
            copy.deepcopy(self.index),
            copy.deepcopy(self.union_receipt),
            copy.deepcopy(self.receipt["subjects"]),
            self.receipt["claim_count"],
            self.receipt["content_change_required_count"],
        )
        first=m.project_status(*args)
        second=m.project_status(
            copy.deepcopy(first[0]),
            copy.deepcopy(first[1]),
            copy.deepcopy(first[2]),
            copy.deepcopy(self.receipt["subjects"]),
            self.receipt["claim_count"],
            self.receipt["content_change_required_count"],
        )
        self.assertEqual(first,second)
        self.assertEqual(first,(self.queue,self.index,self.union_receipt))
        future=copy.deepcopy(self.union_receipt)
        future["completion_claims"]["mirror_synchronized"]=True
        with self.assertRaises(m.E):
            m.project_status(
                copy.deepcopy(self.queue),
                copy.deepcopy(self.index),
                future,
                copy.deepcopy(self.receipt["subjects"]),
                self.receipt["claim_count"],
                self.receipt["content_change_required_count"],
            )
        future_index=copy.deepcopy(self.index)
        future_index["batch_002"]["owner_return_receipt"]={
            "state":"RETURNED",
        }
        with self.assertRaises(m.E):
            m.project_status(
                copy.deepcopy(self.queue),
                future_index,
                copy.deepcopy(self.union_receipt),
                copy.deepcopy(self.receipt["subjects"]),
                self.receipt["claim_count"],
                self.receipt["content_change_required_count"],
            )
        forged_union=copy.deepcopy(self.union_receipt)
        forged_union["source_binding_sha256"]="0"*64
        with self.assertRaises(m.E):
            m.project_status(
                copy.deepcopy(self.queue),
                copy.deepcopy(self.index),
                forged_union,
                copy.deepcopy(self.receipt["subjects"]),
                self.receipt["claim_count"],
                self.receipt["content_change_required_count"],
            )
        forged_index=copy.deepcopy(self.index)
        forged_index["union_id"]="forged-union"
        with self.assertRaises(m.E):
            m.project_status(
                copy.deepcopy(self.queue),
                forged_index,
                copy.deepcopy(self.union_receipt),
                copy.deepcopy(self.receipt["subjects"]),
                self.receipt["claim_count"],
                self.receipt["content_change_required_count"],
            )

    def test_progress_schema_and_policy_required_fields_agree(self):
        schema=load(ROOT/"schemas/human_machine_progress.schema.json")
        durable=schema["$defs"]["durableSnapshotV3"]
        policy=load(ROOT/"policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
        self.assertTrue(set(policy["mandatory_fields"]).issubset(durable["required"]))
        self.assertEqual(durable["properties"]["schema"]["const"],self.progress["schema"])
        self.assertIn(self.progress["state"],durable["properties"]["state"]["enum"])
        self.assertEqual(policy["tracked_snapshot"]["ownerless_state"],"IDLE")
        self.assertEqual(policy["schema"],"qikvrt-human-machine-progress-protocol/1.3")
        self.assertTrue(set(policy["tracked_snapshot"]["required_fields"]).issubset(durable["required"]))
        self.assertIn("TIMEOUT",durable["properties"]["state"]["enum"])
        self.assertTrue(durable["allOf"])
        self.assertTrue(schema["$defs"]["scopeStatus"]["allOf"])

    def test_human_projection_is_byte_current(self):
        status=(ROOT/"AI_STATUS.md").read_text(encoding="utf-8")
        self.assertEqual(status,m.render_ai_status(self.progress))
        self.assertNotIn("87%",status)
        self.assertNotIn("agent/effect-ack-lean-v1",status)
        self.assertNotIn("PR #199: open",status)
        self.assertIn("[████████████░░░░░░░] 63%",status)
        self.assertIn("- ✓ Batch 002 terminally dispositioned",status)
        self.assertIn("- □ Required corrected Batch-002 candidate",status)
        self.assertIn("qikvrt-global-claim-scope-v1",status)
        self.assertIn(self.index["union_id"],status)

    def test_status_projection_check_mode(self):
        subprocess.run(
            [sys.executable,"-B",str(P),"--check-status-projection"],
            cwd=ROOT,
            check=True,
        )
        with tempfile.TemporaryDirectory() as empty_objects:
            environment=dict(os.environ)
            environment.update({
                "GIT_OBJECT_DIRECTORY":empty_objects,
                "GIT_ALTERNATE_OBJECT_DIRECTORIES":"",
                "GIT_NO_LAZY_FETCH":"1",
                "GIT_NO_REPLACE_OBJECTS":"1",
                "GIT_TERMINAL_PROMPT":"0",
            })
            completed=subprocess.run(
                [sys.executable,"-B",str(P),"--check-status-projection"],
                cwd=ROOT,
                env=environment,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        self.assertEqual(completed.returncode,0,completed.stderr)
        self.assertIn('"state": "PASS"',completed.stdout)


if __name__=="__main__":
    unittest.main(verbosity=2)

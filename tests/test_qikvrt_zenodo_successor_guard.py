# SPDX-License-Identifier: Apache-2.0
import json, pathlib, tempfile, unittest
from tools import qikvrt_zenodo_successor_guard as guard
class ZenodoSuccessorGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=pathlib.Path(self.tmp.name); (self.root/"policy").mkdir(); (self.root/"release/x").mkdir(parents=True); (self.root/"docs").mkdir()
        (self.root/"a.txt").write_text("A\n",encoding="utf-8"); (self.root/"docs/b.txt").write_text("B\n",encoding="utf-8")
        self.registry={"schema":"qikvrt_zenodo_successor_targets_v1","targets":[{"id":"x","publication_id":"pub-x","authority_repository":"o/r","source_paths":["a.txt","docs/b.txt"],"candidate_path":"release/x/AUTO_SUCCESSOR_CANDIDATE.json","publish_request_path":"release/x/publish-request.json","owner_authorization_path":"release/x/OWNER.json","publication_receipt_path":"release/x/zenodo-publication.json","enforce_public_effect_on_main":True}]}
        (self.root/"policy/QIKVRT_ZENODO_SUCCESSOR_TARGETS_V1.json").write_text(json.dumps(self.registry),encoding="utf-8")
    def tearDown(self): self.tmp.cleanup()
    def test_materialize_detects_successor_drift(self):
        guard.materialize(self.root,"x"); self.assertTrue(guard.evaluate(self.root,"x")["candidate"]["current"]); (self.root/"a.txt").write_text("A2\n",encoding="utf-8"); self.assertEqual(guard.evaluate(self.root,"x")["candidate"]["state"],"STALE")
    def test_public_effect_requires_exact_current_upload_and_receipt(self):
        guard.materialize(self.root,"x"); current=guard.source_set(self.root,guard.target(self.root,"x")); files=[{"path":x["path"],"git_blob_sha":x["git_blob_sha1"]} for x in current]
        (self.root/"release/x/publish-request.json").write_text(json.dumps({"files":files}),encoding="utf-8"); (self.root/"release/x/zenodo-publication.json").write_text(json.dumps({"state":"published","doi":"10.5281/zenodo.123","files":files}),encoding="utf-8")
        self.assertTrue(guard.evaluate(self.root,"x")["PUBLICATION_EFFECT_ACK_DONE"]); (self.root/"docs/b.txt").write_text("changed\n",encoding="utf-8"); self.assertFalse(guard.evaluate(self.root,"x")["PUBLICATION_EFFECT_ACK_DONE"])
    def test_path_escape_is_rejected(self):
        self.registry["targets"][0]["source_paths"]=["../escape"]; (self.root/"policy/QIKVRT_ZENODO_SUCCESSOR_TARGETS_V1.json").write_text(json.dumps(self.registry),encoding="utf-8")
        with self.assertRaises(guard.GuardError): guard.target(self.root,"x")
if __name__=="__main__": unittest.main()

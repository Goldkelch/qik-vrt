#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations
import importlib.util,json,pathlib,re,tempfile,unittest,unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[1]; MODULE=ROOT/'tools/qikvrt_mesh_html.py'; SPEC=importlib.util.spec_from_file_location('mesh',MODULE); assert SPEC and SPEC.loader; mesh=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mesh)
WORKFLOW=ROOT/'.github/workflows/qikvrt_feature_request.yml'; SCHEMA=ROOT/'policy/QIKVRT_FEATURE_REQUEST_V1.schema.json'; HEAD='1'*40
class Tests(unittest.TestCase):
    def generated(self):
        t=tempfile.TemporaryDirectory(); p=pathlib.Path(t.name)/mesh.ARTIFACT; mesh.write_artifact(p); self.addCleanup(t.cleanup); return p
    def test_deterministic(self):
        a=self.generated().read_bytes(); b=self.generated().read_bytes(); self.assertEqual(a,b); self.assertLess(len(a),10*1024*1024)
    def test_offline_single_file_svg(self):
        text=self.generated().read_text(encoding='utf-8'); self.assertTrue(unicodedata.is_normalized('NFC',text)); self.assertIn('<svg',text); self.assertIn('<style>',text); self.assertIn('<script>',text)
        for x in (r'https?://',r'<script[^>]+src=',r'<link[^>]+href=',r'\bfetch\s*\(',r'XMLHttpRequest',r'WebSocket\s*\(',r'EventSource\s*\('): self.assertIsNone(re.search(x,text,re.I),x)
    def test_capabilities(self):
        text=self.generated().read_text(encoding='utf-8')
        for v in mesh.VIEWS+mesh.TIME_MODES+mesh.ANIMATIONS+['fpsHistory','historyLine','profileFrames','warningList','function migrate','function downgrade','function stable',"normalize('NFC')",'function selfTests','property-based samples=128','localStorage','PREDECESSOR_EVIDENCE_TRANSFER = FALSE','REFERENCE_LINK ≠ EVIDENCE_TRANSFER ≠ EFFECT_ACK']: self.assertIn(v,text)
    def test_repository_dispatch(self):
        q=json.loads(json.dumps(mesh.CANONICAL_REQUEST)); q['subject_sha']=HEAD; self.assertEqual(mesh.request_from_event({'action':mesh.EVENT_TYPE,'client_payload':q},'repository_dispatch',HEAD)['subject_sha'],HEAD)
    def test_subject_drift_fails(self):
        q=json.loads(json.dumps(mesh.CANONICAL_REQUEST)); q['subject_sha']='2'*40
        with self.assertRaises(ValueError): mesh.request_from_event({'action':mesh.EVENT_TYPE,'client_payload':q},'repository_dispatch',HEAD)
    def test_unknown_field_fails(self):
        q=json.loads(json.dumps(mesh.CANONICAL_REQUEST)); q['request']['network']=True
        with self.assertRaises(ValueError): mesh.validate_feature_request(q)
    def test_workflow_dispatch_default(self): self.assertEqual(mesh.request_from_event({'inputs':{'task':mesh.TASK,'request_json_b64':'','subject_sha':''}},'workflow_dispatch',HEAD),mesh.CANONICAL_REQUEST)
    def test_workflow_contract(self):
        text=WORKFLOW.read_text();
        for x in ('types: [qikvrt_feature_request]','options: [build_qik_vrt_mesh_html]','pull_request:','contents: read','persist-credentials: false','validate-event','generate --output dist/QIK_VRT_MESH.html','tests.test_qikvrt_mesh_html','QIK_VRT_MESH.receipt.json'): self.assertIn(x,text)
        self.assertNotIn('contents: write',text); self.assertNotIn('git push',text)
    def test_schema(self):
        s=json.loads(SCHEMA.read_text()); self.assertEqual(s['properties']['event_type']['const'],mesh.EVENT_TYPE); p=s['properties']['client_payload']; self.assertFalse(p['additionalProperties']); self.assertEqual(p['properties']['artifact']['const'],mesh.ARTIFACT)
    def test_receipt_boundary(self):
        p=self.generated(); r=mesh.build_receipt(mesh.CANONICAL_REQUEST,HEAD,'3'*40,p); self.assertFalse(r['repository_mutation']); self.assertFalse(r['effect_ack_done']); self.assertFalse(r['transport_ack_is_effect_ack']); self.assertFalse(r['predecessor_evidence_transfer']); self.assertEqual(r['effect_scope'],'deterministic-build-test-artifact-only')
if __name__=='__main__': unittest.main()

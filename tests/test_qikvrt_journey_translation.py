# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Negative transport/scope tests, not semantic translation certification."""
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('journey_translation',ROOT/'tools/qikvrt_journey_translation.py')
assert spec and spec.loader
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)

class TranslationBoundaries(unittest.TestCase):
    def test_source_binding(self):
        raw,values=worker.source()
        self.assertEqual(len(raw),39745)
        self.assertEqual(len(values),540)
        self.assertEqual(worker.blob(raw),'45c1f23cdf842ef5d92bfbef1d17da536b47f069')

    def test_language_partitions_are_explicit_disjoint_and_exhaustive(self):
        registry=json.loads((ROOT/'docs/reise/WIKIPEDIA_47_LANGUAGE_SOURCE.json').read_text())
        groups=[set(worker.RECOVER),set(worker.TARGETS),{'de','en'},{'sh','simple','wuu'}]
        self.assertEqual([len(x) for x in groups],[8,34,2,3])
        self.assertEqual(set.union(*groups),{row[0] for row in registry['languages']})
        for i,a in enumerate(groups):
            for b in groups[i+1:]:self.assertFalse(a & b)

    def test_recovered_identifiers_are_literal_valid_blobs(self):
        for value in worker.RECOVER.values():self.assertRegex(value,r'^[0-9a-f]{40}$')

    def test_unknown_target_is_not_silently_remapped(self):
        for language in ('wuu','simple','sh','en','../de'):
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_LANGUAGE'):
                worker.translate(language,Path('/absent'),Path('/absent'))

    def test_authenticated_endpoint_is_repository_scoped(self):
        with patch.object(worker.urllib.request,'urlopen') as network:
            with self.assertRaises(ValueError):worker.get_json('/repos/other/project/git/blobs','test-token',{})
            network.assert_not_called()

    def test_only_blob_creation_is_admissible_write(self):
        for route in ('git/refs/heads/main','pulls/1/reviews','pages','releases','actions/workflows/1/dispatches'):
            with patch.object(worker.urllib.request,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'ONLY_CONTENT_ADDRESSED'):
                    worker.get_json('/repos/Goldkelch/qik-vrt/'+route,'test-token',{})
                network.assert_not_called()

    def test_file_allowlist_rejects_workflows_refs_source_and_traversal(self):
        for value in ('../source.de.txt','docs/reise/translations/../../AI',
                      'docs/reise/source.de.txt','.github/workflows/qikvrt_ci.yml',
                      'docs/reise/translations/de.txt','docs/reise/translations/wuu.txt'):
            self.assertFalse(worker.allowed_file(value,'translate'))
            self.assertFalse(worker.allowed_file(value,'recover'))
        self.assertTrue(worker.allowed_file('docs/reise/translations/fr.txt','recover'))
        self.assertFalse(worker.allowed_file('docs/reise/translations/fr.txt','translate'))

    def test_old_source_content_is_reconstructible_not_evidence_transfer(self):
        raw,_=worker.source()
        previous=raw.replace(('\n\n\n'+worker.MEDIA+'\n\n\n').encode(),b'\n\n',1)
        self.assertEqual(worker.sha(previous),worker.OLD_SOURCE_SHA)
        self.assertEqual(len(worker.split(previous)),539)

    def test_incomplete_text_cannot_pass(self):
        _,original=worker.source()
        with self.assertRaises(ValueError):worker.validate_text(original[:-1],original)
        with self.assertRaises(ValueError):worker.validate_text(original,original)

    def test_link_or_signature_substitution_is_rejected(self):
        _,original=worker.source()
        for index in (1,len(original)-1):
            altered=original.copy();altered[0]='Translated';altered[index]='replacement'
            with self.assertRaisesRegex(ValueError,'PROTECTED_BLOCK'):
                worker.validate_text(altered,original)

    def test_rerun_fails_before_remote_observation(self):
        env={'GITHUB_SHA':'a'*40,'GITHUB_REPOSITORY':worker.REPO,
             'GITHUB_REF':'refs/heads/'+worker.BRANCH,'GITHUB_RUN_ATTEMPT':'2'}
        with patch.dict(os.environ,env),patch.object(worker.subprocess,'check_output',return_value='a'*40+'\n'),patch.object(worker,'get_json') as network:
            with self.assertRaisesRegex(ValueError,'BLIND_RERUN'):worker.exact_head(remote=True)
            network.assert_not_called()

    def test_receipt_explicitly_preserves_unreviewed_state(self):
        _,original=worker.source()
        values=original.copy();values[0]='Draft title'
        with tempfile.TemporaryDirectory() as tmp:
            worker.store_edition(Path(tmp),'fr',values,original,{'translator':'test fixture'})
            meta=json.loads((Path(tmp)/'files/docs/reise/translations/fr.json').read_text())
            self.assertFalse(meta['human_language_review'])
            self.assertFalse(meta['formal_semantic_equivalence_proof'])
            self.assertEqual(meta['status'],'AI_TRANSLATION_DRAFT_UNREVIEWED')

    def test_no_runner_context_in_job_level_env(self):
        text=(ROOT/'.github/workflows/qikvrt_journey_translation.yml').read_text()
        self.assertNotIn('\n    env:',text)
        self.assertIn('cancel-in-progress: false',text)
        self.assertIn('persist-credentials: false',text)
        self.assertIn('github.run_attempt == 1',text)

    def test_all_archived_inputs_are_local_and_hash_verified(self):
        raw,_=worker.source()
        old=worker.split(raw.replace(('\n\n\n'+worker.MEDIA+'\n\n\n').encode(),b'\n\n',1))
        with patch.object(worker,'get_json',side_effect=AssertionError('unexpected API read')):
            for code,identifier in worker.RECOVER.items():
                with self.subTest(code=code):
                    data=worker.recovered_input(code)
                    self.assertEqual(worker.blob(data),identifier)
                    worker.validate_text(worker.split(data),old)

    def test_changed_recovery_bytes_are_rejected_before_rebinding(self):
        with patch.object(worker,'read_file',return_value=b'changed'):
            with self.assertRaisesRegex(ValueError,'RECOVERED_BLOB_MISMATCH'):
                worker.recovered_input('fr')
        with self.assertRaisesRegex(ValueError,'UNKNOWN_RECOVERY_INPUT'):
            worker.recovered_input('../source.de')

    def test_pure_preparation_does_not_require_live_api_authority(self):
        text=inspect.getsource(worker.prepare)
        self.assertIn('exact_head(remote=False)',text)
        self.assertNotIn('get_json(',text)
        self.assertIn('exact_head(remote=True)',inspect.getsource(worker.objects))

    def test_http_403_is_diagnostic_not_blindly_retried_or_misclassified(self):
        exc=worker.urllib.error.HTTPError('https://api.github.com/repos/Goldkelch/qik-vrt/git/ref/heads/main',403,'Forbidden',
            {'X-RateLimit-Remaining':'0','X-RateLimit-Reset':'123'},
            io.BytesIO(b'{"message":"API rate limit exceeded; test-secret"}'))
        with patch.object(worker.urllib.request,'urlopen',side_effect=exc) as net,patch.object(worker,'emit') as emit:
            with self.assertRaises(worker.urllib.error.HTTPError):
                worker.get_json('/repos/Goldkelch/qik-vrt/git/ref/heads/main','test-secret')
            self.assertEqual(net.call_count,1)
            fields=emit.call_args.kwargs
            self.assertEqual(fields['http_status'],403)
            self.assertEqual(fields['rate_remaining'],'0')
            self.assertNotIn('test-secret',fields['message'])

    def test_failed_prepare_leaves_an_artifact_not_an_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv=['translation','prepare','--output',tmp]
            with patch.object(worker.sys,'argv',argv),patch.object(worker,'prepare',side_effect=ValueError('fixture failure')):
                self.assertEqual(worker.main(),2)
            failure=json.loads((Path(tmp)/'FAILURE.json').read_text())
            self.assertEqual(failure['error'],'fixture failure')
            self.assertFalse(failure['EFFECT_ACK_DONE'])

    def test_recovery_artifact_excludes_whole_repository_snapshot(self):
        text=(ROOT/'.github/workflows/qikvrt_journey_translation.yml').read_text()
        section=text.split('name: journey-recover-bundle-',1)[1].split('  model:',1)[0]
        self.assertIn('/tmp/qikvrt-journey-generation/files',section)
        self.assertIn('/tmp/qikvrt-journey-generation/FILESET.json',section)
        self.assertNotIn('path: /tmp/qikvrt-journey-generation\n',section)
        self.assertNotIn('TRACKED_SOURCE.zip',section)

if __name__=='__main__':unittest.main()

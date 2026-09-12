# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression tests for independent, attempt-bound draft recovery."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('journey_recovery',ROOT/'tools/qikvrt_journey_recovery.py')
assert spec and spec.loader
recovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(recovery)

class JourneyRecoveryTests(unittest.TestCase):
    def _jobs(self, failures=frozenset({'ast','bn','eu','pl','th'})):
        head='a'*40;run=123
        rows=[{'name':f'translate ({c})','head_sha':head,'run_id':run,'run_attempt':1,
               'status':'completed','conclusion':'failure' if c in failures else 'success'} for c in recovery.worker.TARGETS]
        return head,run,{'total_count':len(rows),'jobs':rows}

    def test_independent_successes_survive_failed_siblings(self):
        head,run,jobs=self._jobs();eligible,blocked=recovery.select_completed_drafts(jobs,head,run)
        self.assertEqual(blocked,{'ast':'failure','bn':'failure','eu':'failure','pl':'failure','th':'failure'})
        self.assertEqual(len(eligible),29);self.assertEqual(eligible|set(blocked),set(recovery.worker.TARGETS))

    def test_incomplete_or_active_inventory_fails_closed(self):
        head,run,jobs=self._jobs();jobs['jobs'].pop();jobs['total_count']-=1
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_LANGUAGE_JOB_INVENTORY'):
            recovery.select_completed_drafts(jobs,head,run)
        head,run,jobs=self._jobs();jobs['jobs'][0]['status']='in_progress'
        with self.assertRaisesRegex(ValueError,'UNBOUND_OR_ACTIVE_INPUT_JOB'):
            recovery.select_completed_drafts(jobs,head,run)

    def test_workflow_uses_partial_recorder_without_weakening_final_coverage(self):
        text=(ROOT/'.github/workflows/qikvrt_journey_translation.yml').read_text()
        self.assertIn("needs.translate.result != 'skipped'",text)
        self.assertIn('tools/qikvrt_journey_recovery.py',text)
        self.assertIn("github.event.before == '968482b55b99aace753b43eb0e219eea45111d0c'",text)
        self.assertIn('--input-run 34660991113',text)
        self.assertIn('--input-head 968482b55b99aace753b43eb0e219eea45111d0c',text)
        self.assertNotIn('continue-on-error: true',text)

    def test_later_attempt_cannot_replace_selected_job_attempt(self):
        h,r,j=self._jobs();j['jobs'][0]['run_attempt']=2
        with self.assertRaisesRegex(ValueError,'WRONG_INPUT_JOB_ATTEMPT'):
            recovery.select_completed_drafts(j,h,r,1)

    def test_missing_attempt_is_not_assumed(self):
        h,r,j=self._jobs();j['jobs'][0].pop('run_attempt')
        with self.assertRaisesRegex(ValueError,'WRONG_INPUT_JOB_ATTEMPT'):
            recovery.select_completed_drafts(j,h,r,1)

    def _artifacts(self,codes):
        rows=[{'name':'journey-translate-'+c+'-'+'a'*40} for c in codes]
        return {'total_count':len(rows),'artifacts':rows}

    def test_failed_setup_without_artifact_does_not_hide_success(self):
        h,r,j=self._jobs({'hr'});eligible,blocked=recovery.select_completed_drafts(j,h,r,1)
        rows,selected=recovery.select_artifacts(self._artifacts(eligible),h,eligible,{'ast','bn','eu','pl','th'})
        self.assertEqual(len(selected),5);self.assertNotIn('hr',rows);self.assertEqual(blocked,{'hr':'failure'})

    def test_missing_successful_artifact_fails(self):
        with self.assertRaisesRegex(ValueError,'MISSING_SUCCESSFUL_LANGUAGE_ARTIFACT'):
            recovery.select_artifacts(self._artifacts({'ast'}),'a'*40,{'ast','bn'},{'bn'})

    def test_requested_failed_language_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'REQUESTED_LANGUAGE_NOT_SUCCESSFUL'):
            recovery.select_artifacts(self._artifacts({'ast','hr'}),'a'*40,{'ast'},{'hr'})

    def test_duplicate_artifact_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'WRONG_OR_DUPLICATE_LANGUAGE_ARTIFACT'):
            recovery.select_artifacts(self._artifacts(['ast','ast']),'a'*40,{'ast'})

    def test_recovery_wake_has_both_predicates_and_explicit_attempt(self):
        text=(ROOT/'.github/workflows/qikvrt_journey_translation.yml').read_text()
        self.assertIn("github.event.before == '27448d95b7d2a7f2db1459a54af6379b9df5e35a'",text)
        self.assertIn('--input-run 34676257032',text)
        self.assertIn('--input-attempt 1 --languages ast bn eu pl th',text)
        self.assertIn('tools/qikvrt_journey_recovery.py\n',text)

if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression tests for independent journey draft recovery."""
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
        rows=[{'name':f'translate ({code})','head_sha':head,'run_id':run,'status':'completed',
               'conclusion':'failure' if code in failures else 'success'}
              for code in recovery.worker.TARGETS]
        return head,run,{'total_count':len(rows),'jobs':rows}

    def test_independent_successes_survive_failed_siblings(self):
        head,run,jobs=self._jobs()
        eligible,blocked=recovery.select_completed_drafts(jobs,head,run)
        self.assertEqual(blocked,{'ast':'failure','bn':'failure','eu':'failure','pl':'failure','th':'failure'})
        self.assertEqual(len(eligible),29)
        self.assertEqual(eligible|set(blocked),set(recovery.worker.TARGETS))

    def test_incomplete_or_active_inventory_fails_closed(self):
        head,run,jobs=self._jobs()
        jobs['jobs'].pop();jobs['total_count']-=1
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

if __name__=='__main__':unittest.main()

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import copy
from pathlib import Path
import tempfile
import unittest
from tools.qikvrt_repair_effectiveness_guard import SCHEMA, REPO, classify, modules_for, policy, source_contract

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    p, pd = policy(ROOT)
    h, t = '1'*40, '2'*40
    s = {'schema':SCHEMA, 'repository':REPO, 'head':h, 'tree':t,
         'main_before':h, 'main_after':h, 'source_after':{'head':h,'tree':t},
         'source_contract':True, 'worktree_clean':True, 'policy_sha256':pd,
         'adoption':{'pr':1071, 'merged':True, 'head':'3'*40, 'merge_commit':'4'*40,
                     'head_is_ancestor':True, 'merge_is_ancestor':True},
         'adoption_review':{'id':1,'author':'Goldkelch','state':'APPROVED','commit_id':'3'*40},
         'ruleset':{'state':'CURRENT','mutation':'NONE','repository':REPO,'ruleset_id':19344903,
                    'pre_state_sha256':'5'*64, 'desired_state_sha256':'5'*64},
         'probes':{m:{'head':h,'tree':t,'status':'EXECUTED','exit_code':0,'tests_run':1,'tests_skipped':0,'log_sha256':'6'*64} for m in modules_for(p)}}
    return p, s


class RepairEffectivenessTests(unittest.TestCase):
    def test_complete_bound_fixture_closes_only_declared_scope(self):
        p,s=fixture(); r=classify(s,p)
        self.assertIs(r['closed'],True)
        self.assertIs(r['future_immunity'],False)
        self.assertIs(r['publication'],False)

    def test_old_boolean_only_guard_input_never_closes(self):
        p,_=fixture()
        for flag in (True, 'false', 1, {}, []):
            s=dict(repair=True,promotion_bound=flag,effective_on_main=flag,regression_probe_success=flag)
            self.assertIs(classify(s,p)['closed'],False)

    def test_candidate_success_without_actual_adoption_is_not_closed(self):
        p,s=fixture(); s['adoption']['merged']=False
        self.assertEqual(classify(s,p)['state'],'VERIFIED_NOT_EFFECTIVE')

    def test_merged_but_not_in_main_history_is_not_effective(self):
        p,s=fixture()
        for key in ('head_is_ancestor','merge_is_ancestor'):
            c=copy.deepcopy(s); c['adoption'][key]=False
            self.assertIs(classify(c,p)['closed'],False)

    def test_same_tree_new_head_invalidates_probe(self):
        p,s=fixture(); next(iter(s['probes'].values()))['head']='9'*40
        self.assertIs(classify(s,p)['closed'],False)

    def test_head_changes_during_observation(self):
        p,s=fixture()
        for key in ('main_before','main_after'):
            c=copy.deepcopy(s); c[key]='9'*40
            self.assertIs(classify(c,p)['closed'],False)
        s['source_after']['tree']='9'*40
        self.assertIs(classify(s,p)['closed'],False)

    def test_zero_jobs_skipped_action_required_and_zero_tests_fail_closed(self):
        p,s=fixture(); name=next(iter(s['probes']))
        for patch in ({'status':'SKIPPED'},{'status':'ACTION_REQUIRED'},{'status':'TIMEOUT'},
                      {'status':'SUCCESS'},{'tests_run':0},{'tests_run':True},{'tests_skipped':1},{'tests_skipped':None},{'tests_skipped':False},
                      {'exit_code':False},{'exit_code':1},{'exit_code':None},{'log_sha256':None}):
            c=copy.deepcopy(s); c['probes'][name].update(patch)
            with self.subTest(patch=patch): self.assertIs(classify(c,p)['closed'],False)

    def test_missing_registered_probe_cannot_disappear_as_success(self):
        p,s=fixture(); s['probes'].pop(next(iter(s['probes'])))
        self.assertEqual(classify(s,p)['state'],'PROBE_COVERAGE_INCOMPLETE')

    def test_rule_drift_and_green_transport_do_not_prove_rule_effect(self):
        p,s=fixture()
        for patch in ({'state':'DRIFT'},{'state':'success'},{'mutation':'PUT'},
                      {'repository':'ingolf-lohmann/qik-vrt'},{'pre_state_sha256':'9'*64}):
            c=copy.deepcopy(s); c['ruleset'].update(patch)
            self.assertIs(classify(c,p)['closed'],False)

    def test_review_request_comment_bot_or_predecessor_is_not_adoption_review(self):
        p,s=fixture()
        for patch in ({'state':'COMMENTED'},{'state':'REQUESTED'}, {'author':'github-actions[bot]'},
                      {'author':'ingolf-lohmann'},{'commit_id':'9'*40},{'id':True}):
            c=copy.deepcopy(s); c['adoption_review'].update(patch)
            self.assertIs(classify(c,p)['closed'],False)

    def test_dirty_or_unknown_observations_are_not_closed(self):
        p,s=fixture()
        for key in ('source_contract','worktree_clean'):
            for bad in (False,None,1,'true'):
                c=copy.deepcopy(s); c[key]=bad
                self.assertIs(classify(c,p)['closed'],False)
        for bad in (None, [], {}, {'schema':SCHEMA}):
            self.assertIs(classify(bad,p)['closed'],False)

    def test_real_source_and_main_consumer_are_connected(self):
        r=source_contract(ROOT)
        self.assertIs(r['source_contract'],True)
        self.assertIs(r['closed'],False)

    def test_mutated_bootstrap_and_recipe_are_rejected_before_any_network(self):
        workflow='.github/workflows/qikvrt_autonomous_ruleset_effect_loop.yml'
        doc='docs/operations/GITHUB_RULESET_ADMIN_APP.md'
        cases=[(workflow,'GH_TOKEN: ${{ github.token }}','GH_TOKEN: ${{ secrets.QIKVRT_RULESET_ADMIN_TOKEN }}'),
               (workflow,'app-id: ${{ vars.QIKVRT_RULESET_APP_ID }}','client-id: ${{ vars.QIKVRT_RULESET_APP_CLIENT_ID }}'),
               (doc,'QIKVRT_RULESET_APP_ID','QIKVRT_RULESET_APP_CLIENT_ID')]
        for path,before,after in cases:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as td:
                temp=Path(td)
                for rel in ('policy/REPAIR_EFFECTIVENESS_CLOSURE_V1.json',workflow,doc,'Makefile','.github/workflows/qikvrt_zero_bug_continuous.yml'):
                    dst=temp/rel; dst.parent.mkdir(parents=True,exist_ok=True)
                    dst.write_bytes((ROOT/rel).read_bytes())
                text=(temp/path).read_text(); self.assertIn(before,text)
                (temp/path).write_text(text.replace(before,after))
                with self.assertRaises(ValueError): source_contract(temp)

    def test_main_effect_job_cannot_create_candidate_promotion_cycle(self):
        text=(ROOT/'.github/workflows/qikvrt_zero_bug_continuous.yml').read_text()
        block=text.split('  repair-effectiveness:',1)[1]
        self.assertIn("github.ref == 'refs/heads/main'",block)
        self.assertIn("github.event_name != 'pull_request'",block)
        self.assertIn('needs: verify',block)
        self.assertIn('if: always()',block)
        self.assertNotIn('statuses: write',block)
        self.assertNotIn('pull-requests: write',block)
        self.assertNotIn('gh pr merge',block)
        self.assertNotIn('workflow_dispatch:',block)


    def test_main_consumer_nested_indentation_is_not_lost(self):
        text=(ROOT/'.github/workflows/qikvrt_zero_bug_continuous.yml').read_text()
        block=text.split('  repair-effectiveness:',1)[1]
        for line in ('        with:', '          fetch-depth: 0', '          persist-credentials: false', '          if-no-files-found: error'):
            self.assertIn(line,block.splitlines())
        for line in block.splitlines():
            if line.strip(): self.assertTrue(line.startswith('    '),repr(line))

if __name__=='__main__': unittest.main()

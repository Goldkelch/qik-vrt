import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CloudSubjectTests(unittest.TestCase):
    def execute(self, mode):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); repo = root/'repo'; repo.mkdir()
            (repo/'src').mkdir(); (repo/'src/probe.py').write_text('bound = True\n')
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
            git('init', '-q'); git('add', '.')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
            head, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
            env = dict(os.environ, QIKVRT_EXACT_HEAD=head, QIKVRT_EXACT_TREE=tree,
                       RAILWAY_GIT_COMMIT_SHA='0'*40)
            if mode == 'head': env['QIKVRT_EXACT_HEAD'] = '1'*40
            if mode == 'tree': env['QIKVRT_EXACT_TREE'] = '2'*40
            if mode == 'dirty': (repo/'src/probe.py').write_text('bound = False\n')
            script = (ROOT/'deploy/universal-terminal/cloud-entrypoint.sh').read_text().split('# Public cloud materialization:', 1)[0]
            target = root/'health.json'
            script = script.replace('/opt/qikvrt', str(repo)).replace('/tmp/qikvrt-mesh-health.json', str(target))
            run = subprocess.run(['sh'], input=script+'\nemit_health READY\n', text=True, capture_output=True, env=env)
            if mode == 'match':
                self.assertEqual(run.returncode, 0, run.stderr)
                got=json.loads(target.read_text())
                self.assertEqual((got['commit'], got['tree']), (head, tree))
                self.assertEqual(got['subject_binding'], 'OBSERVED_GIT_HEAD_TREE')
                self.assertEqual(got['effect_ack'], 'NOT_IMPLIED')
            else:
                self.assertEqual(run.returncode, 78, run.stderr)
                self.assertFalse(target.exists())
    def test_actual_head_and_tree_override_old_provider_base(self): self.execute('match')
    def test_head_drift_fails_closed(self): self.execute('head')
    def test_tree_drift_fails_closed(self): self.execute('tree')
    def test_dirty_runtime_source_fails_closed(self): self.execute('dirty')

if __name__ == '__main__': unittest.main()

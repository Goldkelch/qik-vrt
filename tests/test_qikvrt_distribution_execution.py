"""Delivery regressions: real shell argv and dropped-UID nginx log opening.

The Docker command is a fixture, not an actual image execution. The dedicated
workflow installs nginx to run the real privilege-bound configuration probe.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/qikvrt_megast_distribution_v1.yml'
NGINX = ROOT / 'deploy/universal-terminal/nginx.conf'


def step(name):
    text = WORKFLOW.read_text()
    marker = '      - name: ' + name + '\n'
    if marker not in text:
        raise AssertionError('missing named step: ' + name)
    return text.split(marker, 1)[1].split('\n      - ', 1)[0]


def shell(name):
    return textwrap.dedent(step(name).split('        run: |\n', 1)[1])


class DistributionExecutionTests(unittest.TestCase):
    def test_pr_identity_comes_from_event_or_explicit_configuration(self):
        text = WORKFLOW.read_text()
        self.assertIn('QIKVRT_TEMDD_PR: ${{ github.event.pull_request.number || vars.QIKVRT_TEMDD_PR }}', text)
        self.assertNotRegex(text, r'QIKVRT_TEMDD_PR:\s*(1103|1124)\b')

    def invoke_launch_prefix(self, pr):
        script = shell('Load public Docker archive and execute exact runtime').split('ready=0', 1)[0]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stub = root / 'docker'
            trace = root / 'calls.jsonl'
            stub.write_text('#!/usr/bin/env python3\n'
                'import json,os,sys\n'
                'with open(os.environ["TRACE"], "a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n'
                'if sys.argv[1:3] == ["image","inspect"]:\n'
                ' print(os.environ["QIKVRT_EXACT_TREE" if "source.tree" in sys.argv[4] else "QIKVRT_EXACT_SHA"])\n'
                'elif sys.argv[1] == "run": print("fixture-container")\n')
            stub.chmod(0o755)
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'], TRACE=str(trace),
                       QIKVRT_EXACT_SHA='a' * 40, QIKVRT_EXACT_TREE='b' * 40)
            env.pop('QIKVRT_TEMDD_PR', None)
            if pr is not None:
                env['QIKVRT_TEMDD_PR'] = pr
            # The acceptance trap targets runner paths. Substitute only its
            # evidence directory in this command/argv fixture.
            script = script.replace('/tmp/qikvrt-public-readback', str(root))
            result = subprocess.run(['bash', '-s'], input=script, text=True, capture_output=True, env=env, timeout=10)
            calls = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
            return result, calls

    def test_missing_or_invalid_pr_stops_before_any_docker_effect(self):
        for pr in (None, '', '0', '01', '-1', '1124x', '1;echo injected', '1 2'):
            with self.subTest(pr=pr):
                result, calls = self.invoke_launch_prefix(pr)
                self.assertEqual(result.returncode, 64, result.stderr)
                self.assertEqual(calls, [])

    def test_valid_pr_reaches_exact_container_argv(self):
        result, calls = self.invoke_launch_prefix('1124')
        self.assertEqual(result.returncode, 0, result.stderr)
        runs = [call for call in calls if call[0] == 'run']
        self.assertEqual(len(runs), 1)
        self.assertIn('QIKVRT_TEMDD_PR=1124', runs[0])
        self.assertIn('QIKVRT_EXACT_HEAD=' + 'a' * 40, runs[0])
        self.assertIn('QIKVRT_EXACT_TREE=' + 'b' * 40, runs[0])
        self.assertIn('127.0.0.1:18080:8080', runs[0])

    def test_iso_depends_on_download_not_unrelated_container_result(self):
        readback = step('Fresh unauthenticated complete public payload readback')
        self.assertIn('id: public_readback', readback)
        firmware = step('Boot downloaded ISO through BIOS firmware, not a supplied kernel')
        self.assertIn("if: ${{ !cancelled() && steps.public_readback.outcome == 'success' }}", firmware)
        self.assertNotIn('continue-on-error', WORKFLOW.read_text())
        self.assertNotIn('-kernel ', firmware)
        self.assertNotIn('-initrd ', firmware)

    def test_container_probe_compares_public_temdd_subject(self):
        probe = shell('Load public Docker archive and execute exact runtime')
        self.assertIn('/api/temdd/subject', probe)
        for key in ('repository', 'pr', 'head', 'tree'):
            self.assertIn("'" + key + "'", probe)
        self.assertIn('PUBLIC_TEMDD_SUBJECT_MISMATCH', probe)

    def test_access_log_is_preserved_without_elevating_gateway(self):
        self.assertIn('error_log stderr info;', NGINX.read_text())
        self.assertIn('access_log /tmp/nginx-access.log;', NGINX.read_text())
        probe = shell('Load public Docker archive and execute exact runtime')
        self.assertIn(':/tmp/nginx-access.log', probe)
        self.assertNotIn('--privileged', probe)

    def test_every_workflow_shell_block_parses(self):
        blocks = re.findall(r'^        run: \|\n((?:^          .*\n|^\n)+)', WORKFLOW.read_text(), re.M)
        blocks += re.findall(r'^        run: (?!\|)(.+)$', WORKFLOW.read_text(), re.M)
        self.assertGreaterEqual(len(blocks), 16)
        for block in blocks:
            result = subprocess.run(['bash', '-n'], input=textwrap.dedent(block), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)


class UnprivilegedNginxTests(unittest.TestCase):
    def test_config_opens_logs_without_reopening_root_owned_stdio(self):
        nginx = shutil.which('nginx')
        if not nginx or not shutil.which('runuser'):
            self.skipTest('nginx/runuser required; installed by distribution contract')
        prefix = [] if os.geteuid() == 0 else ['sudo', '-n']
        with tempfile.TemporaryDirectory(prefix='qikvrt-nginx-uid-') as d:
            root = Path(d)
            root.chmod(0o755)
            work = root / 'writable'
            work.mkdir(mode=0o700)
            change = subprocess.run(prefix + ['chown', '65534:65534', str(work)], capture_output=True, text=True)
            self.assertEqual(change.returncode, 0, change.stderr)
            text = NGINX.read_text().replace('/tmp/nginx', str(work / 'nginx'))
            text = text.replace('listen 8080;', 'listen 127.0.0.1:18089;')
            config = root / 'nginx.conf'
            config.write_text(text)
            config.chmod(0o644)
            command = prefix + ['runuser', '-u', 'nobody', '--', nginx, '-t', '-c', str(config)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            # Negative control: only the two log destinations revert. The same
            # dropped UID and root-owned captured stdio must reproduce EACCES.
            bad = text.replace('error_log stderr info;', 'error_log /dev/stderr info;')
            bad = bad.replace('access_log ' + str(work / 'nginx-access.log') + ';', 'access_log /dev/stdout;')
            config.write_text(bad)
            negative = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(negative.returncode, 0)
            self.assertIn('Permission denied', negative.stderr)
            self.assertIn('/dev/stderr', negative.stderr)
            subprocess.run(prefix + ['chown', '-R', str(os.getuid()) + ':' + str(os.getgid()), str(work)], check=True)


if __name__ == '__main__':
    unittest.main()

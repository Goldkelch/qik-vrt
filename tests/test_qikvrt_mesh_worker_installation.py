# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Portable admission checks for a worker with a different local review core."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock

from tools import qikvrt_review_mesh_work as mesh


class PortableWorkerTest(unittest.TestCase):
    def test_main_activation_preserves_predecessor_review(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/qikvrt_requested_review_executor.yml').read_text()
        section = workflow.split('- name: Detect trusted-main activation', 1)[1].split('\n      - name:', 1)[0]
        script = textwrap.dedent(section.split('run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tools').mkdir()
            (root / 'tools/qikvrt_requested_review_executor.py').touch()
            output = root / 'output'
            for installed in (False, True):
                if installed:
                    for name in ('qikvrt_github_observation.py', 'qikvrt_review_mesh_work.py'):
                        (root / 'tools' / name).touch()
                output.write_text('')
                subprocess.run(['bash', '-e', '-c', script], cwd=root, check=True,
                               env={**os.environ, 'GITHUB_OUTPUT': str(output)}, capture_output=True)
                values = dict(line.split('=', 1) for line in output.read_text().splitlines())
                self.assertEqual(values['active'], 'true')
                if 'Bind lossless counterpart work' in workflow:
                    self.assertEqual(values['scaling'], str(installed).lower())
                    self.assertIn("steps.active.outputs.scaling == 'true'", workflow)

    def test_source_main_and_run_are_verified_before_code_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = {"schema": "qikvrt_review_mesh_work_v1",
                    "source_repository": "Goldkelch/qik-vrt", "worker_repository": "ingolf-lohmann/qik-vrt",
                    "source_main_sha": "a" * 40, "source_run_id": "123", "source_run_attempt": "2",
                    "head_sha": "c" * 40, "pr_number": 1240}
            raw = json.dumps(work).encode()
            (root / "work.json").write_bytes(raw)
            client = mock.Mock()
            main = {"sha": "a" * 40}
            run = {"path": ".github/workflows/qikvrt_requested_review_executor.yml",
                   "id": 123, "repository": {"full_name": "Goldkelch/qik-vrt"},
                   "head_branch": "feature/review", "head_sha": "c" * 40,
                   "pull_requests": [{"number": 1240, "base": {"ref": "main"}}],
                   "run_attempt": 2, "event": "pull_request_target"}
            with mock.patch.object(mesh, "ObservationClient", return_value=client), \
                    mock.patch.object(mesh, "git", return_value="b" * 40), \
                    mock.patch.dict("os.environ", {"SOURCE_RUN_ID": "123", "GH_TOKEN": "fixture"}):
                client.get.side_effect = [(main, {}), (run, {})]
                result = mesh.verify_source(root, mesh.digest(raw), "ingolf-lohmann/qik-vrt")
                self.assertEqual(result["sha"], "a" * 40)
                self.assertEqual(result["worker_head"], "b" * 40)
                client.get.side_effect = [({"sha": "c" * 40}, {})]
                with self.assertRaisesRegex(ValueError, "SOURCE_TRUSTED_MAIN_DRIFT"):
                    mesh.verify_source(root, mesh.digest(raw), "ingolf-lohmann/qik-vrt")
                client.get.side_effect = [(main, {}), ({**run, "path": ".github/workflows/untrusted.yml"}, {})]
                with self.assertRaisesRegex(ValueError, "SOURCE_TRUSTED_RUN_MISMATCH"):
                    mesh.verify_source(root, mesh.digest(raw), "ingolf-lohmann/qik-vrt")
                with self.assertRaisesRegex(ValueError, "WORK_DIGEST_MISMATCH"):
                    mesh.verify_source(root, "0" * 64, "ingolf-lohmann/qik-vrt")
                for changed in ({"head_sha": "d" * 40}, {"id": 124},
                                {"repository": {"full_name": "other/repo"}},
                                {"pull_requests": []}):
                    client.get.side_effect = [(main, {}), ({**run, **changed}, {})]
                    with self.assertRaisesRegex(ValueError, "SOURCE_TRUSTED_RUN_MISMATCH"):
                        mesh.verify_source(root, mesh.digest(raw), "ingolf-lohmann/qik-vrt")

    def test_workflow_reads_preserve_predecessor_until_transport_is_on_main(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/qikvrt_requested_review_executor.yml').read_text()
        blocks = re.findall(r"python3 -B - <<'PY'[^\n]*\n(.*?)\n          PY", workflow, re.S)
        checked = 0
        for block in blocks:
            tree = ast.parse(textwrap.dedent(block))
            functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
            names = {n.name for n in functions}
            if 'gh' in names:
                nodes = [n for n in tree.body if
                         isinstance(n, ast.ClassDef) and n.name == 'LedgerHold' or
                         isinstance(n, ast.FunctionDef) and n.name == 'gh']
                import pathlib
                namespace = {'json': json, 'subprocess': subprocess, 'pathlib': pathlib}
                exec(compile(ast.Module(body=nodes, type_ignores=[]), '<workflow>', 'exec'), namespace)
                with mock.patch.object(Path, 'is_file', return_value=False), \
                        mock.patch.object(subprocess, 'run', return_value=
                                          subprocess.CompletedProcess([], 0, '{"legacy":true}', '')) as legacy:
                    self.assertEqual(namespace['gh']('GET', 'repos/a/b/pulls/1'), {'legacy': True})
                    legacy.assert_called_once()
                checked += 1
            elif {'one', 'pages'} <= names and 'environment_client' in block:
                start = block.index('          from pathlib import Path')
                end = block.index('              return out', start) + len('              return out')
                helpers = textwrap.dedent(block[start:end])
                for installed in (False, True):
                    namespace = {'json': json, 'subprocess': subprocess}
                    client = mock.Mock()
                    client.get.return_value = ({'fresh': True}, {})
                    client.pages.return_value = [[{'fresh': True}]]
                    with mock.patch.object(Path, 'is_file', return_value=installed), \
                            mock.patch('tools.qikvrt_github_observation.environment_client', return_value=client), \
                            mock.patch.object(subprocess, 'check_output', side_effect=
                                              ['{"legacy":true}', '[[{"legacy":true}]]']) as legacy:
                        exec(helpers, namespace)
                        expected = {'fresh': True} if installed else {'legacy': True}
                        self.assertEqual(namespace['one']('repos/a/b/pulls/1'), expected)
                        self.assertEqual(namespace['pages']('repos/a/b/pulls'), [expected])
                        self.assertEqual(legacy.call_count, 0 if installed else 2)
                checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()

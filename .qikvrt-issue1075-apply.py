#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""One-shot authoring transform for #1075; never an approval or effect receipt."""
import ast
import hashlib
import importlib.util
import pathlib
import subprocess
from unittest import mock
from urllib.parse import parse_qs, urlsplit

ROOT = pathlib.Path.cwd()
BASE = 'cc3aa741f7721157763a0c5a67965deb15c5acbd'
SOURCE = ROOT / 'tools/qikvrt_requested_review_executor.py'
TESTS = ROOT / 'tests/test_qikvrt_requested_review_executor.py'
BLOBS = {SOURCE: '1e84d57c478688ad6987ba800e51ce1f88380334',
         TESTS: '05ae71ce092ab770dfbfd75f0db4742c3ba67dc1'}

def require(condition, message):
    if not condition:
        raise SystemExit('HOLD_UNVERIFIED: ' + message)

require(subprocess.check_output(['git', 'rev-parse', 'HEAD^'], text=True).strip() == BASE,
        'bootstrap parent differs from bound source')
for path, expected in BLOBS.items():
    raw = path.read_bytes()
    require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == expected,
            'source blob drift: ' + str(path))

# Reproduce the actual old observer with more than one history page, offline.
spec = importlib.util.spec_from_file_location('issue1075_preimage', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
head = 'b' * 40
for active in (False, True):
    rows = [dict(id=10000 + i, head_sha=head, status='completed', name='writer') for i in range(250)]
    if active:
        rows.append(dict(id=7, head_sha=head, status='in_progress', name='writer'))
    def read(endpoint):
        query = parse_qs(urlsplit(endpoint).query)
        require(query.get('head_sha') == [head], 'red witness escaped head')
        require('status' not in query, 'preimage no longer has the reported defect')
        return {'total_count': len(rows), 'workflow_runs': rows[:100]}
    with mock.patch.object(module, '_gh_one', side_effect=read) as reader:
        try:
            module._active_writer_observation('example/qik-vrt', 999, {'writer'}, {head})
        except module.ReviewObservationError as exc:
            require('incomplete' in str(exc), 'unexpected red witness')
        else:
            raise SystemExit('HOLD_UNVERIFIED: expected history defect not reproduced')
        require(reader.call_count == 1, 'red witness exceeded one read')
    print('REPRODUCED history-dependent HOLD: completed=250 active=' + str(int(active)))

def replace_definition(text, name, replacement):
    nodes = [node for node in ast.walk(ast.parse(text))
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    require(len(nodes) == 1, 'definition absent or ambiguous: ' + name)
    node = nodes[0]
    lines = text.splitlines(keepends=True)
    lines[node.lineno - 1:node.end_lineno] = [replacement.rstrip() + '\n']
    return ''.join(lines)

SOURCE.write_text(replace_definition(SOURCE.read_text(), '_active_writer_observation',
                  (ROOT / '.qikvrt-issue1075-function.py').read_text()))
scoped = '''    def test_active_writer_observation_is_exact_head_scoped(self):
        fixture = ActiveWriterHistoryIndependenceTests()
        rows = [fixture.row(902, head=MAIN_SHA, status="queued"),
                fixture.row(904, head=HEAD_SHA, status="waiting"),
                fixture.row(999, head=MAIN_SHA, status="in_progress"),
                fixture.row(905, head=HEAD_SHA, status="pending", name="observer")]
        calls = []
        observed = fixture.observe(fixture.api(rows, calls))
        self.assertEqual([row["id"] for row in observed], [902, 904])
        self.assertEqual(calls, [
            f"repos/example/qik-vrt/actions/runs?head_sha={head}&status={status}&per_page=100&page=1"
            for head in sorted({MAIN_SHA, HEAD_SHA})
            for status in MODULE.ACTIVE_WRITER_STATES
        ])
'''
incomplete = '''    def test_active_writer_observation_rejects_incomplete_exact_head_page(self):
        with mock.patch.object(MODULE, "_gh_one", return_value={
            "total_count": 101, "workflow_runs": [],
        }) as read:
            with self.assertRaisesRegex(MODULE.ReviewObservationError, "exact-head workflow-run page is incomplete"):
                MODULE._active_writer_observation("example/qik-vrt", 999, {"writer"}, {MAIN_SHA, HEAD_SHA})
            read.assert_called_once_with(
                f"repos/example/qik-vrt/actions/runs?head_sha={MAIN_SHA}&status=queued&per_page=100&page=1"
            )
'''
text = replace_definition(TESTS.read_text(), 'test_active_writer_observation_is_exact_head_scoped', scoped)
text = replace_definition(text, 'test_active_writer_observation_rejects_incomplete_exact_head_page', incomplete)
marker = '\nif __name__ == "__main__":'
require(text.count(marker) == 1, 'test entrypoint absent or ambiguous')
text = text.replace(marker, '\n\n' + (ROOT / '.qikvrt-issue1075-tests.py').read_text() + '\n' + marker)
TESTS.write_text(text)
ast.parse(SOURCE.read_text())
ast.parse(TESTS.read_text())
print('APPLIED: only active-writer observer and its existing regression module changed')

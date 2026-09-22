# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class PullRequestHeadMutationBoundaryTests(unittest.TestCase):
    def test_dynamic_pr_head_writers_are_guarded_from_pull_request_events(self) -> None:
        offenders: list[str] = []
        for path in sorted(WORKFLOWS.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            if "pull_request:" not in text:
                continue
            derives_pr_target = (
                "github.event_name == 'pull_request' && github.head_ref" in text
                or "github.event_name == \"pull_request\" && github.head_ref" in text
            )
            if not derives_pr_target:
                continue
            blocks = text.split("\n      - name: ")
            for block in blocks:
                mutates_target = (
                    'git push origin "HEAD:$TARGET_REF"' in block
                    or "git push origin 'HEAD:$TARGET_REF'" in block
                    or "git push origin HEAD:$TARGET_REF" in block
                )
                if not mutates_target:
                    continue
                guarded = (
                    "if: github.event_name != 'pull_request'" in block
                    or 'if: github.event_name != "pull_request"' in block
                    or "if: github.event_name == 'push'" in block
                    or 'if: github.event_name == "push"' in block
                )
                if not guarded:
                    offenders.append(path.as_posix())
        self.assertEqual(
            offenders,
            [],
            "PR workflows must never push to their own github.head_ref via TARGET_REF; "
            "materialize/read back without mutating the active PR head: "
            + ", ".join(offenders),
        )

    def test_primary_materializer_keeps_pr_persistence_read_only(self) -> None:
        path = WORKFLOWS / "qikvrt_batch04_integrity.yml"
        text = path.read_text(encoding="utf-8")
        marker = "- name: Commit materialized repository evidence"
        self.assertIn(marker, text)
        block = text[text.index(marker):]
        self.assertIn("if: github.event_name != 'pull_request'", block)
        self.assertIn('git push origin "HEAD:$TARGET_REF"', block)


    def test_primary_materializer_admits_publication_branch_push(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        push = text.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
        self.assertIn("      - docs/information-effect-axis-v1\n", push)
        self.assertIn("github.actor != 'github-actions[bot]'", text)
        self.assertNotIn("pull_request_target:", text)

    def test_primary_materializer_pins_checkout_to_event_head(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        self.assertIn(
            "EXPECTED_HEAD: ${{ github.event_name == 'pull_request' && "
            "github.event.pull_request.head.sha || github.sha }}",
            text,
        )
        self.assertIn("ref: ${{ env.EXPECTED_HEAD }}", text)
        self.assertNotIn("ref: ${{ env.TARGET_REF }}", text)

    def test_primary_materializer_retains_gate_and_drift_guards(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        marker = "- name: Commit materialized repository evidence"
        before, persist = text.split(marker, 1)
        self.assertIn("make test", before)
        self.assertIn("python3 tools/qikvrt_integrity.py verify", before)
        self.assertIn('if [ "$remote_head" != "$source_head" ]; then', persist)
        self.assertIn('if [ "$remote_head_after_commit" != "$source_head" ]; then', persist)
        self.assertIn('git push origin "HEAD:$TARGET_REF"', persist)
        self.assertNotIn("--force", persist)
        self.assertIn("if: github.event_name != 'pull_request'", persist)
        self.assertIn("permissions:\n  contents: write\n", text)
        self.assertIn("cancel-in-progress: false", text)


    def test_roundtrip_materialization_uses_the_admitted_branch_push(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        push = text.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
        self.assertIn("      - agent/repository-wide-roundtrip-invariant-v1\n", push)
        self.assertIn("github.actor != 'github-actions[bot]'", text)
        self.assertNotIn("pull_request_target:", text)

    def test_materialization_requires_fresh_remote_successor_readback(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        persist = text.split("- name: Commit materialized repository evidence", 1)[1]
        after_push = persist.split('git push origin "HEAD:$TARGET_REF"', 1)[1]
        self.assertIn('git ls-remote --heads origin "refs/heads/$TARGET_REF"', after_push)
        self.assertIn('test "$persisted_head" = "$readback_head"', after_push)
        self.assertIn('HEAD^{tree}', after_push)
        self.assertIn('EFFECT_ACK_CONTINUE', after_push)
        self.assertNotIn('EFFECT_ACK_DONE=true', after_push)


    def test_materializer_queues_pending_runs_without_changing_writer_lease(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        concurrency = text.split("concurrency:\n", 1)[1].split("\njobs:", 1)[0]
        self.assertIn("group: qikvrt-repository-evidence-${{ github.head_ref || github.ref_name }}\n", concurrency)
        self.assertIn("cancel-in-progress: false\n", concurrency)
        self.assertIn("queue: max\n", concurrency)
        self.assertNotIn("cancel-in-progress: true", concurrency)

    def test_boundary_tests_execute_before_any_persistence(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        before, _ = text.split("- name: Commit materialized repository evidence", 1)
        self.assertIn("python3 -B -m unittest -v tests.test_pr_head_mutation_boundary", before)

    def test_successor_reuses_exact_head_verifier_with_fresh_envelope(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        continuation = text.split("- name: Continue persisted roundtrip head through native verification", 1)[1]
        self.assertIn("if: github.event_name == 'push' && github.ref_name == 'agent/repository-wide-roundtrip-invariant-v1'", continuation)
        self.assertIn('test "$local_head" = "$remote_head"', continuation)
        self.assertIn('test "$current" = "$local_head"', continuation)
        self.assertIn('test "$common" = "$main_head"', continuation)
        self.assertIn('qikvrt_autonomous_exact_head_verify', continuation)
        self.assertIn('source_materializer_run_id:$source_run', continuation)
        self.assertIn('gh_json --method POST "repos/${GITHUB_REPOSITORY}/dispatches" --input "$payload"', continuation)
        self.assertNotIn('state=success', continuation)
        self.assertNotIn('EFFECT_ACK_DONE=true', continuation)

class MaterializerRateLimitTests(unittest.TestCase):
    """Execute the inline adapter with isolated HTTP/ref/clock fixtures."""

    def exercise(self, responses, *, drift=""):
        import json
        import os
        import subprocess
        import sys
        import tempfile
        import textwrap

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            binaries = root / "bin"
            binaries.mkdir()
            (root / "responses.json").write_text(json.dumps(responses))
            scripts = {
                "gh": '''#!/usr/bin/env python3
import json, os, pathlib, sys
r=pathlib.Path(os.environ["FIXTURE_ROOT"])
p=r/"calls.json"
a=json.loads(p.read_text()) if p.exists() else []
x=json.loads((r/"responses.json").read_text())[len(a)]
a.append(sys.argv[1:]); p.write_text(json.dumps(a))
sys.stdout.write(x.get("raw", "")); sys.exit(x.get("rc", 0))
''',
                "git": '''#!/usr/bin/env python3
import os, pathlib, sys
r=pathlib.Path(os.environ["FIXTURE_ROOT"])
main="refs/heads/main" in sys.argv
if "HEAD^{tree}" in sys.argv:
    print("d"*40); sys.exit(0)
v=("b" if main else "a")*40
if (r/"slept").exists() and os.environ.get("REF_DRIFT")==("main" if main else "head"):
    v="c"*40
print(v+"\\t"+("refs/heads/main" if main else "refs/heads/agent/repository-wide-roundtrip-invariant-v1") if "ls-remote" in sys.argv else v)
''',
                "sleep": '''#!/usr/bin/env python3
import os, pathlib, sys
r=pathlib.Path(os.environ["FIXTURE_ROOT"])
with (r/"sleeps.txt").open("a") as f: f.write(sys.argv[1]+"\\n")
(r/"slept").touch()
''',
            }
            for name, value in scripts.items():
                path = binaries / name
                path.write_text(value.replace("#!/usr/bin/env python3", "#!" + sys.executable + " -S", 1))
                path.chmod(0o755)
            text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text()
            step = text.split("- name: Continue persisted roundtrip head through native verification", 1)[1]
            script = textwrap.dedent(step.split("        run: |\n", 1)[1])
            prefix = script.split('pages="$RUNNER_TEMP/qikvrt-materialized-pr-pages.json"', 1)[0]
            payload = root / "payload.json"
            payload.write_text('{"event_type":"qikvrt_autonomous_exact_head_verify"}')
            environment = dict(os.environ, FIXTURE_ROOT=str(root), RUNNER_TEMP=str(root),
                               PATH=str(binaries)+os.pathsep+os.environ["PATH"],
                               TARGET_REF="agent/repository-wide-roundtrip-invariant-v1",
                               GITHUB_REPOSITORY="Goldkelch/qik-vrt", REF_DRIFT=drift,
                               PERSISTED_HEAD="a"*40, PERSISTED_TREE="d"*40,
                               GITHUB_RUN_ID="fixture-no-native-run")
            result = subprocess.run(["bash", "-c", prefix +
                '\ngh_json --method POST "repos/${GITHUB_REPOSITORY}/dispatches" --input "'+str(payload)+'"\n'],
                env=environment, text=True, capture_output=True, timeout=45)
            calls = json.loads((root / "calls.json").read_text()) if (root / "calls.json").exists() else []
            sleeps = [int(value) for value in (root / "sleeps.txt").read_text().splitlines()] if (root / "sleeps.txt").exists() else []
            return result, calls, sleeps

    @staticmethod
    def response(status, headers=None, body="", rc=None):
        fields = headers or {}
        raw = "HTTP/2.0 " + str(status) + " Fixture\r\n"
        raw += "".join(str(key) + ": " + str(value) + "\r\n" for key, value in fields.items())
        return {"raw": raw + "\r\n" + body, "rc": (0 if status < 300 else 1) if rc is None else rc}

    def test_primary_limit_obeys_reset_before_reusing_the_same_dispatch(self):
        import time
        limited = self.response(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": int(time.time())+30})
        result, calls, sleeps = self.exercise([limited, self.response(204)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(len(sleeps), 1)
        self.assertGreaterEqual(sleeps[0], 29)
        self.assertLessEqual(sleeps[0], 32)
        self.assertIn("--include", calls[0])
        self.assertIn("github.com", calls[0])

    def test_retry_after_is_honored(self):
        result, calls, sleeps = self.exercise([self.response(429, {"Retry-After": "2"}), self.response(204)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [2])

    def test_secondary_limit_without_headers_waits_at_least_a_minute(self):
        result, calls, sleeps = self.exercise([
            self.response(403, body='{"message":"secondary rate limit exceeded"}'), self.response(204)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [60])

    def test_permission_failure_is_not_retried(self):
        result, calls, sleeps = self.exercise([self.response(403, body='{"message":"Resource not accessible by integration"}')])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])

    def test_ambiguous_transport_and_server_failures_do_not_replay_post(self):
        for response in ({"raw": "", "rc": 1}, self.response(503)):
            with self.subTest(response=response):
                result, calls, sleeps = self.exercise([response])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(calls), 1)
                self.assertEqual(sleeps, [])

    def test_provider_delay_is_not_shortened_to_fit_the_carrier_budget(self):
        import time
        limited = self.response(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": int(time.time())+3600})
        result, calls, sleeps = self.exercise([limited])
        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertIn("HANDOFF_PENDING", result.stderr)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])

    def test_candidate_or_main_drift_prevents_a_repeated_dispatch(self):
        for drift in ("head", "main"):
            with self.subTest(drift=drift):
                result, calls, sleeps = self.exercise([self.response(429, {"Retry-After": "1"})], drift=drift)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(len(calls), 1)
                self.assertEqual(sleeps, [1])

    def test_retries_are_bounded_even_when_server_keeps_refusing(self):
        result, calls, sleeps = self.exercise([self.response(429, {"Retry-After": "1"})] * 4)
        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleeps, [1, 1, 1])

    def test_repository_envelope_is_filtered_without_polling_the_entire_queue(self):
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text()
        step = text.split("- name: Continue persisted roundtrip head through native verification", 1)[1]
        self.assertNotIn("--paginate", step)
        self.assertIn("state=open&base=main&head=${head_filter}&per_page=100", step)
        self.assertIn('test "$common" = "$main_head"', step)
        self.assertIn('select(.state == "open" and .base.ref == "main")', step)
        self.assertIn("retry_deadline=$((SECONDS + 600))", step)



class MaterializerHandoffIsolationTests(unittest.TestCase):
    def workflow(self) -> str:
        return (WORKFLOWS / 'qikvrt_batch04_integrity.yml').read_text(encoding='utf-8')

    def script(self, name: str) -> str:
        import textwrap
        block = self.workflow().split('      - name: ' + name + '\n', 1)[1]
        block = block.split('\n      - ', 1)[0].split('\n  handoff:', 1)[0]
        return textwrap.dedent(block.split('        run: |\n', 1)[1])

    def test_handoff_depends_on_successful_writer_without_replaying_it(self) -> None:
        text = self.workflow()
        materialize, handoff = text.split('\n  handoff:\n', 1)
        self.assertIn('    needs: materialize\n', handoff)
        self.assertNotIn('always()', handoff)
        self.assertNotIn('git push', handoff)
        self.assertNotIn('git commit', handoff)
        self.assertNotIn('make test', handoff)
        self.assertNotIn('gh_json', materialize)
        self.assertIn('    timeout-minutes: 15\n', handoff)
        self.assertIn('ref: ${{ env.PERSISTED_HEAD }}', handoff)
        for name in ('head_sha', 'tree_sha', 'source_sha', 'source_run_id'):
            self.assertIn(name + ': ${{ steps.persisted_subject.outputs.' + name + ' }}', materialize)
            self.assertIn('${{ needs.materialize.outputs.' + name + ' }}', handoff)
        self.assertLess(materialize.index('git push origin "HEAD:$TARGET_REF"'),
                        materialize.index('- name: Bind persisted materializer subject'))
        self.assertLess(handoff.index('Validate persisted handoff envelope before checkout'),
                        handoff.index('uses: actions/checkout@'))

    def test_missing_or_mismatched_outputs_fail_before_checkout(self) -> None:
        import os
        import subprocess
        environment = dict(os.environ, PERSISTED_HEAD='a'*40, PERSISTED_TREE='b'*40,
                           MATERIALIZER_SOURCE='c'*40, EVENT_SOURCE='c'*40,
                           MATERIALIZER_RUN='123', GITHUB_RUN_ID='123')
        script = self.script('Validate persisted handoff envelope before checkout')
        valid = subprocess.run(['bash', '-c', script], env=environment, capture_output=True, timeout=10)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        for overrides in ({'PERSISTED_HEAD': ''}, {'PERSISTED_TREE': 'refs/heads/main'},
                          {'MATERIALIZER_SOURCE': 'd'*40}, {'MATERIALIZER_RUN': '124'}):
            with self.subTest(overrides=overrides):
                result = subprocess.run(['bash', '-c', script], env=dict(environment, **overrides),
                                        capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)

    def test_handoff_error_diagnostics_cannot_contaminate_json_stdout(self) -> None:
        script = self.script('Continue persisted roundtrip head through native verification')
        self.assertIn('set -Eeuo pipefail', script)
        self.assertIn('HANDOFF_FAILURE phase=%s exit=%s subject=%s run=%s', script)
        self.assertIn('"$GITHUB_RUN_ID" >&2; exit "$rc"', script)
        for phase in ('BIND', 'PR_LOOKUP', 'PR_REOBSERVE', 'MAIN_ANCESTRY', 'DISPATCH'):
            self.assertIn('handoff_phase=' + phase, script)
        self.assertIn('test "$local_head" = "$PERSISTED_HEAD"', script)
        self.assertIn('test "$(git rev-parse --verify HEAD^{tree})" = "$PERSISTED_TREE"', script)

    def test_actual_git_subject_binding_and_remote_drift(self) -> None:
        import os
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            work = root / 'work'
            work.mkdir()
            remote = root / 'remote.git'
            branch = 'agent/repository-wide-roundtrip-invariant-v1'
            def git(*args):
                completed = subprocess.run(['git', *args], cwd=work, text=True,
                                           capture_output=True, timeout=15)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return completed.stdout.strip()
            git('init', '--bare', str(remote))
            git('init', '-b', branch)
            git('config', 'user.name', 'fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            git('remote', 'add', 'origin', str(remote))
            (work / 'subject').write_text('first\n')
            git('add', 'subject'); git('commit', '-m', 'fixture source')
            head = git('rev-parse', 'HEAD')
            tree = git('rev-parse', 'HEAD^{tree}')
            git('push', 'origin', branch)
            output = root / 'outputs'
            environment = dict(os.environ, TARGET_REF=branch, EXPECTED_HEAD=head,
                               GITHUB_RUN_ID='123', GITHUB_OUTPUT=str(output))
            script = self.script('Bind persisted materializer subject')
            result = subprocess.run(['bash', '-c', script], cwd=work, env=environment,
                                    text=True, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            values = dict(line.split('=', 1) for line in output.read_text().splitlines())
            self.assertEqual(values, {'head_sha': head, 'tree_sha': tree,
                                      'source_sha': head, 'source_run_id': '123'})
            (work / 'subject').write_text('new remote subject\n')
            git('add', 'subject'); git('commit', '-m', 'fixture concurrent advancement')
            git('push', 'origin', branch)
            git('checkout', '--detach', head)
            output.unlink()
            drift = subprocess.run(['bash', '-c', script], cwd=work, env=environment,
                                   text=True, capture_output=True, timeout=15)
            self.assertNotEqual(drift.returncode, 0)
            self.assertFalse(output.exists(), 'stale subject must never publish handoff outputs')

if __name__ == "__main__":
    unittest.main()

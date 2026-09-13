#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-Main repair closure, not a scheduler, signer, merger or repair writer.

Source checks are candidate-local. Operational closure is a separate read-only
Main observation with newly executed probes. Historical #770/#781/#785/#787
provide design provenance only. Their permissive boolean classifier is not used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'policy/REPAIR_EFFECTIVENESS_CLOSURE_V1.json'
REPO = 'Goldkelch/qik-vrt'
SHA = re.compile(r'[0-9a-f]{40}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
SCHEMA = 'qikvrt_exact_main_repair_closure_v2'


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def policy(root=ROOT):
    raw = (root / POLICY).read_bytes()
    value = json.loads(raw)
    require(value.get('schema') == 'qikvrt_repair_effectiveness_closure_v1', 'POLICY_SCHEMA')
    require(value.get('revision') == 2 and value.get('repository') == REPO, 'POLICY_BINDING')
    classes = value.get('failure_classes')
    require(isinstance(classes, dict) and bool(classes), 'EMPTY_REPAIR_REGISTRY')
    for name, item in classes.items():
        require(re.fullmatch(r'[A-Z][A-Z0-9_]+', name) is not None, 'CLASS_NAME')
        modules = item.get('regression_modules')
        require(isinstance(modules, list) and bool(modules), 'UNPROBED_CLASS:' + name)
        require(len(modules) == len(set(modules)), 'DUPLICATE_PROBE')
        for module in modules:
            require(isinstance(module, str) and re.fullmatch(r'tests\.test_[a-z0-9_]+', module), 'PROBE_ALLOWLIST')
    return value, sha256(raw)


def modules_for(value):
    return sorted({m for item in value['failure_classes'].values() for m in item['regression_modules']})


def source_contract(root=ROOT):
    """Deliberately restricted source assertions; not a general YAML parser."""
    value, digest = policy(root)
    workflow = (root / '.github/workflows/qikvrt_autonomous_ruleset_effect_loop.yml').read_text()
    # Check the job-level environment BEFORE steps, not an incidental comment
    # or a later step override. Semantic changes require review of this contract.
    job_prefix = workflow.split('    steps:', 1)[0]
    bindings = re.findall(r'^      GH_TOKEN:\s*(.*?)\s*$', job_prefix, re.M)
    require(bindings == ['${{ github.token }}'], 'READ_BOOTSTRAP_DEPENDS_ON_ADMIN')
    require('secrets.QIKVRT_RULESET_ADMIN_TOKEN' not in workflow, 'STATIC_ADMIN_FALLBACK')
    require('QIKVRT_RULESET_ADMIN_TOKEN: ${{ steps.app-token.outputs.token }}' in workflow, 'ADMIN_TOKEN_NOT_EFFECT_SCOPED')
    require('QIKVRT_RULESET_APP_CLIENT_ID' not in workflow, 'STALE_APP_CONFIGURATION_NAME')
    require('app-id: ${{ vars.QIKVRT_RULESET_APP_ID }}' in workflow, 'APP_ID_BINDING')
    require('private-key: ${{ secrets.QIKVRT_RULESET_APP_PRIVATE_KEY }}' in workflow, 'APP_KEY_BINDING')
    require('permission-administration: write' in workflow, 'APP_PERMISSION_BINDING')
    doc = (root / 'docs/operations/GITHUB_RULESET_ADMIN_APP.md').read_text()
    require('QIKVRT_RULESET_APP_ID' in doc and 'QIKVRT_RULESET_APP_CLIENT_ID' not in doc, 'CONFIGURATION_RECIPE_DRIFT')
    require('`QIKVRT ruleset effect dispatch bridge` is the sole' not in doc, 'REMOVED_WORKFLOW_RECIPE')
    require('`QIKVRT required code-owner review`' in doc, 'NATIVE_EVENT_RECIPE_MISSING')
    makefile = (root / 'Makefile').read_text()
    require('test: repair-effectiveness-contract' in makefile, 'REPAIR_TEST_NOT_IN_FULL_SUITE')
    require('tests.test_qikvrt_repair_effectiveness_guard' in makefile, 'REPAIR_TEST_NOT_REGISTERED')
    consumer = (root / '.github/workflows/qikvrt_zero_bug_continuous.yml').read_text()
    require('repair-effectiveness:' in consumer and '--observe-main' in consumer, 'NO_MAIN_EFFECT_CONSUMER')
    require('--source-check' in makefile, 'NO_SOURCE_CONTRACT_CONSUMER')
    for module in modules_for(value):
        require((root / (module.replace('.', '/') + '.py')).is_file(), 'PROBE_MISSING:' + module)
    return {'source_contract': True, 'policy_sha256': digest, 'scope': 'SOURCE_ONLY', 'closed': False}


def classify(snapshot, value):
    """Total fail-closed decision over observer-produced facts, not wire authority.

    Only observe_main constructs production facts from Git, authenticated API
    reads and executed probes. Supplying a JSON object is not authentication.
    """
    def hold(reason):
        return {'schema': SCHEMA, 'state': reason, 'closed': False}
    try:
        require(isinstance(value.get('failure_classes'), dict) and bool(value['failure_classes']), 'EMPTY_REPAIR_REGISTRY')
        require(all(isinstance(c.get('regression_modules'), list) and bool(c['regression_modules']) for c in value['failure_classes'].values()), 'UNPROBED_CLASS')
        require(bool(modules_for(value)), 'EMPTY_PROBE_REGISTRY')
        require(snapshot.get('schema') == SCHEMA and snapshot.get('repository') == REPO, 'INVALID_BINDING')
        head, tree = snapshot.get('head'), snapshot.get('tree')
        require(isinstance(head, str) and SHA.fullmatch(head), 'INVALID_HEAD')
        require(isinstance(tree, str) and SHA.fullmatch(tree), 'INVALID_TREE')
        require(snapshot.get('main_before') == head == snapshot.get('main_after'), 'MAIN_DRIFT_OR_UNOBSERVED')
        require(snapshot.get('source_contract') is True, 'SOURCE_CONTRACT_UNSATISFIED')
        require(snapshot.get('worktree_clean') is True, 'MUTATED_PROBE_CHECKOUT')
        require(snapshot.get('source_after') == {'head': head, 'tree': tree}, 'SOURCE_MUTATED_DURING_PROBES')
        require(isinstance(snapshot.get('policy_sha256'), str) and DIGEST.fullmatch(snapshot['policy_sha256']), 'POLICY_UNBOUND')
        adoption = snapshot.get('adoption', {})
        require(adoption.get('pr') == value['integration_pr'] and type(adoption.get('pr')) is int, 'ADOPTION_SUBJECT')
        require(adoption.get('merged') is True, 'VERIFIED_NOT_EFFECTIVE')
        require(adoption.get('head_is_ancestor') is True and adoption.get('merge_is_ancestor') is True, 'ADOPTION_NOT_IN_MAIN_HISTORY')
        for key in ('head', 'merge_commit'):
            require(isinstance(adoption.get(key), str) and SHA.fullmatch(adoption[key]), 'ADOPTION_SHA_INVALID')
        # This is a causal adoption prerequisite, never a transfer of candidate
        # test results to Main. Main probes below must actually execute afresh.
        review = snapshot.get('adoption_review', {})
        require(review.get('author') == 'Goldkelch' and review.get('state') == 'APPROVED', 'NATIVE_ADOPTION_REVIEW_UNVERIFIED')
        require(type(review.get('id')) is int and review['id'] > 0, 'REVIEW_ID_INVALID')
        require(review.get('commit_id') == adoption['head'], 'REVIEW_ON_PREDECESSOR')
        rules = snapshot.get('ruleset', {})
        require(rules.get('state') == 'CURRENT' and rules.get('mutation') == 'NONE', 'RULESET_NOT_CURRENT')
        require(rules.get('repository') == REPO and rules.get('ruleset_id') == 19344903, 'RULESET_IDENTITY')
        require(isinstance(rules.get('desired_state_sha256'), str) and DIGEST.fullmatch(rules['desired_state_sha256']), 'RULESET_HASH_INVALID')
        require(rules.get('pre_state_sha256') == rules['desired_state_sha256'], 'RULESET_HASH_MISMATCH')
        probes = snapshot.get('probes', {})
        required = modules_for(value)
        require(set(probes) == set(required), 'PROBE_COVERAGE_INCOMPLETE')
        for module in required:
            probe = probes[module]
            require(probe.get('head') == head and probe.get('tree') == tree, 'STALE_PROBE:' + module)
            require(probe.get('status') == 'EXECUTED' and type(probe.get('exit_code')) is int and probe['exit_code'] == 0, 'PROBE_FAILED_OR_NOT_EXECUTED:' + module)
            require(type(probe.get('tests_run')) is int and probe['tests_run'] > 0, 'ZERO_TEST_PROBE:' + module)
            require(isinstance(probe.get('log_sha256'), str) and DIGEST.fullmatch(probe['log_sha256']), 'PROBE_LOG_UNBOUND:' + module)
        return {'schema': SCHEMA, 'state': 'EFFECTIVE_ON_EXACT_MAIN', 'closed': True,
                'head': head, 'tree': tree, 'policy_sha256': snapshot['policy_sha256'],
                'closed_classes': sorted(value['failure_classes']),
                'scope': 'REGISTERED_REPAIR_CLASSES_AT_THIS_OBSERVATION',
                'future_immunity': False, 'publication': False, 'independent_human_review': False}
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return hold(str(exc) if isinstance(exc, ValueError) else 'INVALID_OBSERVATION')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def api(path, token):
    require(bool(token), 'OBSERVATION_TOKEN_UNAVAILABLE')
    require(path.startswith('repos/' + REPO + '/'), 'API_SCOPE')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    request = urllib.request.Request('https://api.github.com/' + path, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'QIKVRT-repair-closure/2'}, method='GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            raw = response.read(2000001)
        require(len(raw) <= 2000000, 'API_RESPONSE_TOO_LARGE')
        return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ValueError('API_READ_HTTP_' + str(exc.code)) from None
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        raise ValueError('API_READ_UNVERIFIED') from None


def observe_main(expected, out, root=ROOT):
    out = out.resolve()
    require(not out.is_relative_to(root.resolve()), 'RECEIPT_MUST_BE_OUTSIDE_SOURCE')
    out.mkdir(parents=True, exist_ok=False)
    value, pd = policy(root)
    s = {'schema': SCHEMA, 'repository': REPO, 'policy_sha256': pd,
         'head': git(root, 'rev-parse', 'HEAD'), 'tree': git(root, 'rev-parse', 'HEAD^{tree}'),
         'probes': {}, 'run_id': os.environ.get('GITHUB_RUN_ID'), 'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}
    token = os.environ.get('GH_TOKEN', '')
    try:
        require(s['head'] == expected, 'EXPECTED_MAIN_MISMATCH')
        require(not git(root, 'status', '--porcelain'), 'DIRTY_SOURCE_BEFORE_PROBES')
        s['main_before'] = api('repos/' + REPO + '/git/ref/heads/main', token)['object']['sha']
        require(s['main_before'] == expected, 'MAIN_CHANGED_BEFORE_PROBES')
        s.update(source_contract(root))
        pull = api(f"repos/{REPO}/pulls/{value['integration_pr']}", token)
        require(pull['base']['repo']['full_name'] == REPO and pull['base']['ref'] == 'main', 'ADOPTION_BASE')
        require(pull['head']['repo']['full_name'] == REPO, 'ADOPTION_REPOSITORY')
        a = {'pr': pull['number'], 'merged': pull['merged'], 'head': pull['head']['sha'], 'merge_commit': pull.get('merge_commit_sha')}
        def ancestor(sha):
            return isinstance(sha, str) and SHA.fullmatch(sha) is not None and subprocess.run(
                ['git', 'merge-base', '--is-ancestor', sha, expected], cwd=root, capture_output=True).returncode == 0
        a['head_is_ancestor'], a['merge_is_ancestor'] = ancestor(a['head']), ancestor(a['merge_commit'])
        s['adoption'] = a
        reviews = api(f"repos/{REPO}/pulls/{value['integration_pr']}/reviews?per_page=100", token)
        require(isinstance(reviews, list) and len(reviews) < 100, 'REVIEW_INVENTORY_INCOMPLETE')
        # No order is inferred from review IDs, timestamps or list position.
        # Ambiguous decisive same-head inventories need a native disposition.
        decisions = [r for r in reviews if r.get('user', {}).get('login') == 'Goldkelch' and r.get('commit_id') == a['head'] and r.get('state') in {'APPROVED','CHANGES_REQUESTED','DISMISSED'}]
        require(len(decisions) <= 1, 'AMBIGUOUS_NATIVE_REVIEW_INVENTORY')
        if decisions:
            r = decisions[0]
            s['adoption_review'] = {'id': r['id'], 'author': r['user']['login'], 'state': r['state'], 'commit_id': r['commit_id']}
        sys.path.insert(0, str(root))
        from tools.qikvrt_ruleset_reconcile import evaluate, load_policy
        s['ruleset'] = evaluate(api(f'repos/{REPO}/rulesets/19344903', token), load_policy(root / 'policy/GITHUB_MAIN_RULESET_V1.json'))
        for module in modules_for(value):
            log = out / (module + '.log')
            try:
                proc = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v', module], cwd=root,
                    capture_output=True, timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1'))
                raw = proc.stdout + proc.stderr
                counts = re.findall(rb'\bRan ([0-9]+) tests? in ', raw)
                p = {'status': 'EXECUTED', 'exit_code': proc.returncode, 'tests_run': int(counts[-1]) if len(counts) == 1 else 0}
            except subprocess.TimeoutExpired as exc:
                raw = (exc.stdout or b'') + (exc.stderr or b'')
                p = {'status': 'TIMEOUT', 'exit_code': None, 'tests_run': 0}
            log.write_bytes(raw)
            p.update(head=s['head'], tree=s['tree'], log_sha256=sha256(raw))
            s['probes'][module] = p
        s['source_after'] = {'head': git(root, 'rev-parse', 'HEAD'), 'tree': git(root, 'rev-parse', 'HEAD^{tree}')}
        s['worktree_clean'] = not git(root, 'status', '--porcelain')
        require(policy(root)[1] == pd, 'POLICY_CHANGED_DURING_PROBES')
        s['main_after'] = api('repos/' + REPO + '/git/ref/heads/main', token)['object']['sha']
        result = classify(s, value)
    except Exception as exc:
        # No network response body, token, private URL or untrusted text is logged.
        result = {'schema': SCHEMA, 'state': 'HOLD_UNVERIFIED', 'closed': False,
                  'first_blocker': str(exc) if type(exc) is ValueError else type(exc).__name__}
    s['result'] = result
    raw = canonical(s)
    (out / 'REPAIR_EFFECTIVENESS.json').write_bytes(raw)
    (out / 'REPAIR_EFFECTIVENESS.json.sha256').write_text(sha256(raw) + '  REPAIR_EFFECTIVENESS.json\n')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['closed'] is True else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source-check', action='store_true')
    mode.add_argument('--observe-main', action='store_true')
    p.add_argument('--expected-main')
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    try:
        if a.source_check:
            print(json.dumps(source_contract(), sort_keys=True))
            return 0
        require(isinstance(a.expected_main, str) and SHA.fullmatch(a.expected_main), 'EXPECTED_MAIN_REQUIRED')
        require(a.out is not None, 'OUTPUT_REQUIRED')
        return observe_main(a.expected_main, a.out)
    except (ValueError, OSError) as exc:
        print('HOLD_UNVERIFIED: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())

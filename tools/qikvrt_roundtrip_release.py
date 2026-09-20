# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Bounded publisher for the explicitly commissioned common HTML publication.

Reuses the existing repository release patterns: exact source, separate
activation, own-repository GITHUB_TOKEN, create-only tag, draft upload, readback.
No policy, main, existing asset, existing tag or other publication is rewritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

REPOS = ('Goldkelch/qik-vrt', 'ingolf-lohmann/qik-vrt')
BRANCH = 'publication/roundtrip-unified-20260920'
TAG = 'qikvrt-roundtrip-2026-09-20-unified'
BUNDLE = 'docs/publications/2026-09-20-qikvrt-roundtrip-unified'
ASSET = 'QIKVRT_Roundtrip.html'
MARKER = 'release/roundtrip-unified-publication-request.json'
SCRIPT = 'tools/qikvrt_roundtrip_release.py'
TITLE = 'QIK-VRT — Erkenntnis, Macht und Verantwortung'
KEYS = {'schema', 'state', 'repository', 'source_commit', 'source_tree',
        'peer_repository', 'peer_commit', 'peer_tree', 'executor_commit',
        'publisher_sha256', 'artifact_sha256', 'artifact_bytes',
        'release_notes_sha256', 'owner_authorization_sha256'}
SHA = re.compile(r'[0-9a-f]{40}\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def require(condition, message):
    if not condition:
        raise RuntimeError('BLOCK: ' + message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args])


def source_bytes(commit, path):
    return git('show', commit + ':' + path)


def validate_shape(m):
    require(set(m) == KEYS, 'closed request schema')
    require(m['schema'] == 'qikvrt_roundtrip_publication_request_v1', 'schema')
    require(m['state'] == 'AUTHORIZE_COMMON_HTML_RELEASE', 'active owner scope')
    require(m['repository'] in REPOS, 'repository allowlist')
    require(m['peer_repository'] in REPOS and m['peer_repository'] != m['repository'], 'peer allowlist')
    for key in ('source_commit', 'source_tree', 'peer_commit', 'peer_tree', 'executor_commit'):
        require(isinstance(m[key], str) and SHA.fullmatch(m[key]), key)
    for key in ('publisher_sha256', 'artifact_sha256', 'release_notes_sha256', 'owner_authorization_sha256'):
        require(isinstance(m[key], str) and SHA256.fullmatch(m[key]), key)
    require(type(m['artifact_bytes']) is int and 0 < m['artifact_bytes'] < 10_000_000, 'static byte budget')


def validate_payload(m, raw, notes, owner):
    require(len(raw) == m['artifact_bytes'] and digest(raw) == m['artifact_sha256'], 'artifact bytes')
    require(digest(notes) == m['release_notes_sha256'], 'release notes bytes')
    require(digest(owner) == m['owner_authorization_sha256'], 'owner instruction bytes')
    decision = json.loads(owner)
    require(decision['actor'] == 'Ingolf Lohmann' and decision['repositories'] == list(REPOS), 'owner scope')
    require(decision['artifact_sha256'] == m['artifact_sha256'] and decision['artifact_bytes'] == len(raw), 'instruction-artifact binding')
    require('diese Freigabe erteile ich hiermit zugleich' in decision['instruction_verbatim'], 'recorded explicit instruction')


def verify_asset(asset, m):
    require(asset.get('name') == ASSET and asset.get('state') == 'uploaded', 'asset identity/state')
    require(asset.get('size') == m['artifact_bytes'], 'asset size')
    require(asset.get('digest') == 'sha256:' + m['artifact_sha256'], 'GitHub asset digest')


class Api:
    def __init__(self, repo, token):
        require(repo in REPOS, 'API repository')
        self.repo, self.token = repo, token

    def call(self, method, path, body=None, missing=False):
        require(path.startswith('/') and '://' not in path, 'API path')
        url = 'https://api.github.com/repos/' + self.repo + path
        headers = {'Accept': 'application/vnd.github+json', 'Authorization': 'Bearer ' + self.token,
                   'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'qikvrt-roundtrip-publication'}
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers['Content-Type'] = 'application/json'
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if missing and error.code == 404:
                return None
            raise RuntimeError('GitHub API ' + method + ' ' + path + ': HTTP ' + str(error.code)) from None

    def upload(self, release_id, raw):
        require(type(release_id) is int and release_id > 0, 'release id')
        url = 'https://uploads.github.com/repos/' + self.repo + '/releases/' + str(release_id) + '/assets?name=' + ASSET
        headers = {'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                   'Content-Type': 'text/html', 'User-Agent': 'qikvrt-roundtrip-publication',
                   'X-GitHub-Api-Version': '2022-11-28'}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=raw, headers=headers, method='POST'), timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError('GitHub asset upload: HTTP ' + str(error.code)) from None


def public_bytes(url):
    # No credential is sent on public reads, including redirects to asset CDN.
    parsed = urllib.parse.urlparse(url)
    require(parsed.scheme == 'https' and parsed.hostname in ('github.com', 'raw.githubusercontent.com', 'api.github.com'), 'public origin')
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'qikvrt-roundtrip-readback'}), timeout=60) as response:
        data = response.read(10_000_001)
        require(len(data) < 10_000_000, 'public read budget')
        return data


def validate_context(m):
    validate_shape(m)
    require(os.environ.get('GITHUB_REPOSITORY') == m['repository'], 'runner repository')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/' + BRANCH, 'runner branch')
    require(os.environ.get('GITHUB_EVENT_NAME') == 'push', 'push activation only')
    head = git('rev-parse', 'HEAD').decode().strip()
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    require(not event.get('forced') and event['after'] == head == os.environ['GITHUB_SHA'], 'non-forced exact event')
    parents = git('show', '-s', '--format=%P', head).decode().split()
    require(parents == [m['executor_commit']] and event['before'] == m['executor_commit'], 'activation parent')
    require(git('show', '-s', '--format=%P', m['executor_commit']).decode().split() == [m['source_commit']], 'source-executor ancestry')
    require(git('rev-parse', m['source_commit'] + '^{tree}').decode().strip() == m['source_tree'], 'source tree')
    changed = set(git('diff', '--name-only', m['executor_commit'], head).decode().splitlines())
    require(changed == {MARKER, 'REPOSITORY_FILE_MANIFEST.json', 'REPOSITORY_FILE_MANIFEST.json.sha256', 'SHA256SUMS.txt'}, 'activation-only delta with canonical integrity')
    require(digest(Path(SCRIPT).read_bytes()) == m['publisher_sha256'], 'publisher binding')
    require(source_bytes(m['executor_commit'], SCRIPT) == Path(SCRIPT).read_bytes(), 'unchanged executor')
    raw = source_bytes(m['source_commit'], BUNDLE + '/' + ASSET)
    notes = source_bytes(m['source_commit'], BUNDLE + '/RELEASE_NOTES.md')
    owner = source_bytes(m['source_commit'], BUNDLE + '/AUTHOR_AUTHORIZATION.json')
    validate_payload(m, raw, notes, owner)
    subprocess.run(['python3', '-B', 'tools/qikvrt_integrity.py', 'verify'], check=True)
    api = Api(m['repository'], os.environ.get('GH_TOKEN', ''))
    require(bool(api.token), 'repository token')
    require(api.call('GET', '/git/ref/heads/' + BRANCH)['object']['sha'] == head, 'current activation head')
    current_main = api.call('GET', '/git/ref/heads/main')['object']['sha']
    # The release source is publication-only and contains no workflow changes.
    # The separately authorized executor never becomes the release target.
    subprocess.run(['git', 'fetch', '--no-tags', 'origin', current_main], check=True)
    require(not git('diff', '--name-only', current_main, m['source_commit'], '--', '.github/workflows').strip(), 'publication source modifies workflows')
    require(api.call('GET', '/git/commits/' + m['source_commit'])['tree']['sha'] == m['source_tree'], 'remote source tree')
    peer_commit = json.loads(public_bytes('https://api.github.com/repos/' + m['peer_repository'] + '/git/commits/' + m['peer_commit']))
    require(peer_commit['tree']['sha'] == m['peer_tree'], 'remote peer tree')
    peer = public_bytes('https://raw.githubusercontent.com/' + m['peer_repository'] + '/' + m['peer_commit'] + '/' + BUNDLE + '/' + ASSET)
    require(peer == raw, 'peer publication byte equality')
    check = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'qikvrt-roundtrip-source'
    require(not check.exists(), 'clean source validation worktree')
    subprocess.run(['git', 'worktree', 'add', '--detach', str(check), m['source_commit']], check=True)
    subprocess.run(['python3', '-B', BUNDLE + '/verify_snapshot.py'], cwd=check, check=True)
    # The personal repository's existing test suite references a historical
    # source commit through its frozen finalizer manifest. Provision that exact
    # Git object when checkout did not contain it; never alter or skip the test.
    historical = check / 'release/observer-relative-retrocausality-current-synthesis-zenodo-v2/publish-request.json'
    if historical.exists():
        fixture = json.loads(historical.read_text()).get('source_head')
        if fixture is not None:
            require(isinstance(fixture, str) and SHA.fullmatch(fixture), 'historical test fixture binding')
            present = subprocess.run(['git', 'cat-file', '-e', fixture + '^{commit}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if present.returncode:
                subprocess.run(['git', 'fetch', '--no-tags', 'origin', fixture], check=True)
            require(git('rev-parse', fixture + '^{commit}').decode().strip() == fixture, 'historical fixture exact object')
    logpath = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'qikvrt-roundtrip-make-test.log'
    with logpath.open('w') as log:
        result = subprocess.run(['make', 'test'], cwd=check, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print('\n'.join(logpath.read_text(errors='replace').splitlines()[-100:]))
    require(result.returncode == 0, 'fresh full source test')
    require(not git('status', '--porcelain', '--untracked-files=no').strip(), 'executor worktree unchanged')
    return api, head, raw, notes.decode()


def publish(m):
    api, head, raw, notes = validate_context(m)
    # All validation and peer-byte observation precede the first external write.
    require(api.call('GET', '/git/ref/heads/' + BRANCH)['object']['sha'] == head, 'head before effect')
    tag = api.call('GET', '/git/ref/tags/' + TAG, missing=True)
    if tag is None:
        api.call('POST', '/git/refs', {'ref': 'refs/tags/' + TAG, 'sha': m['source_commit']})
        tag = api.call('GET', '/git/ref/tags/' + TAG)
    require(tag['object']['type'] == 'commit' and tag['object']['sha'] == m['source_commit'], 'create-only exact tag')
    release = api.call('GET', '/releases/tags/' + TAG, missing=True)
    if release is None:
        # Authenticated listings include a draft left by an interrupted upload.
        drafts = [r for r in api.call('GET', '/releases?per_page=100') if r['tag_name'] == TAG]
        require(len(drafts) <= 1, 'unique release identity')
        release = drafts[0] if drafts else None
    if release is None:
        release = api.call('POST', '/releases', {'tag_name': TAG, 'target_commitish': m['source_commit'], 'name': TITLE,
                                              'body': notes, 'draft': True, 'prerelease': False, 'make_latest': 'false'})
    require(release['name'] == TITLE and release['body'] == notes and not release['prerelease'], 'existing release metadata conflict')
    assets = api.call('GET', '/releases/' + str(release['id']) + '/assets?per_page=100')
    require(len(assets) <= 1 and all(a['name'] == ASSET for a in assets), 'unexpected assets')
    if assets:
        verify_asset(assets[0], m)
    else:
        require(release['draft'], 'published release without authorized asset')
        verify_asset(api.upload(release['id'], raw), m)
    if release['draft']:
        require(api.call('GET', '/git/ref/heads/' + BRANCH)['object']['sha'] == head, 'head before publication')
        release = api.call('PATCH', '/releases/' + str(release['id']), {'draft': False, 'make_latest': 'false'})
    public = json.loads(public_bytes('https://api.github.com/repos/' + m['repository'] + '/releases/tags/' + TAG))
    require(not public['draft'] and public['tag_name'] == TAG and public['body'] == notes, 'public release identity')
    require(len(public['assets']) == 1, 'public asset count')
    asset = public['assets'][0]
    verify_asset(asset, m)
    expected_url = 'https://github.com/' + m['repository'] + '/releases/download/' + TAG + '/' + ASSET
    require(asset['browser_download_url'] == expected_url, 'public asset location')
    require(public_bytes(expected_url) == raw, 'public asset byte-exact readback')
    receipt = {'schema': 'qikvrt_roundtrip_release_readback_v1', 'repository': m['repository'], 'source_commit': m['source_commit'],
               'source_tree': m['source_tree'], 'activation_commit': head, 'release_url': public['html_url'], 'asset_url': expected_url,
               'artifact_bytes': len(raw), 'artifact_sha256': digest(raw), 'peer_source_commit': m['peer_commit'],
               'peer_html_identical': True, 'public_readback': 'PASS', 'release_published': True,
               'main_adoption': 'NOT_CLAIMED', 'whole_repository_equality': 'NOT_CLAIMED'}
    out = Path('.qikvrt/runtime/roundtrip-release-readback.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    request = json.loads(Path(MARKER).read_text())
    if request.get('state') == 'PREPARED_INACTIVE':
        print('PREPARED_INACTIVE: no publication effect')
    elif args.publish:
        publish(request)
    else:
        validate_shape(request)
        print('Request shape valid; publication not executed')

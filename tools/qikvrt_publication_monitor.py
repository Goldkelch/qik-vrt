#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded public GET collector and recoverable publication-monitor state machine.

Code and policy are versioned on the reviewed source branch. Mutable observations
live on the explicitly named data-only Git ref. No credentials are accepted by
the public collector. Git persistence is a separate authorized runner operation.
A local snapshot, successful GET, or queued outbox event is not a delivered alert.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import fcntl
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse as urlparse
import urllib.request as request
import xml.etree.ElementTree as ET

STATE_SCHEMA = 'qikvrt.publication-monitor.state.v1'
MONITOR_ID = 'qikvrt-publication-discovery-v1'
PLATFORMS = ('zenodo', 'arxiv', 'wikimedia', 'cratesio')
STATE_PATH = Path('monitor/state.json')
HEX = re.compile(r'^[0-9a-f]{64}$')
CRATE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
ARXIV_ID = re.compile(r'^(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+/\d{7})v[1-9]\d*$')


class MonitorError(RuntimeError):
    """Fail closed; never substitute an empty inventory for a failed read."""


class ReadError(MonitorError):
    def __init__(self, reason: str, status: int | None = None, evidence: dict | None = None):
        super().__init__(reason)
        self.status, self.evidence = status, evidence


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise MonitorError('Timestamp must include a timezone')
    return parsed


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(value) -> str:
    return digest(canonical(value))


def load_json(data: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise MonitorError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise MonitorError('Non-finite JSON number')
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise MonitorError(reason)


def integer(value, label: str) -> int:
    require(type(value) is int and value >= 0, 'Invalid ' + label)
    return value


def total(value) -> int:
    if isinstance(value, dict):
        require(value.get('relation') == 'eq', 'Non-exact total')
        value = value.get('value')
    return integer(value, 'total')


def dictionary(value, label: str) -> dict:
    require(isinstance(value, dict), 'Missing object: ' + label)
    return value


def seq(value, label: str) -> list:
    require(isinstance(value, list), 'Missing array: ' + label)
    return value


def ordered(items: list) -> list:
    return sorted(items, key=canonical)


def pick(obj: dict, fields: str) -> dict:
    return {key: obj.get(key) for key in fields.split()}


def safe_read(path: Path) -> bytes:
    require(all(not parent.is_symlink() for parent in (path, *path.parents)), 'Refuse symlink path')
    require(path.is_file(), 'STATE_UNAVAILABLE: ' + str(path))
    require(path.stat().st_size <= 64 * 1024 * 1024, 'Oversize local state')
    return path.read_bytes()


def atomic_write(path: Path, data: bytes) -> None:
    require(all(not parent.is_symlink() for parent in (path, *path.parents)), 'Refuse symlink path')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def validate_policy(policy: dict) -> None:
    require(policy.get('schema') == 'qikvrt.publication-monitor.policy.v1', 'Unknown policy')
    require(policy.get('monitor_id') == MONITOR_ID, 'Wrong monitor')
    require(policy.get('repository') == 'Goldkelch/qik-vrt', 'Wrong Authority')
    require(policy.get('state_ref') == 'qikvrt/publication-monitor-state-v1', 'Wrong state ref')
    require(policy.get('state_path') == STATE_PATH.as_posix(), 'Wrong state path')
    require(policy.get('external_methods') == ['GET'], 'Public writes forbidden')
    require(set(policy['queries']) == set(PLATFORMS), 'Incomplete platform policy')
    require(set(policy['queries']['cratesio']) == {'qik-vrt', 'qikvrt', 'temdd', 'cloud-transputer'}, 'Baseline scope drift')
    for host in policy['wiki_sites']:
        require(host in {'en.wikipedia.org', 'de.wikipedia.org', 'commons.wikimedia.org'}, 'Unapproved wiki')


def genesis(policy: dict, provenance: dict) -> dict:
    validate_policy(policy)
    return {
        'schema': STATE_SCHEMA, 'monitor_id': MONITOR_ID,
        'policy_sha256': fingerprint(policy), 'generation': 0,
        'previous_state_sha256': None, 'source': provenance,
        'platforms': {name: {
            'baseline_established': name == 'cratesio', 'subjects': {},
            'queries': copy.deepcopy(policy['genesis']['cratesio']) if name == 'cratesio' else {},
            'last_attempt': None, 'health': 'NOT_YET_OBSERVED',
        } for name in PLATFORMS},
        'migration': copy.deepcopy(policy['migration']),
        'outbox': {}, 'acknowledged_events': {},
        'boundary': 'ONLY_PUBLIC_PLATFORM_STATE; NO_GENERAL_EFFECT_ACK_DONE',
    }


def validate_state(state: dict, policy: dict) -> None:
    require(state.get('schema') == STATE_SCHEMA and state.get('monitor_id') == MONITOR_ID, 'Wrong state identity')
    require(state.get('policy_sha256') == fingerprint(policy), 'POLICY_DRIFT: reviewed migration required')
    integer(state.get('generation'), 'generation')
    require(set(state.get('platforms', {})) == set(PLATFORMS), 'Missing platform state')
    dictionary(state.get('outbox'), 'outbox')
    dictionary(state.get('acknowledged_events'), 'acknowledged events')
    for name, platform in state['platforms'].items():
        require(type(platform.get('baseline_established')) is bool, 'Invalid baseline flag')
        for key, item in dictionary(platform.get('subjects'), name + ' subjects').items():
            require(isinstance(key, str) and item.get('fingerprint') == fingerprint(item['canonical']), 'Corrupt subject fingerprint')
            require(type(item.get('available')) is bool, 'Invalid availability')
            integer(item.get('revision'), 'revision')
            require(item['evidence']['evidence_class'] == 'PUBLIC_READBACK', 'Historical report cannot be last-good state')



def validate_store(store: Path, state: dict, policy: dict) -> None:
    """Validate persisted bytes, current/predecessor history and referenced GETs.

    Git's exact commit/tree remains the outside anchor. This check does not
    pretend that a self-contained writable hash chain authenticates its writer.
    """
    validate_state(state, policy)
    raw = safe_read(store / STATE_PATH)
    require(raw == canonical(state), 'Noncanonical or changed state bytes')
    history = store / 'monitor/history'
    current = history / ('%012d-%s.json' % (state['generation'], digest(raw)))
    require(safe_read(current) == raw, 'Current immutable snapshot missing or changed')
    if state['generation']:
        previous = state.get('previous_state_sha256')
        require(isinstance(previous, str) and HEX.fullmatch(previous) is not None, 'Missing predecessor hash')
        prior = history / ('%012d-%s.json' % (state['generation'] - 1, previous))
        prior_raw = safe_read(prior)
        require(digest(prior_raw) == previous, 'Predecessor snapshot changed')
        require(load_json(prior_raw).get('generation') == state['generation'] - 1, 'Wrong predecessor generation')
    else:
        require(state['previous_state_sha256'] is None, 'Genesis has a predecessor')
    checked = set()
    def check(value):
        if isinstance(value, dict):
            if 'response_sha256' in value:
                sha = value['response_sha256']
                require(isinstance(sha, str) and HEX.fullmatch(sha) is not None, 'Invalid raw-response hash')
                expected = 'monitor/responses/' + sha + '.body'
                require(value.get('response_path') == expected, 'Missing or escaped response path')
                require(value.get('method') == 'GET', 'Wrong recorded method')
                allowed_url(value['url'])
                if sha not in checked:
                    require(digest(safe_read(store / expected)) == sha, 'Raw public response missing or changed')
                    checked.add(sha)
            for item in value.values():
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    check(state)
    require(not (set(state['outbox']) & set(state['acknowledged_events'])), 'Event both pending and acknowledged')
    for ident, item in list(state['outbox'].items()) + [(i, v['event']) for i, v in state['acknowledged_events'].items()]:
        require(ident == item['event_id'] == fingerprint({k: item[k] for k in ('platform', 'subject', 'revision', 'old', 'new')}), 'Corrupt outbox event')



def subject_view(item: dict | None):
    return None if item is None else {'available': item['available'], 'state': item['canonical']}


class Ledger:
    def __init__(self, state: dict, policy: dict, now: str):
        validate_state(state, policy)
        parse_time(now)
        self.state, self.policy, self.now = copy.deepcopy(state), policy, now
        self.errors: dict[str, list] = {name: [] for name in PLATFORMS}

    def event(self, platform: str, key: str, before: dict | None, after: dict, proof: dict) -> None:
        old, new = subject_view(before), subject_view(after)
        if old == new:
            return
        entry = {'platform': platform, 'subject': key, 'revision': after['revision'],
                 'old': old, 'new': new, 'observed_at': proof.get('observed_at', self.now),
                 'platform_updated_at': after['canonical'].get('updated', after['canonical'].get('updated_at')),
                 'evidence_class': 'PUBLIC_READBACK', 'evidence': proof,
                 'smallest_safe_action': 'Read the exact official subject and compare identity/version bindings; do not mutate the platform.'}
        identifier = fingerprint({k: entry[k] for k in ('platform', 'subject', 'revision', 'old', 'new')})
        entry['event_id'] = identifier
        if identifier not in self.state['acknowledged_events']:
            self.state['outbox'].setdefault(identifier, entry)

    def accept(self, platform: str, key: str, value: dict, evidence: dict) -> None:
        require(evidence.get('evidence_class') == 'PUBLIC_READBACK' and evidence.get('method') == 'GET', 'Unverified observation')
        require(evidence.get('status') == 200 and HEX.fullmatch(evidence.get('response_sha256', '')) is not None, 'Missing public byte binding')
        p = self.state['platforms'][platform]
        previous = p['subjects'].get(key)
        if previous:
            require(parse_time(evidence['observed_at']) >= parse_time(previous['last_success_at']), 'Stale subject observation')
        h = fingerprint(value)
        changed = previous is None or previous['fingerprint'] != h or not previous['available']
        current = {
            'canonical': value, 'fingerprint': h, 'available': True,
            'revision': (previous['revision'] if previous else 0) + int(changed),
            'last_success_at': evidence['observed_at'], 'evidence': evidence,
        }
        p['subjects'][key] = current
        # Recovery observations establish a missing baseline silently. A known
        # verified subject may still undergo a real transition during recovery.
        if previous is not None or p['baseline_established']:
            self.event(platform, key, previous, current, evidence)

    def failure(self, platform: str, key: str, error: Exception, inventory_ok: bool = False) -> None:
        status = error.status if isinstance(error, ReadError) else None
        evidence = error.evidence if isinstance(error, ReadError) else None
        self.errors[platform].append({'subject': key, 'reason': str(error)[:200], 'http_status': status, 'evidence': evidence})
        current = self.state['platforms'][platform]['subjects'].get(key)
        # A timeout, schema failure, quota response or lost tool route NEVER
        # means disappearance. Only repeated official 404/410 with a successful
        # platform inventory in this run can change a prior public availability.
        if current is None or status not in (404, 410) or not evidence or not inventory_ok:
            return
        expected_url = None
        if platform == 'zenodo' and key.startswith('record:'):
            expected_url = 'https://zenodo.org/api/records/' + key.split(':', 1)[1]
        elif platform == 'cratesio':
            expected_url = 'https://crates.io/api/v1/crates/' + key.split(':', 1)[1].split('@', 1)[0]
        if evidence.get('url') != expected_url or expected_url is None:
            return
        previous_pending = current.get('pending_absence')
        if (previous_pending and previous_pending['status'] == status
                and (parse_time(self.now) - parse_time(previous_pending['observed_at'])).total_seconds() >= 60):
            if current['available']:
                old = copy.deepcopy(current)
                current['available'] = False
                current['revision'] += 1
                current['absence_evidence'] = [previous_pending, evidence]
                self.event(platform, key, old, current, {'confirmations': current['absence_evidence'], 'predicate': 'EXACT_ENDPOINT_REPEATED_OFFICIAL_HTTP_' + str(status)})
        elif not previous_pending:
            current['pending_absence'] = evidence

    def finish(self, platform: str, queries: dict | None) -> None:
        p = self.state['platforms'][platform]
        p['last_attempt'] = self.now
        p['health'] = 'READ_FAILED_PRESERVED_LAST_GOOD' if self.errors[platform] else 'OBSERVED'
        p['errors'] = self.errors[platform]
        p.pop('retry_not_before', None)
        for error in self.errors[platform]:
            ev = error.get('evidence') or {}
            delay = ev.get('retry_after')
            if not delay:
                continue
            try:
                until = (parse_time(ev['observed_at']) + dt.timedelta(seconds=int(delay))) if str(delay).isdigit() else parsedate_to_datetime(delay)
                if until.tzinfo is None:
                    continue
                value = until.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
                if parse_time(value) > parse_time(p.get('retry_not_before', self.now)):
                    p['retry_not_before'] = value
            except (TypeError, ValueError, OverflowError):
                pass
        if queries is not None:
            p['queries'] = {'canonical': queries, 'observed_at': self.now}
            if not self.errors[platform]:
                p['baseline_established'] = True


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def allowed_url(url: str) -> str:
    p = urlparse.urlsplit(url)
    require(p.scheme == 'https' and p.username is None and p.password is None
            and p.port in (None, 443) and not p.fragment, 'Unapproved public URL')
    args = urlparse.parse_qs(p.query, strict_parsing=True) if p.query else {}
    host, path = p.hostname, p.path
    if host == 'zenodo.org':
        good = bool(re.fullmatch(r'/api/records(?:/[1-9][0-9]*)?', path))
        permitted = {'q', 'page', 'size', 'sort', 'all_versions'}
    elif host == 'crates.io':
        good = bool(re.fullmatch(r'/api/v1/crates(?:/[A-Za-z0-9_-]+(?:/owners|/versions)?)?', path))
        permitted = {'q', 'page', 'per_page', 'sort'}
    elif host == 'export.arxiv.org':
        good = path == '/api/query'
        permitted = {'search_query', 'id_list', 'start', 'max_results', 'sortBy', 'sortOrder'}
    elif host in {'en.wikipedia.org', 'de.wikipedia.org', 'commons.wikimedia.org', 'www.wikidata.org'}:
        good = path == '/w/api.php' and args.get('action') in (['query'], ['wbsearchentities'])
        permitted = {'action', 'format', 'formatversion', 'prop', 'titles', 'redirects', 'rvprop', 'rvlimit', 'inprop', 'search', 'language', 'limit', 'continue'}
    else:
        good, permitted = False, set()
    require(good and set(args) <= permitted and all(len(v) == 1 for v in args.values()), 'Unapproved read endpoint or parameter')
    return url


class PublicGET:
    """No token parameter, no cookie handler, no secret environment lookup."""
    def __init__(self, policy: dict, store: Path):
        self.limits, self.store = policy['limits'], store
        self.count = 0
        self.deadline = time.monotonic() + self.limits['deadline_seconds']
        self.last_by_host: dict[str, float] = {}
        self.opener = request.build_opener(NoRedirect())

    def read(self, url: str, xml: bool = False):
        allowed_url(url)
        require(time.monotonic() < self.deadline, 'Read deadline reached; retain baseline')
        self.count += 1
        require(self.count <= self.limits['requests'], 'Bounded request budget exhausted')
        host = urlparse.urlsplit(url).hostname
        pause = self.limits['arxiv_pacing_seconds'] if host == 'export.arxiv.org' else self.limits['pacing_seconds']
        time.sleep(max(0, self.last_by_host.get(host, 0) + pause - time.monotonic()))
        self.last_by_host[host] = time.monotonic()
        req = request.Request(url, method='GET', headers={
            'User-Agent': 'QIKVRT-publication-monitor/1.0 (https://github.com/Goldkelch/qik-vrt)',
            'Accept': 'application/atom+xml' if xml else 'application/json',
            'Accept-Encoding': 'identity',
        })
        try:
            response = self.opener.open(req, timeout=max(0.1, min(self.limits['timeout_seconds'], self.deadline - time.monotonic())))
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, urllib.error.URLError) as exc:
            raise ReadError('TRANSPORT_' + type(exc).__name__) from None
        try:
            with response:
                require(response.geturl() == url, 'Unexpected redirect')
                raw = response.read(self.limits['json_bytes'] + 1)
                status = response.code
                content_type = response.headers.get('Content-Type', '').split(';')[0].lower()
                retry_after = response.headers.get('Retry-After')
        except (OSError, http.client.HTTPException) as exc:
            raise ReadError('TRANSPORT_BODY_' + type(exc).__name__) from None
        require(len(raw) <= self.limits['json_bytes'], 'Public response too large')
        sha = digest(raw)
        raw_path = self.store / 'monitor' / 'responses' / (sha + '.body')
        if raw_path.exists():
            require(safe_read(raw_path) == raw, 'Response digest collision')
        else:
            atomic_write(raw_path, raw)
        proof = {'method': 'GET', 'url': url, 'status': status,
                 'observed_at': utc(), 'response_sha256': sha,
                 'response_path': raw_path.relative_to(self.store).as_posix(),
                 'content_type': content_type, 'evidence_class': 'PUBLIC_READBACK'}
        if retry_after:
            proof['retry_after'] = retry_after[:80]
        if status != 200:
            raise ReadError('OFFICIAL_HTTP_' + str(status), status, proof)
        try:
            if xml:
                require(content_type in ('application/atom+xml', 'application/xml', 'text/xml'), 'Wrong XML content type')
                require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'XML entities forbidden')
                value = ET.fromstring(raw)
            else:
                require(content_type == 'application/json', 'Wrong JSON content type')
                value = load_json(raw)
        except (ValueError, ET.ParseError, MonitorError) as exc:
            raise ReadError('SCHEMA_' + type(exc).__name__, status, proof) from None
        return value, proof


def endpoint(base: str, **params) -> str:
    return base + ('?' + urlparse.urlencode(params) if params else '')


def paged_json(client, base: str, params: dict, family: str, limit: int) -> tuple[list, list]:
    items, proofs, seen, expected = [], [], set(), None
    for page in range(1, limit + 1):
        args = {**params, 'page': page, ('per_page' if family == 'cratesio' else 'size'): 100}
        value, proof = client.read(endpoint(base, **args))
        dictionary(value, family)
        container = dictionary(value['meta'] if family == 'cratesio' else value['hits'], 'inventory metadata')
        count = total(container['total'])
        require(expected is None or count == expected, 'Inventory moved while paging')
        expected = count
        batch = seq(value['crates'] if family == 'cratesio' else value['hits']['hits'], 'inventory')
        for item in batch:
            key = str(item['id'])
            require(key not in seen, 'Duplicate inventory entry')
            seen.add(key)
            items.append(item)
        proofs.append(proof)
        require(len(items) <= expected, 'Inventory exceeded declared total')
        if len(items) == expected:
            return items, proofs
        require(bool(batch), 'Truncated inventory')
    raise MonitorError('Pagination bound exceeded; incomplete inventory')


def zenodo_record(value: dict, record_id: str) -> dict:
    require(str(value.get('id')) == record_id, 'Zenodo record identity mismatch')
    metadata = dictionary(value.get('metadata'), 'Zenodo metadata')
    require(isinstance(metadata.get('title'), str) and bool(metadata['title']), 'Missing title')
    creators = seq(metadata.get('creators'), 'creators')
    files = []
    names = set()
    for file in seq(value.get('files'), 'Zenodo files'):
        key = file.get('key')
        require(isinstance(key, str) and key not in names, 'Invalid/duplicate public file key')
        names.add(key)
        checksum = file.get('checksum')
        require(isinstance(checksum, str) and re.fullmatch(r'(?:md5:[0-9a-f]{32}|sha256:[0-9a-f]{64})', checksum) is not None, 'Invalid publisher file checksum')
        integer(file.get('size'), 'file size')
        files.append(pick(file, 'key size checksum id version_id links'))
    return {'record_id': record_id, 'doi': value.get('doi'),
            'concept_id': value.get('conceptrecid'), 'concept_doi': value.get('conceptdoi'),
            'version': metadata.get('version'), 'title': metadata['title'],
            'description': metadata.get('description'), 'language': metadata.get('language'),
            'keywords': ordered(metadata.get('keywords', [])),
            'access_conditions': metadata.get('access_conditions'), 'embargo_date': metadata.get('embargo_date'),
            'creators': creators, 'owners': ordered(seq(value.get('owners', []), 'owners')),
            'created': value.get('created'), 'updated': value.get('updated'),
            'publication_date': metadata.get('publication_date'),
            'license': metadata.get('license'), 'access_right': metadata.get('access_right'),
            'resource_type': metadata.get('resource_type'), 'related_identifiers': ordered(metadata.get('related_identifiers', [])),
            'relations': value.get('relations'), 'status': value.get('status'),
            'files': sorted(files, key=lambda f: f['key']),
            'public_url': 'https://zenodo.org/records/' + record_id,
            'file_evidence_scope': 'PUBLISHER_METADATA_NOT_FRESH_FILE_REDOWNLOAD'}


def collect_zenodo(client, ledger: Ledger):
    queries, ids = {}, set(ledger.policy['zenodo_known_ids'])
    for key in ledger.state['platforms']['zenodo']['subjects']:
        if key.startswith('record:'):
            ids.add(key.split(':', 1)[1])
    healthy = True
    for query in ledger.policy['queries']['zenodo']:
        try:
            items, proofs = paged_json(client, 'https://zenodo.org/api/records', {'q': query, 'all_versions': 'true', 'sort': 'mostrecent'}, 'zenodo', ledger.policy['limits']['pages'])
            query_ids = sorted(str(item['id']) for item in items)
            queries[query] = {'ids': query_ids, 'evidence': proofs}
            ids.update(query_ids)
        except (MonitorError, KeyError, TypeError, ValueError) as exc:
            healthy = False
            ledger.failure('zenodo', 'query:' + query, exc)
    for rid in sorted(ids):
        key = 'record:' + rid
        try:
            data, proof = client.read('https://zenodo.org/api/records/' + rid)
            ledger.accept('zenodo', key, zenodo_record(data, rid), proof)
        except (MonitorError, KeyError, TypeError, ValueError) as exc:
            ledger.failure('zenodo', key, exc, healthy)
    ledger.finish('zenodo', queries if healthy else None)


def relevant_crate(value: dict) -> bool:
    name = re.sub(r'[-_]', '', str(value.get('id', '')).lower())
    if any(term in name for term in ('qikvrt', 'temdd', 'cloudtransputer')):
        return True
    text = ' '.join(str(value.get(key) or '') for key in ('description', 'repository', 'homepage', 'documentation'))
    return bool(re.search(r'(?i)(?<![A-Za-z0-9])(?:qik[-_]?vrt|temdd|cloud[-_ ]transputer)(?![A-Za-z0-9])', text))


def crate_subjects(data: dict, owner_data: dict, name: str) -> dict:
    crate = dictionary(data.get('crate'), 'crate')
    require(crate.get('id') == name, 'Crate identity mismatch')
    owners = seq(owner_data.get('users'), 'crate owners')
    owners = ordered([pick(dictionary(o, 'owner'), 'id login name kind url') for o in owners])
    require(all(type(o['id']) is int and isinstance(o['login'], str) for o in owners), 'Incomplete owner identity')
    versions = seq(data.get('versions'), 'crate versions')
    version_ids = seq(crate.get('versions'), 'complete version identifiers')
    require(all(type(v) is int and v > 0 for v in version_ids), 'Invalid crate version ID')
    require(len(set(version_ids)) == len(version_ids), 'Duplicate crate version ID')
    require(set(version_ids) == {v.get('id') for v in versions} and len(versions) == len(version_ids), 'Incomplete crate version readback')
    results = {'crate:' + name: {**pick(crate, 'id name description repository homepage documentation created_at updated_at max_version newest_version max_stable_version'), 'owners': owners, 'public_url': 'https://crates.io/crates/' + name}}
    for version in versions:
        require(version.get('crate') == name and type(version.get('yanked')) is bool, 'Crate version binding/yank flag invalid')
        require(type(version.get('id')) is int and isinstance(version.get('num'), str), 'Missing exact version')
        key = 'version:' + name + '@' + version['num']
        require(key not in results, 'Duplicate semantic version')
        results[key] = {**pick(version, 'id crate num yanked checksum created_at updated_at license rust_version repository homepage documentation'), 'public_url': 'https://crates.io/crates/' + name + '/' + version['num']}
    return results


def collect_crates(client, ledger: Ledger):
    queries, names, healthy = {}, set(), True
    previous = ledger.state['platforms']['cratesio']['subjects']
    for key in previous:
        if key.startswith('crate:'):
            names.add(key.split(':', 1)[1])
    for query in ledger.policy['queries']['cratesio']:
        try:
            items, proofs = paged_json(client, 'https://crates.io/api/v1/crates', {'q': query}, 'cratesio', ledger.policy['limits']['pages'])
            queries[query] = {'count': len(items), 'relevant': sorted(v['id'] for v in items if relevant_crate(v)), 'evidence': proofs}
            names.update(queries[query]['relevant'])
        except (MonitorError, KeyError, TypeError, ValueError) as exc:
            healthy = False
            ledger.failure('cratesio', 'query:' + query, exc)
    for name in sorted(names):
        try:
            require(CRATE.fullmatch(name) is not None, 'Invalid crate name')
            data, proof = client.read('https://crates.io/api/v1/crates/' + name)
            owners, owner_proof = client.read('https://crates.io/api/v1/crates/' + name + '/owners')
            subjects = crate_subjects(data, owners, name)
            proof = {**proof, 'owner_readback': owner_proof}
            for key, value in subjects.items():
                ledger.accept('cratesio', key, value, proof)
            # Missing from a complete ID list is an exact public transition,
            # unlike missing from a search query or an incomplete version page.
            for key in sorted(set(previous) - set(subjects)):
                if key.startswith('version:' + name + '@'):
                    old = copy.deepcopy(previous[key])
                    if old['available']:
                        previous[key]['available'] = False
                        previous[key]['revision'] += 1
                        previous[key]['absence_evidence'] = proof
                        ledger.event('cratesio', key, old, previous[key], {'predicate': 'ABSENT_FROM_COMPLETE_PUBLIC_VERSION_ID_LIST', 'readback': proof})
        except (MonitorError, KeyError, TypeError, ValueError) as exc:
            # Preserve each version separately if the crate endpoint fails.
            keys = [k for k in previous if k == 'crate:' + name or k.startswith('version:' + name + '@')]
            for key in keys or ['crate:' + name]:
                ledger.failure('cratesio', key, exc, healthy)
    ledger.finish('cratesio', queries if healthy else None)


ATOM = '{http://www.w3.org/2005/Atom}'
OS = '{http://a9.com/-/spec/opensearch/1.1/}'
AX = '{http://arxiv.org/schemas/atom}'


def arxiv_entries(root: ET.Element) -> tuple[int, list]:
    require(root.tag == ATOM + 'feed', 'Not an Atom feed')
    count = root.findtext(OS + 'totalResults')
    require(count is not None and count.isdecimal(), 'Missing exact arXiv total')
    items = []
    for element in root.findall(ATOM + 'entry'):
        ident = element.findtext(ATOM + 'id', '')
        p = urlparse.urlsplit(ident)
        require(p.hostname == 'arxiv.org' and p.path.startswith('/abs/'), 'arXiv error or wrong ID origin')
        version_id = p.path.removeprefix('/abs/')
        require(ARXIV_ID.fullmatch(version_id) is not None, 'Missing exact arXiv version')
        items.append({'version_id': version_id, 'public_url': 'https://arxiv.org/abs/' + version_id,
                      'title': ' '.join(element.findtext(ATOM + 'title', '').split()),
                      'summary': ' '.join(element.findtext(ATOM + 'summary', '').split()),
                      'authors': [a.findtext(ATOM + 'name') for a in element.findall(ATOM + 'author')],
                      'published': element.findtext(ATOM + 'published'), 'updated': element.findtext(ATOM + 'updated'),
                      'doi': element.findtext(AX + 'doi'), 'journal_ref': element.findtext(AX + 'journal_ref'),
                      'categories': sorted(c.get('term') for c in element.findall(ATOM + 'category'))})
    return int(count), items


def collect_arxiv(client, ledger: Ledger):
    queries, found, healthy = {}, {}, True
    for query in ledger.policy['queries']['arxiv']:
        try:
            ids, expected, proofs = set(), None, []
            for page in range(ledger.policy['limits']['pages']):
                root, proof = client.read(endpoint('https://export.arxiv.org/api/query', search_query=query, start=page * 100, max_results=100), xml=True)
                count, items = arxiv_entries(root)
                require(expected is None or expected == count, 'arXiv inventory moved')
                expected = count
                for item in items:
                    require(item['version_id'] not in ids, 'Duplicate arXiv entry')
                    ids.add(item['version_id'])
                    found[item['version_id']] = (item, proof)
                proofs.append(proof)
                if len(ids) == count:
                    break
                require(items and len(ids) < count, 'Incomplete arXiv inventory')
            else:
                raise MonitorError('arXiv pagination exceeded')
            queries[query] = {'ids': sorted(ids), 'evidence': proofs}
        except (MonitorError, KeyError, TypeError, ValueError) as exc:
            healthy = False
            ledger.failure('arxiv', 'query:' + query, exc)
    # Explicit old versions remain independently queried, even when search only
    # exposes a newer version. Search omission is never deletion evidence.
    for key in ledger.state['platforms']['arxiv']['subjects']:
        ident = key.removeprefix('version:')
        if ident not in found:
            try:
                root, proof = client.read(endpoint('https://export.arxiv.org/api/query', id_list=ident, max_results=1), xml=True)
                count, entries = arxiv_entries(root)
                require(count == 1 and len(entries) == 1 and entries[0]['version_id'] == ident, 'Historical arXiv version not independently resolved')
                found[ident] = (entries[0], proof)
            except (MonitorError, KeyError, TypeError, ValueError) as exc:
                ledger.failure('arxiv', key, exc, healthy)
    for ident, (value, proof) in sorted(found.items()):
        ledger.accept('arxiv', 'version:' + ident, value, proof)
    ledger.finish('arxiv', queries if healthy else None)


def wiki_page(value: dict, title: str) -> dict:
    require('error' not in value and 'continue' not in value, 'MediaWiki error or continuation')
    pages = seq(dictionary(value.get('query'), 'wiki query').get('pages'), 'wiki pages')
    require(len(pages) == 1, 'Ambiguous wiki result')
    page = dictionary(pages[0], 'wiki page')
    require('invalid' not in page and isinstance(page.get('title'), str), 'Invalid wiki title')
    if 'missing' in page:
        require(page['missing'] is True, 'Invalid missing flag')
        return {'requested_title': title, 'resolved_title': page['title'], 'exists': False}
    require(type(page.get('pageid')) is int and page['pageid'] > 0, 'Missing page identity')
    revisions = seq(page.get('revisions'), 'wiki revisions')
    require(len(revisions) == 1 and type(revisions[0].get('revid')) is int, 'Missing exact wiki revision')
    return {'requested_title': title, 'exists': True,
            **pick(page, 'title pageid ns fullurl lastrevid'), 'revision': pick(revisions[0], 'revid parentid timestamp sha1'),
            'redirects': value['query'].get('redirects', []), 'normalized': value['query'].get('normalized', [])}


def collect_wikimedia(client, ledger: Ledger):
    queries = {}
    for host in ledger.policy['wiki_sites']:
        for title in ledger.policy['queries']['wikimedia']:
            key = host + ':' + title
            try:
                data, proof = client.read(endpoint('https://' + host + '/w/api.php', action='query', format='json', formatversion=2, prop='info|revisions', titles=title, redirects=1, rvprop='ids|timestamp|sha1', rvlimit=1, inprop='url'))
                ledger.accept('wikimedia', key, wiki_page(data, title), proof)
                queries[key] = {'evidence': proof}
            except (MonitorError, KeyError, TypeError, ValueError) as exc:
                ledger.failure('wikimedia', key, exc)
    for language in ledger.policy['wikidata_search_languages']:
        for query in ledger.policy['queries']['wikimedia']:
            key = 'wikidata:' + language + ':' + query
            try:
                data, proof = client.read(endpoint('https://www.wikidata.org/w/api.php', action='wbsearchentities', format='json', search=query, language=language, limit=50))
                require(data.get('success') == 1 and 'error' not in data and 'search-continue' not in data, 'Incomplete Wikidata result')
                items = seq(data.get('search'), 'Wikidata search')
                require(all(re.fullmatch(r'Q[1-9][0-9]*', i.get('id', '')) for i in items), 'Invalid Wikidata ID')
                ledger.accept('wikimedia', key, {'query': query, 'language': language, 'entities': ordered([pick(i, 'id label description concepturi url') for i in items])}, proof)
                queries[key] = {'evidence': proof}
            except (MonitorError, KeyError, TypeError, ValueError) as exc:
                ledger.failure('wikimedia', key, exc)
    ledger.finish('wikimedia', queries if not ledger.errors['wikimedia'] else None)


def publish_local_snapshot(store: Path, before: bytes, after: dict) -> tuple[str, str]:
    require(safe_read(store / STATE_PATH) == before, 'STATE_CONFLICT: never overwrite a successor')
    after['previous_state_sha256'] = digest(before)
    after['generation'] += 1
    output = canonical(after)
    sha = digest(output)
    history = store / 'monitor/history' / ('%012d-%s.json' % (after['generation'], sha))
    if history.exists():
        require(safe_read(history) == output, 'History collision')
    else:
        atomic_write(history, output)
    # The source authority is Git: only the runner's atomic commit/ref update and
    # independent readback make this local replacement an acknowledged effect.
    require(safe_read(store / STATE_PATH) == before, 'STATE_CONFLICT during preparation')
    atomic_write(store / STATE_PATH, output)
    require(safe_read(store / STATE_PATH) == output, 'Local readback mismatch')
    return sha, history.relative_to(store).as_posix()


def provenance(source_head: str, source_tree: str, run_id: str) -> dict:
    require(re.fullmatch(r'[0-9a-f]{40}', source_head) is not None, 'Invalid source HEAD')
    require(re.fullmatch(r'[0-9a-f]{40}', source_tree) is not None, 'Invalid source TREE')
    require(re.fullmatch(r'[0-9]+(?:-[0-9]+)?|local-test', run_id) is not None, 'Invalid run identity')
    return {'repository': 'Goldkelch/qik-vrt', 'head': source_head, 'tree': source_tree, 'run_id': run_id}


@contextmanager
def exclusive_store(store: Path):
    require(all(not parent.is_symlink() for parent in (store, *store.parents)), 'Refuse symlink store')
    folder = store / 'monitor'
    require(not folder.is_symlink(), 'Refuse symlink monitor directory')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / '.lock'
    require(not path.is_symlink(), 'Refuse symlink lock')
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise MonitorError('STATE_WRITER_BUSY') from None
        yield
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('initialize', 'observe', 'validate', 'acknowledge'))
    parser.add_argument('--policy', type=Path, default=Path(__file__).resolve().parents[1] / 'policy/PUBLICATION_MONITOR_V1.json')
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--source-head', default='')
    parser.add_argument('--source-tree', default='')
    parser.add_argument('--run-id', default='')
    parser.add_argument('--event-id', action='append', default=[])
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    policy = load_json(safe_read(args.policy))
    validate_policy(policy)
    args.store.mkdir(parents=True, exist_ok=True)
    require(not args.store.is_symlink(), 'Refuse symlink store')
    with exclusive_store(args.store):
        return execute(args, policy)


def execute(args, policy) -> int:
    path = args.store / STATE_PATH
    if args.command == 'initialize':
        require(not path.exists() and not path.is_symlink(), 'Refuse to reset existing state')
        require(not any((args.store / 'monitor/history').glob('*.json')), 'Refuse genesis over existing history')
        state = genesis(policy, provenance(args.source_head, args.source_tree, args.run_id))
        raw = canonical(state)
        atomic_write(args.store / 'monitor/history' / ('%012d-%s.json' % (0, digest(raw))), raw)
        atomic_write(path, raw)
        require(load_json(safe_read(path)) == state, 'Genesis readback mismatch')
        return 0
    before = safe_read(path)  # Missing state is an error, NEVER a fresh genesis.
    state = load_json(before)
    validate_store(args.store, state, policy)
    if args.command == 'validate':
        print(json.dumps({'state_sha256': digest(before), 'generation': state['generation'], 'monitor_id': MONITOR_ID}))
        return 0
    if args.command == 'acknowledge':
        require(bool(args.event_id), 'No exact notification event IDs')
        for ident in args.event_id:
            require(HEX.fullmatch(ident) is not None, 'Invalid event ID')
            if ident in state['acknowledged_events']:
                continue
            require(ident in state['outbox'], 'Unknown outbox event')
            state['acknowledged_events'][ident] = {'acknowledged_at': utc(), 'event': state['outbox'].pop(ident)}
        if state != load_json(before):
            publish_local_snapshot(args.store, before, state)
        return 0
    state['source'] = provenance(args.source_head, args.source_tree, args.run_id)
    ledger = Ledger(state, policy, utc())
    client = PublicGET(policy, args.store)
    for platform, collector in zip(PLATFORMS, (collect_zenodo, collect_arxiv, collect_wikimedia, collect_crates)):
        retry = ledger.state['platforms'][platform].get('retry_not_before')
        if retry and parse_time(ledger.now) < parse_time(retry):
            ledger.state['platforms'][platform]['health'] = 'RETRY_AFTER_HOLD_LAST_GOOD_RETAINED'
            continue
        try:
            collector(client, ledger)
        except (MonitorError, KeyError, TypeError, ValueError) as exc:
            ledger.failure(platform, 'collector', exc)
            ledger.finish(platform, None)
    validate_state(ledger.state, policy)
    sha, history = publish_local_snapshot(args.store, before, ledger.state)
    validate_store(args.store, ledger.state, policy)
    receipt = {'schema': 'qikvrt.publication-monitor.local-preparation.v1',
               'state_sha256': sha, 'previous_state_sha256': digest(before),
               'history': history, 'source': state['source'], 'public_request_attempts': client.count,
               'health': {p: ledger.state['platforms'][p]['health'] for p in PLATFORMS},
               'outbox_event_ids': sorted(ledger.state['outbox']),
               'external_publication_writes': 0, 'repository_persistence_readback': False,
               'notification_authorized_by_this_receipt': False}
    if args.receipt:
        atomic_write(args.receipt, canonical(receipt))
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (MonitorError, OSError, ValueError, KeyError, TypeError) as exc:
        print('BLOCK_PUBLICATION_MONITOR: ' + str(exc)[:300], file=sys.stderr)
        raise SystemExit(2)

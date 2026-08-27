# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DISCLOSURE = ROOT / '.well-known' / 'qik-vrt-self-disclosure.json'
TOOL = ROOT / 'tools' / 'qikvrt_self_disclosure.py'
OVERVIEW_HTML = ROOT / 'docs' / 'publications' / 'index.html'
OVERVIEW_JSON = ROOT / 'docs' / 'publications' / 'index.json'
CANONICAL_URL = 'https://goldkelch.github.io/qik-vrt/publications/'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SelfDisclosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.disclosure = read_json(DISCLOSURE)
        cls.overview = read_json(OVERVIEW_JSON)
        cls.html = OVERVIEW_HTML.read_text(encoding='utf-8')

    def test_discovery_document(self):
        self.assertEqual(self.disclosure['state'], 'AVAILABLE')
        self.assertTrue(self.disclosure['capabilities'])
        self.assertFalse(self.disclosure['completion_claims']['pass'])
        capabilities = {entry['id'] for entry in self.disclosure['capabilities']}
        self.assertIn('publication_overview_discovery', capabilities)
        self.assertIn('firefox_proxy_delegation_bridge', capabilities)
        binding = self.disclosure['bindings']['publication_overview']
        self.assertEqual(binding['canonical_url'], CANONICAL_URL)
        self.assertEqual(binding['human_index_path'], 'docs/publications/index.html')
        self.assertEqual(binding['machine_index_path'], 'docs/publications/index.json')
        firefox = self.disclosure['bindings']['firefox_proxy_delegation_bridge']
        self.assertEqual(
            firefox['executor_contract_path'],
            'state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json',
        )
        self.assertEqual(
            firefox['workflow_path'],
            '.github/workflows/qikvrt_firefox_proxy_delegation.yml',
        )
        self.assertTrue(firefox['current_exact_head_gate_required'])
        self.assertFalse(firefox['historical_gate_evidence_transferable'])

    def test_machine_interaction(self):
        for command in ('show', 'capabilities', 'status'):
            process = subprocess.run(
                [sys.executable, str(TOOL), command],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            json.loads(process.stdout)

    def test_batch_002_evidence_present(self):
        base = ROOT / 'release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/public-candidate-byte-freeze'
        self.assertTrue((base / 'PUBLIC_CANDIDATE_BYTE_FREEZE_RECEIPT.json').is_file())
        self.assertEqual(len(list((base / 'records').glob('*.json'))), 6)
        self.assertEqual(len(list((base / 'files').glob('*.json'))), 70)

    def test_publication_overview_discovery_and_bundle_coverage(self):
        self.assertEqual(self.overview['schema'], 'qikvrt_publication_overview_v1')
        self.assertEqual(self.overview['canonical_url'], CANONICAL_URL)
        self.assertIn(f'<link rel="canonical" href="{CANONICAL_URL}">', self.html)
        self.assertIn('application/ld+json', self.html)
        self.assertIn(CANONICAL_URL, (ROOT / 'docs/sitemap.xml').read_text(encoding='utf-8'))
        self.assertIn('https://goldkelch.github.io/qik-vrt/sitemap.xml', (ROOT / 'docs/robots.txt').read_text(encoding='utf-8'))
        self.assertIn('href="publications/"', (ROOT / 'docs/index.html').read_text(encoding='utf-8'))

        for path in ('AI', 'README.md'):
            text = (ROOT / path).read_text(encoding='utf-8')
            self.assertIn(CANONICAL_URL, text, path)
            self.assertIn('docs/publications/index.json', text, path)

        indexed = {entry['path']: entry for entry in self.overview['publication_bundles']}
        local = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / 'docs' / 'publications').glob('*/README.md')
        }
        self.assertTrue(local)
        self.assertTrue(local.issubset(indexed), sorted(local - set(indexed)))

        for path, entry in indexed.items():
            local_path = ROOT / path
            self.assertIn(path, self.html, path)
            if local_path.is_file():
                continue
            commit = entry.get('repository_commit', '')
            self.assertRegex(commit, r'^[0-9a-f]{40}$', path)
            self.assertIn(f'/blob/{commit}/{path}', entry.get('url', ''), path)
            self.assertIn(entry['url'], self.html, path)

    def test_referenced_dois_are_indexed_and_visible(self):
        indexed = {entry['doi'] for entry in self.overview['zenodo_records']}
        source_paths = self.overview['maintenance']['coverage_sources'][-3:]
        referenced = set()
        for relative in source_paths:
            text = (ROOT / relative).read_text(encoding='utf-8')
            referenced.update(re.findall(r'https://doi\.org/(10\.5281/zenodo\.\d+)', text))
        self.assertTrue(referenced)
        self.assertTrue(referenced.issubset(indexed), sorted(referenced - indexed))
        for entry in self.overview['zenodo_records']:
            self.assertEqual(entry['doi_url'], f"https://doi.org/{entry['doi']}")
            self.assertIn(entry['doi_url'], self.html, entry['id'])

    def test_zenodo_publication_receipt_coverage(self):
        records = {entry.get('receipt_path'): entry for entry in self.overview['zenodo_records'] if entry.get('receipt_path')}
        published_receipts = []
        for path in (ROOT / 'release').glob('**/zenodo-publication.json'):
            receipt = read_json(path)
            published = (
                receipt.get('state') == 'published'
                or receipt.get('public_record_verified') is True
                or receipt.get('published_by_this_run') is True
            )
            if published:
                published_receipts.append((path, receipt))

        self.assertTrue(published_receipts)
        for path, receipt in published_receipts:
            relative = path.relative_to(ROOT).as_posix()
            self.assertIn(relative, records, relative)
            indexed = records[relative]
            self.assertEqual(indexed['doi'], receipt['doi'], relative)
            self.assertEqual(indexed['manifest_sha256'], receipt['manifest_sha256'], relative)
            self.assertEqual(indexed['file_count'], len(receipt['files']), relative)
            if receipt.get('repository_commit'):
                self.assertEqual(indexed['repository_commit'], receipt['repository_commit'], relative)
            concept = receipt.get('conceptdoi') or receipt.get('concept_doi')
            if not concept and receipt.get('concept_record_id'):
                concept = f"10.5281/zenodo.{receipt['concept_record_id']}"
            if concept:
                self.assertEqual(indexed['concept_doi'], concept, relative)

        for relative, indexed in records.items():
            local = ROOT / relative
            if local.is_file():
                continue
            commit = indexed.get('receipt_commit', '')
            self.assertRegex(commit, r'^[0-9a-f]{40}$', relative)
            self.assertRegex(indexed.get('receipt_sha256', ''), r'^[0-9a-f]{64}$', relative)
            self.assertIn(f'/blob/{commit}/{relative}', indexed.get('receipt_url', ''), relative)
            self.assertIn(indexed['receipt_url'], self.html, relative)

    def test_featured_artifacts_are_hash_bound_or_commit_pinned(self):
        for artifact in self.overview['featured_artifacts']:
            path = ROOT / artifact['path']
            self.assertIn(artifact['url'], self.html, artifact['id'])
            if path.is_file():
                if artifact.get('sha256'):
                    self.assertEqual(artifact['sha256'], sha256(path), artifact['id'])
                continue
            commit = artifact.get('repository_commit', '')
            self.assertRegex(commit, r'^[0-9a-f]{40}$', artifact['id'])
            self.assertIn(commit, artifact['url'], artifact['id'])
            self.assertIn(artifact['path'], artifact['url'], artifact['id'])
            if artifact.get('sha256'):
                self.assertRegex(artifact['sha256'], r'^[0-9a-f]{64}$', artifact['id'])

    def test_ietf_provenance_coverage_and_truthful_state(self):
        indexed = {}
        for entry in self.overview['ietf_documents']:
            paths = entry.get('evidence_paths') or [entry.get('evidence_path')]
            for path in paths:
                if path:
                    self.assertNotIn(path, indexed, path)
                    indexed[path] = entry
        evidence_paths = sorted((ROOT / 'external' / 'ietf').glob('*.PROVENANCE.json'))
        evidence_paths += sorted((ROOT / 'external' / 'ietf').glob('*.CANDIDATE.json'))
        evidence_paths += sorted((ROOT / 'external' / 'ietf').glob('*.SUBMISSION_RECEIPT.json'))
        evidence_paths += sorted((ROOT / 'external' / 'ietf').glob('*.PUBLICATION_RECEIPT.json'))
        self.assertTrue(evidence_paths)
        for path in evidence_paths:
            relative = path.relative_to(ROOT).as_posix()
            self.assertIn(relative, indexed, relative)
            evidence = read_json(path)
            entry = indexed[relative]
            self.assertEqual(entry['id'], evidence['internet_draft'], relative)
            if evidence.get('datatracker_submission_performed') is False:
                self.assertEqual(entry['state'], 'candidate_not_submitted', relative)
            if evidence.get('url'):
                self.assertEqual(entry['official_url'], evidence['url'], relative)
            if evidence.get('datatracker_url'):
                self.assertEqual(entry['official_url'], evidence['datatracker_url'], relative)

        for path in (ROOT / 'external' / 'ietf').glob('*.json'):
            evidence = read_json(path)
            is_publication_receipt = (
                evidence.get('schema')
                == 'qikvrt_ietf_datatracker_publication_receipt_v1'
            )
            is_submission_evidence = (
                evidence.get('datatracker_submission_performed') is True
                or evidence.get('submitted') is True
            )
            if not (is_publication_receipt or is_submission_evidence):
                continue
            matches = [
                entry
                for entry in self.overview['ietf_documents']
                if entry['id'] == evidence.get('internet_draft')
            ]
            self.assertTrue(matches, path.name)
            entry = matches[0]
            relative = path.relative_to(ROOT).as_posix()
            # Historical candidate and submission receipts remain truthful
            # observations of their own time.  Only the selected evidence_path
            # projects the overview state.
            if relative != entry.get('evidence_path'):
                self.assertIn(relative, entry.get('evidence_paths', []))
                continue
            if is_publication_receipt:
                self.assertEqual(
                    evidence.get('public_state'),
                    'ACTIVE_INDIVIDUAL_INTERNET_DRAFT',
                    path.name,
                )
                if entry.get('superseded_by'):
                    self.assertEqual(
                        entry['state'],
                        'published_superseded_internet_draft',
                        path.name,
                    )
                    self.assertIs(entry.get('active'), False, path.name)
                    superseders = [
                        item
                        for item in self.overview['ietf_documents']
                        if item['id'] == entry['superseded_by']
                    ]
                    self.assertEqual(len(superseders), 1, path.name)
                    self.assertEqual(
                        superseders[0]['state'],
                        'published_internet_draft',
                        path.name,
                    )
                    self.assertIs(superseders[0].get('active'), True, path.name)
                else:
                    self.assertEqual(
                        entry['state'],
                        'published_internet_draft',
                        path.name,
                    )
                    self.assertIs(entry.get('active'), True, path.name)
                continue
            expected_state = (
                'published_internet_draft'
                if evidence.get('published') is not False
                and evidence.get('state')
                != 'AWAITING_PREVIOUS_VERSION_AUTHOR_APPROVAL'
                else 'awaiting_previous_version_author_approval'
            )
            self.assertEqual(entry['state'], expected_state, path.name)

        for entry in self.overview['ietf_documents']:
            self.assertIn(entry['boundary'], json.dumps(self.overview, ensure_ascii=False))
            if entry['state'] in {
                'published_internet_draft',
                'published_superseded_internet_draft',
                'awaiting_previous_version_author_approval',
            }:
                self.assertIn(entry['official_url'], self.html, entry['id'])
            else:
                self.assertNotIn('official_url', entry, entry['id'])
            for artifact in entry.get('artifacts', {}).values():
                path = ROOT / artifact['path']
                if path.is_file():
                    self.assertEqual(artifact['sha256'], sha256(path), artifact['path'])
                else:
                    self.assertRegex(artifact['sha256'], r'^[0-9a-f]{64}$', artifact['path'])
                    self.assertIn(artifact['url'], self.html, artifact['path'])


if __name__ == '__main__':
    unittest.main()

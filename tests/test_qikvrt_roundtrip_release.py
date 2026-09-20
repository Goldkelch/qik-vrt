# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Reject changed assets, mismatched authorization and unsafe publication inputs."""
import copy
import json
import unittest
from tools import qikvrt_roundtrip_release as p


class PublicationBoundaries(unittest.TestCase):
    def setUp(self):
        self.raw = b'<html>the authorized publication</html>'
        self.notes = b'Frozen release notes'
        self.owner = json.dumps({'actor': 'Ingolf Lohmann', 'repositories': list(p.REPOS),
                               'artifact_sha256': p.digest(self.raw), 'artifact_bytes': len(self.raw),
                               'instruction_verbatim': 'Und diese Freigabe erteile ich hiermit zugleich.'}).encode()
        self.m = {'schema': 'qikvrt_roundtrip_publication_request_v1', 'state': 'AUTHORIZE_COMMON_HTML_RELEASE',
                  'repository': p.REPOS[0], 'peer_repository': p.REPOS[1], 'source_commit': 'a'*40,
                  'source_tree': 'b'*40, 'peer_commit': 'c'*40, 'peer_tree': 'd'*40, 'executor_commit': 'e'*40,
                  'publisher_sha256': 'f'*64, 'artifact_sha256': p.digest(self.raw), 'artifact_bytes': len(self.raw),
                  'release_notes_sha256': p.digest(self.notes), 'owner_authorization_sha256': p.digest(self.owner)}

    def test_exact_binding_and_changed_bytes(self):
        p.validate_shape(self.m)
        p.validate_payload(self.m, self.raw, self.notes, self.owner)
        for raw, notes, owner in ((self.raw+b'x', self.notes, self.owner), (self.raw, self.notes+b'x', self.owner), (self.raw, self.notes, self.owner+b' ')):
            with self.assertRaises(RuntimeError):
                p.validate_payload(self.m, raw, notes, owner)

    def test_no_other_repository_or_extra_path(self):
        for key, value in (('repository', 'other/repository'), ('peer_repository', p.REPOS[0]), ('asset_path', '../../secret'), ('state', 'PREPARED_INACTIVE')):
            m = copy.deepcopy(self.m); m[key] = value
            with self.assertRaises(RuntimeError): p.validate_shape(m)

    def test_budget_and_unbound_refs(self):
        for key, value in (('artifact_bytes', 10_000_000), ('artifact_bytes', True), ('source_commit', 'main'), ('artifact_sha256', '0')):
            m = copy.deepcopy(self.m); m[key] = value
            with self.assertRaises(RuntimeError): p.validate_shape(m)

    def test_existing_asset_conflict_is_not_overwritten(self):
        asset = {'name': p.ASSET, 'state': 'uploaded', 'size': len(self.raw), 'digest': 'sha256:'+p.digest(self.raw)}
        p.verify_asset(asset, self.m)
        for key, value in (('name', 'other.html'), ('size', len(self.raw)+1), ('digest', None), ('state', 'starter')):
            changed = dict(asset); changed[key] = value
            with self.assertRaises(RuntimeError): p.verify_asset(changed, self.m)


if __name__ == '__main__':
    unittest.main()

# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Git transport seconds do not weaken exact publication decision bindings."""
import copy
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools import qikvrt_zenodo_publish as publisher

class TaggerPrecisionTests(unittest.TestCase):
    def test_git_seconds_and_timezone(self):
        cases = {
            '2026-09-19T04:21:17.149683+00:00': '2026-09-19T04:21:17Z',
            '2026-09-19T06:21:17.999999+02:00': '2026-09-19T04:21:17Z',
            '2026-09-19T04:21:17Z': '2026-09-19T04:21:17Z',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(publisher._canonical_github_tagger_date(raw), expected)

    def test_other_tag_fields_remain_exact(self):
        expected = {'tag':'qikvrt-zenodo-auth/'+'1'*64, 'message':'exact-decision\n', 'object':'2'*40, 'type':'commit', 'tagger':{'name':'Publisher', 'email':'test@example.invalid', 'date':'2026-09-19T04:21:17Z'}}
        good = {'sha':'3'*40, 'tag':expected['tag'], 'message':expected['message'], 'object':{'sha':expected['object'], 'type':'commit'}, 'tagger':dict(expected['tagger'])}
        publisher._validate_github_tag_response(good, expected, '3'*40)
        mutations = [('message', 'exact-decision'), ('tag', 'other'), ('sha', '4'*40), ('object', {'sha':'5'*40,'type':'commit'}), ('object', {'sha':'2'*40,'type':'tree'})]
        for field, value in mutations:
            changed = copy.deepcopy(good); changed[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(publisher.zenodo.ZenodoError):
                    publisher._validate_github_tag_response(changed, expected, '3'*40)
        for field, value in [('name','Other'),('email','other@example.invalid'),('date','2026-09-19T04:21:18Z')]:
            changed=copy.deepcopy(good); changed['tagger'][field]=value
            with self.subTest(tagger_field=field):
                with self.assertRaises(publisher.zenodo.ZenodoError):
                    publisher._validate_github_tag_response(changed, expected, '3'*40)

if __name__ == '__main__':
    unittest.main(verbosity=2)

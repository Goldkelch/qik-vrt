from __future__ import annotations

import copy
import unittest

from controller.qikvrt_trusted_handoff import HandoffBlock, make_authorization, validate_request, verify_authorization


REQUEST = {
    "schema": "qikvrt_execution_request_v1",
    "transaction_id": "pr-98-2a14e065",
    "repository": "Goldkelch/qik-vrt",
    "source_kind": "pull_request",
    "source_number": 98,
    "base_sha": "4" * 40,
    "head_sha": "2" * 40,
    "tree_sha": "3" * 40,
    "delta_sha256": "a" * 64,
    "requested_operation": "EXECUTE",
}


class TrustedHandoffTests(unittest.TestCase):
    def test_exact_request_authorizes_and_verifies(self):
        key = b"test-only-handoff-key"
        authorization = make_authorization(REQUEST, key=key, principal="qikvrt-control-plane", installation_id=123)
        result = verify_authorization(REQUEST, authorization, key=key, expected_principal="qikvrt-control-plane", expected_installation_id=123)
        self.assertEqual(result["state"], "AUTHORIZATION_CHECKED")
        self.assertFalse(result["completion_claims"]["PASS"])

    def test_candidate_cannot_change_bound_tree_after_authorization(self):
        key = b"test-only-handoff-key"
        authorization = make_authorization(REQUEST, key=key, principal="qikvrt-control-plane", installation_id=123)
        changed = copy.deepcopy(REQUEST)
        changed["tree_sha"] = "9" * 40
        with self.assertRaises(HandoffBlock):
            verify_authorization(changed, authorization, key=key, expected_principal="qikvrt-control-plane", expected_installation_id=123)

    def test_wrong_principal_or_installation_is_rejected(self):
        key = b"test-only-handoff-key"
        authorization = make_authorization(REQUEST, key=key, principal="qikvrt-control-plane", installation_id=123)
        with self.assertRaises(HandoffBlock):
            verify_authorization(REQUEST, authorization, key=key, expected_principal="other", expected_installation_id=123)
        with self.assertRaises(HandoffBlock):
            verify_authorization(REQUEST, authorization, key=key, expected_principal="qikvrt-control-plane", expected_installation_id=999)

    def test_noncanonical_or_extra_fields_fail_closed(self):
        changed = copy.deepcopy(REQUEST)
        changed["candidate_command"] = "echo pwned"
        with self.assertRaises(HandoffBlock):
            validate_request(changed)


if __name__ == "__main__":
    unittest.main()

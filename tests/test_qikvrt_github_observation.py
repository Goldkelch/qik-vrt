# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error

from tools.qikvrt_github_observation import ObservationClient, ObservationError, gh_read_json
from tools import qikvrt_requested_review_executor as executor


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status, self.headers = status, headers or {}


class ObservationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.requests = []
        self.replies = []
        self.client = ObservationClient("Goldkelch/qik-vrt", "test-secret", self.root,
                                        opener=self.request, clock=lambda: 1000)
        self.path = "repos/Goldkelch/qik-vrt/pulls/1240"

    def request(self, request, **kwargs):
        self.requests.append(request)
        status, body, headers = self.replies.pop(0)
        if status >= 300:
            raise urllib.error.HTTPError(request.full_url, status, "test", headers,
                                         io.BytesIO(body))
        return Response(body, status, headers)

    def receipts(self):
        return [json.loads(p.read_bytes()) for p in (self.root / "receipts").glob("*.json")]

    def test_repeated_observations_require_fresh_server_validation(self):
        self.replies = [(200, b'{"head":"a"}', {"ETag": '"a"'})] + [
            (304, b"", {"ETag": '"a"'}) for _ in range(9)]
        for _ in range(10):
            self.assertEqual(self.client.get(self.path)[0], {"head": "a"})
        self.assertEqual(len(self.requests), 10)
        self.assertEqual([r.get_header("If-none-match") for r in self.requests],
                         [None] + ['"a"'] * 9)
        self.assertEqual(len(self.receipts()), 10)
        self.assertEqual(len(list((self.root / "objects").iterdir())), 1)
        self.assertEqual(sum(r["status"] == 200 for r in self.receipts()), 1)

    def test_changed_head_is_observed_and_old_bytes_are_retained(self):
        self.replies = [(200, b'{"head":"a"}', {"ETag": '"a"'}),
                        (200, b'{"head":"b"}', {"ETag": '"b"'})]
        self.assertEqual(self.client.get(self.path)[0]["head"], "a")
        self.assertEqual(self.client.get(self.path)[0]["head"], "b")
        self.assertEqual(len(list((self.root / "objects").iterdir())), 2)

    def test_rate_limit_never_returns_cache_and_never_rotates_credentials(self):
        self.replies = [(200, b'{}', {"ETag": '"a"'}),
                        (403, b'{"message":"rate limit exceeded"}',
                         {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1234"})]
        self.client.get(self.path)
        with self.assertRaisesRegex(ObservationError, "RATE_LIMIT_EXHAUSTED.*reset=1234"):
            self.client.get(self.path)
        self.assertEqual(len(self.requests), 2)
        failed = [r for r in self.receipts() if r["status"] == 403][0]
        self.assertFalse(failed["cached_body_used"])
        self.assertEqual(failed["headers"]["x-ratelimit-reset"], "1234")
        self.assertTrue(all(r.get_header("Authorization") == "Bearer test-secret"
                            for r in self.requests))

    def test_permission_failure_is_not_rate_limit(self):
        self.replies = [(403, b'{"message":"permission denied"}', {})]
        with self.assertRaisesRegex(ObservationError, "GITHUB_OBSERVATION_HTTP_ERROR"):
            self.client.get(self.path)

    def test_secondary_limit_preserves_retry_after_without_blind_retry(self):
        self.replies = [(429, b'{}', {"Retry-After": "60"})]
        with self.assertRaisesRegex(ObservationError, "retry_after=60"):
            self.client.get(self.path)
        self.assertEqual(len(self.requests), 1)

    def test_corrupt_cache_fails_before_network(self):
        self.replies = [(200, b'{}', {"ETag": '"a"'})]
        self.client.get(self.path)
        next((self.root / "objects").iterdir()).write_bytes(b'{"corrupt":true}')
        with self.assertRaisesRegex(ObservationError, "CACHE_CORRUPT"):
            self.client.get(self.path)
        self.assertEqual(len(self.requests), 1)

    def test_unbound_304_is_not_data(self):
        self.replies = [(304, b'', {"ETag": '"a"'})]
        with self.assertRaisesRegex(ObservationError, "304_BINDING_INVALID"):
            self.client.get(self.path)

    def test_mismatched_304_validator_is_rejected(self):
        self.replies = [(200, b'{}', {"ETag": '"a"'}),
                        (304, b'', {"ETag": '"b"'})]
        self.client.get(self.path)
        with self.assertRaisesRegex(ObservationError, "304_BINDING_INVALID"):
            self.client.get(self.path)

    def test_no_validator_requires_full_new_response(self):
        self.replies = [(200, b'{"v":1}', {}), (200, b'{"v":2}', {})]
        self.client.get(self.path)
        self.assertEqual(self.client.get(self.path)[0], {"v": 2})
        self.assertIsNone(self.requests[1].get_header("If-none-match"))

    def test_pagination_is_lossless_and_each_page_is_revalidated(self):
        next_url = "https://api.github.com/" + self.path + "?page=2"
        self.replies = [(200, b'[1]', {"ETag": '"one"', "Link": f'<{next_url}>; rel="next"'}),
                        (200, b'[2]', {"ETag": '"two"'}),
                        (304, b'', {}), (200, b'[2,3]', {"ETag": '"three"'})]
        self.assertEqual(self.client.pages(self.path), [[1], [2]])
        self.assertEqual(self.client.pages(self.path), [[1], [2, 3]])
        self.assertEqual(len(self.requests), 4)

    def test_pagination_never_leaks_token_to_another_host_or_repository(self):
        for destination in ("https://evil.test/x",
                            "https://api.github.com/repos/other/repo/pulls"):
            self.replies = [(200, b'[]', {"Link": f'<{destination}>; rel="next"'})]
            with self.assertRaisesRegex(ObservationError, "OUTSIDE_BOUND_REPOSITORY"):
                self.client.pages(self.path)

    def test_pagination_cycle_is_rejected(self):
        self.replies = [(200, b'[]', {"Link": f'<https://api.github.com/{self.path}>; rel="next"'})]
        with self.assertRaisesRegex(ObservationError, "PAGINATION_NOT_COMPLETE"):
            self.client.pages(self.path)

    def test_journal_contains_no_credential(self):
        self.replies = [(200, b'{}', {"ETag": '"a"', "Authorization": "test-secret"})]
        self.client.get(self.path)
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"test-secret", path.read_bytes())

    def test_role_and_lane_indices_are_separate(self):
        self.replies = [(200, b'{}', {"ETag": '"a"'}), (200, b'{}', {"ETag": '"b"'})]
        self.client.get(self.path)
        mirror = ObservationClient("ingolf-lohmann/qik-vrt", "mirror-token", self.root,
                                   opener=self.request)
        mirror.get("repos/ingolf-lohmann/qik-vrt/pulls/1240")
        self.assertIsNone(self.requests[1].get_header("If-none-match"))
        self.assertEqual(len(list((self.root / "index").iterdir())), 2)

    def test_transport_rejects_mutation_command(self):
        with self.assertRaisesRegex(ObservationError, "READ_ONLY_COMMAND_REQUIRED"):
            gh_read_json(("gh", "api", "--method", "POST", self.path))

    def test_executor_uses_transport_and_propagates_failure(self):
        with mock.patch.dict("os.environ", {"GH_TOKEN": "test-token"}), \
                mock.patch("tools.qikvrt_github_observation.gh_read_json",
                           side_effect=ObservationError("RATE_LIMIT_EXHAUSTED")) as read:
            with self.assertRaisesRegex(executor.ReviewObservationError, "RATE_LIMIT_EXHAUSTED"):
                executor._gh_one(self.path)
        read.assert_called_once_with(("gh", "api", self.path))


if __name__ == "__main__":
    unittest.main()

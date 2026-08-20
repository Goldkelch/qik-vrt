import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock
from urllib.parse import parse_qs, urlparse

from tools import qikvrt_firefox_proxy_delegate as bridge

HEAD = "e24c343b90bf734b09201c45f9ba66d8da41a25f"
TREE = "6574244dc78b7710352ae2a5196518b7642e76ff"


class FirefoxProxyDelegateTests(unittest.TestCase):
    def test_rejects_non_https(self):
        with self.assertRaises(ValueError):
            bridge.validate_target("http://github.com/settings")

    def test_rejects_unlisted_host(self):
        with self.assertRaises(ValueError):
            bridge.validate_target("https://example.com/")

    def test_rejects_embedded_credentials(self):
        with self.assertRaises(ValueError):
            bridge.validate_target("https://user:secret@github.com/settings")

    def test_record_never_serializes_secret_or_effect(self):
        record = bridge.build_record(
            "https://github.com/settings/personal-access-tokens",
            "Goldkelch",
            "Goldkelch/qik-vrt",
            True,
        )
        self.assertFalse(record["secret_serialized"])
        self.assertFalse(record["effect_executed"])
        self.assertEqual(record["next_boundary"], "HUMAN_AUTHENTICATION_OR_SECRET_ENTRY")
        self.assertEqual(record["post_boundary_requirement"], "AUTHORITATIVE_REOBSERVATION")

    def test_review_effect_is_exactly_bound(self):
        bound = bridge.bind_review_effect(
            "https://github.com/Goldkelch/qik-vrt/pull/727/files",
            owner="Goldkelch",
            repository="Goldkelch/qik-vrt",
            pr=727,
            head=HEAD,
            tree=TREE,
        )
        q = parse_qs(urlparse(bound).query)
        self.assertEqual(q["qikvrt_effect"], ["review_approve"])
        self.assertEqual(q["qikvrt_owner"], ["Goldkelch"])
        self.assertEqual(q["qikvrt_repo"], ["Goldkelch/qik-vrt"])
        self.assertEqual(q["qikvrt_pr"], ["727"])
        self.assertEqual(q["qikvrt_head"], [HEAD])
        self.assertEqual(q["qikvrt_tree"], [TREE])

    def test_review_effect_rejects_wrong_owner_or_page(self):
        with self.assertRaises(ValueError):
            bridge.bind_review_effect(
                "https://github.com/Goldkelch/qik-vrt/pull/727/files",
                owner="ingolf-lohmann", repository="Goldkelch/qik-vrt", pr=727, head=HEAD, tree=TREE)
        with self.assertRaises(ValueError):
            bridge.bind_review_effect(
                "https://github.com/Goldkelch/qik-vrt/pull/728/files",
                owner="Goldkelch", repository="Goldkelch/qik-vrt", pr=727, head=HEAD, tree=TREE)

    @mock.patch.object(bridge.subprocess, "Popen")
    @mock.patch.object(bridge, "resolve_firefox", return_value="/usr/bin/firefox")
    def test_launches_exact_allowlisted_url(self, _resolve, popen):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = bridge.main([
                "--url", "https://github.com/settings/personal-access-tokens",
                "--expected-owner", "Goldkelch",
                "--repository", "Goldkelch/qik-vrt",
                "--json",
            ])
        self.assertEqual(rc, 0)
        popen.assert_called_once()
        argv = popen.call_args.args[0]
        self.assertEqual(argv[:2], ["/usr/bin/firefox", "--new-tab"])
        self.assertEqual(argv[2], "https://github.com/settings/personal-access-tokens")
        record = json.loads(out.getvalue())
        self.assertTrue(record["launched"])
        self.assertFalse(record["secret_serialized"])
        self.assertFalse(record["effect_executed"])

    @mock.patch.object(bridge.subprocess, "Popen")
    @mock.patch.object(bridge, "resolve_firefox", return_value="/usr/bin/firefox")
    def test_review_launch_carries_only_nonsecret_exact_binding(self, _resolve, popen):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = bridge.main([
                "--url", "https://github.com/Goldkelch/qik-vrt/pull/727/files",
                "--expected-owner", "Goldkelch",
                "--repository", "Goldkelch/qik-vrt",
                "--effect", "review_approve",
                "--pr", "727",
                "--head", HEAD,
                "--tree", TREE,
                "--json",
            ])
        self.assertEqual(rc, 0)
        target = popen.call_args.args[0][2]
        self.assertIn("qikvrt_effect=review_approve", target)
        self.assertNotIn("token", target.lower())
        record = json.loads(out.getvalue())
        self.assertEqual(record["action"], bridge.REVIEW_EFFECT)
        self.assertEqual(record["next_boundary"], "OWNER_AUTHENTICATED_SESSION")
        self.assertFalse(record["secret_serialized"])
        self.assertFalse(record["effect_executed"])


if __name__ == "__main__":
    unittest.main()

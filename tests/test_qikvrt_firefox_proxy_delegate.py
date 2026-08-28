import io
import json
import pathlib
import unittest
from contextlib import redirect_stdout
from unittest import mock
from urllib.parse import parse_qs, urlparse

from tools import qikvrt_firefox_proxy_delegate as bridge

HEAD = "e24c343b90bf734b09201c45f9ba66d8da41a25f"
TREE = "6574244dc78b7710352ae2a5196518b7642e76ff"
ROOT = pathlib.Path(__file__).resolve().parents[1]


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
        query = parse_qs(urlparse(bound).query)
        self.assertEqual(query["qikvrt_effect"], ["review_approve"])
        self.assertEqual(query["qikvrt_owner"], ["Goldkelch"])
        self.assertEqual(query["qikvrt_repo"], ["Goldkelch/qik-vrt"])
        self.assertEqual(query["qikvrt_pr"], ["727"])
        self.assertEqual(query["qikvrt_head"], [HEAD])
        self.assertEqual(query["qikvrt_tree"], [TREE])

    def test_review_effect_rejects_wrong_owner_or_page(self):
        with self.assertRaises(ValueError):
            bridge.bind_review_effect(
                "https://github.com/Goldkelch/qik-vrt/pull/727/files",
                owner="ingolf-lohmann", repository="Goldkelch/qik-vrt", pr=727, head=HEAD, tree=TREE)
        with self.assertRaises(ValueError):
            bridge.bind_review_effect(
                "https://github.com/Goldkelch/qik-vrt/pull/728/files",
                owner="Goldkelch", repository="Goldkelch/qik-vrt", pr=727, head=HEAD, tree=TREE)

    def test_content_script_enforces_live_state_and_prior_exact_disposition(self):
        source = (ROOT / "browser/firefox/qikvrt-terminal/review_effect.js").read_text(encoding="utf-8")
        required = [
            'pr.state !== "open"',
            'pr.base?.ref !== "main"',
            'pr.head?.repo?.full_name !== expectedRepo',
            'reviewer.login === expectedOwner',
            'qikvrt-requested-review-executor:v1',
            'disposition=APPROVE',
            'review.user?.login === "github-actions[bot]"',
            'body.includes(treeLine)',
            'independent Code-Owner approval: **not implied**',
            'SUBMITTED_REOBSERVE_REQUIRED',
            'MutationObserver',
            'AbortSignal.timeout',
        ]
        for needle in required:
            self.assertIn(needle, source)

    def test_review_effect_waits_only_on_dom_edges(self):
        source = (ROOT / "browser/firefox/qikvrt-terminal/review_effect.js").read_text(encoding="utf-8")
        self.assertIn('observer.observe(root, {attributes: true, childList: true, subtree: true})', source)
        self.assertIn('timeout.addEventListener("abort", onTimeout, {once: true})', source)
        self.assertNotIn("setTimeout", source)
        self.assertNotIn("while (Date.now() < deadline)", source)
        self.assertNotIn("waitFor(", source)

    def test_policy_binds_the_same_prior_disposition(self):
        policy = json.loads((ROOT / "policy/FIREFOX_PROXY_DELEGATION_V1.json").read_text(encoding="utf-8"))
        effect = policy["allowed_owner_authenticated_effects"][0]
        prior = effect["required_prior_disposition"]
        self.assertEqual(prior["review_author"], "github-actions[bot]")
        self.assertEqual(prior["disposition"], "APPROVE")
        self.assertTrue(prior["binds_exact_head"])
        self.assertTrue(prior["binds_exact_tree"])
        self.assertFalse(prior["independent_code_owner_approval_implied"])

    def test_workflow_is_pinned_and_covers_browser_effect_paths(self):
        workflow = (ROOT / ".github/workflows/qikvrt_firefox_proxy_delegation.yml").read_text(encoding="utf-8")
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", workflow)
        self.assertIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", workflow)
        self.assertIn("browser/firefox/qikvrt-terminal/review_effect.js", workflow)
        self.assertIn("browser/firefox/qikvrt-terminal/manifest.json", workflow)
        self.assertIn("node --check browser/firefox/qikvrt-terminal/review_effect.js", workflow)

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

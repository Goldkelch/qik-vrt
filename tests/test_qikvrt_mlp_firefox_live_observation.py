import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_mlp_firefox_live_observation.py"
POLICY = ROOT / "policy/MLP_FIREFOX_LIVE_OBSERVATION_V1.json"
CANONICAL_POLICY = ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_mlp_firefox_live_observation.yml"


class LiveFirefoxObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("live_observation", TOOL)
        cls.mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(cls.mod)

    def test_page_keeps_effect_boundary_visible(self):
        html = self.mod.page("a" * 40, "b" * 40)
        self.assertIn("Firefox rendered this page and executed JavaScript", html)
        self.assertIn("EFFECT_ACK_DONE = false", html)
        self.assertIn(self.mod.MLP_SHA256, html)
        self.assertIn(self.mod.TCPIP_SOURCE_HEAD, html)
        self.assertIn(self.mod.TCPIP_SOURCE_TREE, html)
        self.assertIn("fetch('/observed?nonce=", html)

    def test_policy_requires_real_observation_without_effect_claim(self):
        p = json.loads(POLICY.read_text())
        self.assertTrue(p["required_observation"]["real_firefox_process"])
        self.assertTrue(p["required_observation"]["javascript_witness"])
        self.assertTrue(p["required_observation"]["color_screenshot"])
        self.assertFalse(p["state_separation"]["effect_ack_done"])
        self.assertFalse(p["state_separation"]["protected_external_effect"])
        self.assertFalse(p["state_separation"]["physical_megast_execution"])
        self.assertEqual(p["stack"]["guest_tcpip_proof_tree"], self.mod.TCPIP_SOURCE_TREE)
        self.assertEqual(p["canonical_source"]["repository_role"], "AUTHORITY")
        self.assertEqual(p["canonical_source"]["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(
            p["canonical_source"]["candidate_repositories"],
            ["Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"],
        )
        self.assertFalse(p["canonical_source"]["local_origin_is_source_authority"])

    def test_workflow_binds_exact_head_and_proven_predecessor(self):
        text = WORKFLOW.read_text()
        canonical = json.loads(CANONICAL_POLICY.read_text())
        self.assertIn("github.event.pull_request.head.sha || github.sha", text)
        self.assertIn(self.mod.TCPIP_SOURCE_HEAD, text)
        self.assertIn(self.mod.MLP_SHA256, text)
        self.assertIn("firefox --headless", text)
        self.assertIn("browser-observation.json", text)
        self.assertIn("firefox-live.png", text)
        self.assertIn("refs/pull/745/head", text)
        self.assertIn("git diff --quiet", text)
        self.assertIn("policy/CANONICAL_UPSTREAM_REMOTE_V1.json", text)
        self.assertIn('git remote add "$authority_remote" "$authority_url"', text)
        self.assertIn('git fetch --no-tags "$authority_remote" "refs/pull/745/head:$source_ref"', text)
        self.assertNotIn("git fetch --no-tags origin 'refs/pull/745/head", text)
        self.assertEqual(canonical["canonical_upstream"]["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(canonical["canonical_upstream"]["role"], "AUTHORITY")
        self.assertNotIn("git merge-base --is-ancestor", text)


if __name__ == "__main__":
    unittest.main()

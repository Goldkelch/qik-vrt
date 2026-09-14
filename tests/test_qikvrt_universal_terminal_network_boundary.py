import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy/universal-terminal/compose.yaml"
POLICY = ROOT / "policy/QIKVRT_UNIVERSAL_TERMINAL_VIRTUALIZATION_V1.json"


class UniversalTerminalNetworkBoundaryTests(unittest.TestCase):
    def test_compose_host_bind_is_literal_ipv4_loopback(self):
        text = COMPOSE.read_text(encoding="utf-8")
        self.assertIn('      - "127.0.0.1:${QIKVRT_NOVNC_HOST_PORT:-6080}:6080"', text)
        self.assertNotIn("QIKVRT_BIND_ADDRESS", text)
        self.assertNotIn('"0.0.0.0:', text)
        self.assertNotIn('"[::]:', text)

    def test_policy_forbids_non_loopback_exposure(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        boundary = policy["network_boundary"]
        self.assertEqual(boundary["human_view"], "NOVNC_LOOPBACK_ONLY")
        self.assertEqual(boundary["host_bind_address"], "127.0.0.1")
        self.assertIs(boundary["host_bind_address_configurable"], False)
        self.assertIs(boundary["non_loopback_exposure_permitted"], False)
        self.assertIs(boundary["external_exposure_permitted"], False)
        self.assertIn(
            "HOST_NOVNC_BIND_MUST_REMAIN_IPV4_LOOPBACK_ONLY",
            policy["required_semantics"],
        )
        self.assertIn(
            "NON_LOOPBACK_NOVNC_EXPOSURE_FORBIDDEN",
            policy["required_semantics"],
        )
        self.assertEqual(
            policy["definition_of_done"]["loopback_only_host_bind_regression"],
            "REQUIRED",
        )


if __name__ == "__main__":
    unittest.main()

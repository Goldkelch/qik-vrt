import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy/universal-terminal/compose.yaml"
POLICY = ROOT / "policy/QIKVRT_UNIVERSAL_TERMINAL_VIRTUALIZATION_V1.json"
ENTRYPOINT = ROOT / "deploy/universal-terminal/entrypoint.sh"
CLOUD_ENTRYPOINT = ROOT / "deploy/universal-terminal/cloud-entrypoint.sh"
DOCKERFILE = ROOT / "deploy/universal-terminal/Dockerfile"
WORKFLOW = ROOT / ".github/workflows/qikvrt_universal_terminal_container.yml"


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

    def test_standalone_default_and_cloud_mesh_route_are_explicit_and_distinct(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["runtime_transport"]["default_start_surface"], "about:blank")
        self.assertEqual(
            policy["runtime_transport"]["runtime_state_schema"],
            "qikvrt_universal_terminal_runtime_state_v2",
        )
        self.assertIn(
            'START_URL="${QIKVRT_START_URL:-about:blank}"',
            ENTRYPOINT.read_text(encoding="utf-8"),
        )
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("QIKVRT_START_URL=about:blank", dockerfile)
        self.assertIn('browser.startup.homepage", "about:blank"', dockerfile)
        self.assertIn(
            'export QIKVRT_START_URL="${QIKVRT_CLOUD_START_URL:-http://127.0.0.1:8080/qik-vrt/mesh/v1/}"',
            CLOUD_ENTRYPOINT.read_text(encoding="utf-8"),
        )
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("qikvrt_universal_terminal_runtime_state_v2", workflow)
        self.assertNotIn("qikvrt_universal_terminal_runtime_state_v1", workflow)


if __name__ == "__main__":
    unittest.main()

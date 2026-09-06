import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy/universal-terminal/compose.yaml"
POLICY = ROOT / "policy/QIKVRT_UNIVERSAL_TERMINAL_VIRTUALIZATION_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_universal_terminal_container.yml"
BOOTSTRAP = pathlib.PurePosixPath("/opt/qikvrt/runtime/bootstrap-profile")


def tmpfs_targets(text):
    """Read short-form tmpfs targets from this deliberately small Compose file.

    Docker Compose remains the authoritative parser in the integration test.
    Reject an unsupported shape rather than silently interpreting no mounts.
    """
    match = re.search(r"^    tmpfs:\n((?:^      .*\n)+)", text, re.MULTILINE)
    if not match:
        raise ValueError("missing or unsupported tmpfs section")
    targets = []
    for line in match.group(1).splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if not value.startswith("- /"):
            raise ValueError("unsupported tmpfs entry")
        target = value[2:].split(":", 1)[0]
        path = pathlib.PurePosixPath(target)
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe tmpfs target")
        targets.append(path)
    if not targets:
        raise ValueError("empty tmpfs section")
    return targets


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
        self.assertIn("HOST_NOVNC_BIND_MUST_REMAIN_IPV4_LOOPBACK_ONLY", policy["required_semantics"])
        self.assertIn("NON_LOOPBACK_NOVNC_EXPOSURE_FORBIDDEN", policy["required_semantics"])
        self.assertEqual(policy["definition_of_done"]["loopback_only_host_bind_regression"], "REQUIRED")

    def test_tmpfs_does_not_hide_bootstrap_profile(self):
        for target in tmpfs_targets(COMPOSE.read_text(encoding="utf-8")):
            self.assertNotEqual(target, BOOTSTRAP)
            self.assertNotIn(target, BOOTSTRAP.parents)

    def test_original_runtime_mount_is_a_regression(self):
        original = "    tmpfs:\n      - /tmp\n      - /run\n      - /opt/qikvrt/runtime:size=256m,mode=1777\n"
        self.assertTrue(any(target == BOOTSTRAP or target in BOOTSTRAP.parents for target in tmpfs_targets(original)))

    def test_unknown_tmpfs_shape_fails_closed(self):
        with self.assertRaises(ValueError):
            tmpfs_targets("    tmpfs: []\n")
        with self.assertRaises(ValueError):
            tmpfs_targets("    tmpfs:\n      - type: tmpfs\n")

    def test_hardening_and_writable_logs_are_retained(self):
        text = COMPOSE.read_text(encoding="utf-8")
        self.assertIn(pathlib.PurePosixPath("/opt/qikvrt/runtime/logs"), tmpfs_targets(text))
        self.assertIn("    read_only: true", text)
        self.assertIn("      - no-new-privileges:true", text)
        self.assertIn("    cap_drop:\n      - ALL", text)

    def test_ci_runs_compose_instead_of_a_weaker_docker_run(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("COMPOSE_FILE: deploy/universal-terminal/compose.yaml", text)
        self.assertIn("docker compose build", text)
        self.assertIn("docker compose up -d --no-build --wait --wait-timeout 120", text)
        self.assertIn("docker compose up -d --no-build --force-recreate --wait --wait-timeout 120", text)
        self.assertNotIn("docker run -d", text)
        self.assertIn("host['ReadonlyRootfs'] is True", text)
        self.assertIn("'ALL' in host['CapDrop']", text)

    def test_receipt_uses_step_outcomes_not_file_existence(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("steps.observe.outcome", text)
        self.assertIn("steps.restart.outcome", text)
        self.assertIn("steps.final_binding.outcome", text)
        self.assertNotIn("runtime_observed=os.path.exists", text)
        self.assertIn("'scope':'CI_LOCAL_ONLY'", text)


if __name__ == "__main__":
    unittest.main()

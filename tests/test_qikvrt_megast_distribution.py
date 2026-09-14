import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "distribution/qikvrt-megast/build.sh"
SESSION = ROOT / "distribution/qikvrt-megast/qikvrt-megast-session.sh"
README = ROOT / "distribution/qikvrt-megast/README.md"
WORKFLOW = ROOT / ".github/workflows/qikvrt_megast_distribution_v1.yml"


class MegaSTDistributionContract(unittest.TestCase):
    def test_build_contract_is_fail_closed(self):
        text = BUILD.read_text()
        self.assertIn('set -eu', text)
        self.assertIn('effect_ack_done', text)
        self.assertIn('qikvrt-megast-amd64.iso.sha256', text)
        self.assertIn('BLOCKED: live-build produced no ISO', text)

    def test_modern_compatibility_envelope_is_present(self):
        text = BUILD.read_text()
        for token in ('hatari', 'firefox-esr', 'flatpak', 'podman', 'xfce4'):
            self.assertIn(token, text)

    def test_live_build_uses_supported_security_and_updates_switches(self):
        text = BUILD.read_text()
        self.assertIn("lb config --help 2>&1 | grep -q -- '--security-suite'", text)
        self.assertIn('--security true --security-suite trixie-security', text)
        self.assertIn('debian-security trixie-security', text)
        self.assertIn('set -- "$@" --security false', text)
        self.assertIn("lb config --help 2>&1 | grep -q -- '--updates'", text)
        self.assertIn('set -- "$@" --updates true', text)

    def test_visual_shell_does_not_claim_atari_identity(self):
        text = SESSION.read_text()
        self.assertIn('Mega-ST/GEM-inspired', text)
        self.assertIn('does not claim binary or hardware identity', text)
        self.assertIn('effect_ack_done', text)

    def test_publication_waits_for_exact_main(self):
        text = WORKFLOW.read_text()
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertEqual(
            text.count('(cd out && sha256sum -c qikvrt-megast-amd64.iso.sha256)'),
            1,
        )
        self.assertIn('cd out\n          sha256sum -c qikvrt-megast-amd64.iso.sha256', text)
        self.assertIn('Read back published release metadata', text)

    def test_pull_request_build_is_literal_head_bound(self):
        text = WORKFLOW.read_text()
        subject = '${{ github.event.pull_request.head.sha || github.sha }}'
        self.assertEqual(text.count(f'ref: {subject}'), 2)
        self.assertIn(f'QIKVRT_EXACT_SHA: {subject}', text)
        self.assertIn(f'"source_sha": "{subject}"', text)
        self.assertIn(f'name: qikvrt-megast-{subject}', text)

    def test_workflow_pins_trixie_live_build_toolchain(self):
        text = WORKFLOW.read_text()
        self.assertNotIn('apt-get install -y live-build', text)
        self.assertIn('live-build_20250505+deb13u1_all.deb', text)
        self.assertIn(
            '58e09779881cbcc631c49ceb703413e0247a87db01823e597b2a1c40a2afd8f4',
            text,
        )
        self.assertIn('/tmp/live-build.deb | sha256sum -c -', text)
        self.assertIn('sudo dpkg -i /tmp/live-build.deb', text)
        self.assertIn('debian-archive-keyring_2025.1_all.deb', text)
        self.assertIn(
            '9ea7778e443144ca490668737a8ab22dd3e748bb99e805e22ec055abeb3c7fac',
            text,
        )
        self.assertIn('/tmp/debian-archive-keyring.deb | sha256sum -c -', text)
        self.assertIn('sudo dpkg -i /tmp/debian-archive-keyring.deb', text)

    def test_terminal_definition_requires_download_readback(self):
        text = README.read_text()
        self.assertIn('stable release path', text)
        self.assertIn('independently read back after publication', text)
        self.assertIn('EFFECT_ACK_DONE', text)
        self.assertIn('Stay fail closed and keep future open', text)


if __name__ == '__main__':
    unittest.main()

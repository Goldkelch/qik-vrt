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

    def test_visual_shell_does_not_claim_atari_identity(self):
        text = SESSION.read_text()
        self.assertIn('Mega-ST/GEM-inspired', text)
        self.assertIn('does not claim binary or hardware identity', text)
        self.assertIn('effect_ack_done', text)

    def test_publication_waits_for_exact_main(self):
        text = WORKFLOW.read_text()
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn('sha256sum -c', text)
        self.assertIn('Read back published release metadata', text)

    def test_terminal_definition_requires_download_readback(self):
        text = README.read_text()
        self.assertIn('stable release path', text)
        self.assertIn('independently read back after publication', text)
        self.assertIn('EFFECT_ACK_DONE', text)
        self.assertIn('Stay fail closed and keep future open', text)


if __name__ == '__main__':
    unittest.main()

import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "distribution/qikvrt-reference-minimal"
CONTRACT = BASE / "BUILD_CONTRACT.json"
BUILD = BASE / "build.sh"
VERIFY = BASE / "verify-rebuild.py"
WORKFLOW = ROOT / ".github/workflows/qikvrt_reference_minimal_v1.yml"


class ReferenceMinimalContract(unittest.TestCase):
    def test_contract_is_narrow_and_fail_closed(self):
        value = json.loads(CONTRACT.read_text())
        self.assertEqual(value["schema"], "qikvrt.reference-linux-build-contract.v1")
        self.assertEqual(value["artifact"]["architecture"], "amd64")
        self.assertIn("snapshot.debian.org/archive/debian/20260922/", value["distribution"]["snapshot"])
        self.assertTrue(value["distribution"]["apt_signature_verification_required"])
        self.assertTrue(value["reproducibility"]["byte_identical_iso_required"])
        self.assertEqual(value["reproducibility"]["independent_work_directories"], 2)
        self.assertFalse(value["scope_boundary"]["effect_ack_done"])
        excluded = set(value["scope_boundary"]["excluded"])
        self.assertTrue({"atari", "m68000", "transputer", "universal_terminal", "temdd_runtime", "public_release"} <= excluded)

    def test_build_binds_exact_source_and_deterministic_time(self):
        text = BUILD.read_text()
        self.assertIn("exact source HEAD mismatch", text)
        self.assertIn("git -C \"$ROOT\" rev-parse 'HEAD^{tree}'", text)
        self.assertIn("git -C \"$ROOT\" show -s --format=%ct \"$SHA\"", text)
        self.assertIn("export SOURCE_DATE_EPOCH", text)
        self.assertIn("--mirror-bootstrap \"$SNAPSHOT\"", text)
        self.assertIn("Acquire::Check-Valid-Until=false", text)
        self.assertIn("--security false", text)
        self.assertIn("--updates false", text)
        self.assertIn("QIKVRT_REFERENCE_LINUX_BOOT_OK", text)
        self.assertIn('"effect_ack_done": false', text)

    def test_minimal_build_does_not_pull_later_reference_layers(self):
        packages = json.loads(CONTRACT.read_text())["distribution"]["packages"]
        forbidden = ("hatari", "firefox", "xfce", "podman", "codex", "pharo", "qemu-user")
        for token in forbidden:
            self.assertFalse(any(token in package for package in packages), token)

    def test_rebuild_verifier_accepts_only_identical_bytes_and_subject(self):
        spec = importlib.util.spec_from_file_location("qikvrt_ref_verify", VERIFY)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        payload = b"synthetic iso bytes"
        base = {
            "schema": "qikvrt.reference-linux-build-receipt.v1",
            "source_sha": "a" * 40,
            "source_tree": "b" * 40,
            "source_date_epoch": 1,
            "contract_sha256": "c" * 64,
            "snapshot": "snapshot",
            "toolchain": {"live_build": "v", "xorriso": "x", "mksquashfs": "s", "debootstrap": "d"},
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            ia, ib = root / "a.iso", root / "b.iso"
            ra, rb = root / "a.json", root / "b.json"
            ia.write_bytes(payload); ib.write_bytes(payload)
            ra.write_text(json.dumps(base)); rb.write_text(json.dumps(base))
            result = module.verify(ia, ra, ib, rb)
            self.assertTrue(result["rebuild_sha256_match"])
            ib.write_bytes(payload + b"drift")
            with self.assertRaisesRegex(ValueError, "bind actual ISO bytes|REBUILD_SHA256_MATCH"):
                module.verify(ia, ra, ib, rb)
            ib.write_bytes(payload)
            drift = dict(base, source_sha="d" * 40)
            rb.write_text(json.dumps(drift))
            with self.assertRaisesRegex(ValueError, "source_sha"):
                module.verify(ia, ra, ib, rb)

    def test_workflow_performs_two_builds_and_bios_boot(self):
        text = WORKFLOW.read_text()
        self.assertIn("QIKVRT_REFERENCE_WORK: ${{ runner.temp }}/qikvrt-ref-a", text)
        self.assertIn("QIKVRT_REFERENCE_WORK: ${{ runner.temp }}/qikvrt-ref-b", text)
        self.assertIn("verify-rebuild.py", text)
        self.assertIn("-boot order=d", text)
        self.assertIn("-cdrom out/qikvrt-reference-linux-amd64.iso", text)
        self.assertIn("QIKVRT_REFERENCE_LINUX_BOOT_OK source_sha=${QIKVRT_EXACT_SHA}", text)
        self.assertNotIn("hatari", text.lower())


if __name__ == "__main__":
    unittest.main()

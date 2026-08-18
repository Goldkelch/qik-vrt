import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "tools" / "qikvrt_universal_understanding_ansic.c"
LOWER = ROOT / "tools" / "qikvrt_metagrammar_m68000_lower_ansic.c"
EMIT = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"


class UniversalUnderstandingAnsiCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.front = Path(cls.tmp.name) / "universal-front"
        cls.lower = Path(cls.tmp.name) / "m68000-lower"
        cls.emit = Path(cls.tmp.name) / "m68000-emit"
        for source, target in [(FRONT, cls.front), (LOWER, cls.lower), (EMIT, cls.emit)]:
            subprocess.run(
                [
                    "cc",
                    "-std=c89",
                    "-pedantic-errors",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(source),
                    "-o",
                    str(target),
                ],
                check=True,
                cwd=ROOT,
            )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def source(
        self,
        *,
        kind="OBSERVE",
        rid="r1",
        scheme="repo",
        identity="Goldkelch/qik-vrt",
        version=None,
        subject_state=None,
        intent="OBSERVE terminal",
        auth_state="BOUND",
        auth_id="po-1",
        evid_type="HEAD",
        evid_digest=None,
        state="OBSERVED",
        effect_state="NONE",
        effect_id="none",
        next_action="REOBSERVE",
        proof=None,
        cause="-",
    ):
        version = version or "a" * 40
        subject_state = subject_state or "b" * 40
        evid_digest = evid_digest or "c" * 64
        proof = proof or "d" * 64
        return (
            "QIKU1\n"
            f"KIND {kind}\n"
            f"RID {rid}\n"
            f"SUBJECT {scheme} {identity} {version} {subject_state}\n"
            f"INTENT {intent}\n"
            f"AUTH {auth_state} {auth_id}\n"
            f"EVID {evid_type} {evid_digest}\n"
            f"STATE {state}\n"
            f"EFFECT {effect_state} {effect_id}\n"
            f"NEXT {next_action}\n"
            f"PROOF {proof}\n"
            f"CAUSE {cause}\n"
            "END\n"
        )

    def run_front(self, text, target=False):
        argv = [str(self.front)]
        if target:
            argv.append("--target-megast")
        return subprocess.run(argv, input=text, text=True, capture_output=True, cwd=ROOT)

    def target_bytes(self, text):
        front = self.run_front(text, target=True)
        self.assertEqual(front.returncode, 0, front.stderr)
        lower = subprocess.run(
            [str(self.lower)], input=front.stdout.encode("ascii"), capture_output=True, cwd=ROOT
        )
        self.assertEqual(lower.returncode, 0, lower.stderr)
        emit = subprocess.run([str(self.emit)], input=lower.stdout, capture_output=True, cwd=ROOT)
        self.assertEqual(emit.returncode, 0, emit.stderr)
        return emit.stdout

    def test_universal_frontend_accepts_non_repository_subject(self):
        r = self.run_front(
            self.source(
                scheme="document",
                identity="contract-17",
                version="v3",
                subject_state="reviewed",
                next_action="HOLD",
            )
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SUBJECT_SCHEME=document", r.stdout)
        self.assertIn("TARGET_PROFILE=UNIVERSAL_FRONTEND_V1", r.stdout)

    def test_cause_is_explicit_and_preserved(self):
        r = self.run_front(self.source(rid="later", cause="earlier", next_action="HOLD"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("CAUSE=earlier", r.stdout)

    def test_megast_reobserve_compiles_to_existing_exact_bytes(self):
        self.assertEqual(self.target_bytes(self.source(next_action="REOBSERVE")), bytes.fromhex("70024e75"))

    def test_megast_noop_compiles_to_existing_exact_bytes(self):
        self.assertEqual(self.target_bytes(self.source(next_action="NOOP")), bytes.fromhex("70004e75"))

    def test_megast_requires_repository_adapter(self):
        r = self.run_front(
            self.source(scheme="document", identity="contract-17", version="v3", subject_state="reviewed"),
            target=True,
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("MEGAST_REPO_BINDUNG_ERFORDERLICH", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_megast_requires_exact_head_and_tree(self):
        r = self.run_front(self.source(version="v3"), target=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("MEGAST_EXACT_HEAD_TREE_ERFORDERLICH", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_productive_intent_requires_bound_authority(self):
        r = self.run_front(
            self.source(intent="EXECUTE mutation", auth_state="MISSING", next_action="HOLD")
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("PRODUKTIVE_ABSICHT_OHNE_AUTORITAET", r.stderr)

    def test_unknown_cannot_drive_productive_intent(self):
        r = self.run_front(self.source(intent="EXECUTE mutation", state="UNKNOWN", next_action="HOLD"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("UNKNOWN_DARF_NICHT_WIRKEN", r.stderr)

    def test_nonbound_authority_cannot_select_productive_next_action(self):
        r = self.run_front(
            self.source(intent="OBSERVE terminal", auth_state="MISSING", next_action="EXECUTE")
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("UNBEFUGTE_FORTSETZUNG", r.stderr)

    def test_acknowledged_effect_requires_ack_kind(self):
        r = self.run_front(self.source(effect_state="ACKNOWLEDGED", effect_id="e1"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("ACKNOWLEDGED_ERFORDERT_ACK", r.stderr)

    def test_self_causation_is_rejected(self):
        r = self.run_front(self.source(rid="same", cause="same"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("SELBSTKAUSALITAET", r.stderr)

    def test_megast_rejects_unsupported_productive_lowering(self):
        r = self.run_front(self.source(intent="EXECUTE mutation", next_action="EXECUTE"), target=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("MEGAST_AKTION_NICHT_UNTERSTUETZT", r.stderr)
        self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()

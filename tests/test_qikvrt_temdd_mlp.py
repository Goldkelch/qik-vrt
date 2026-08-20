import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "mlp" / "TEMDD_MLP_EVENT_MODEL_V1.json"
ASM = ROOT / "runtime" / "megast" / "mlp_kernel_68000.s"
ATARI_C = ROOT / "runtime" / "megast" / "mlp_main_ansic.c"
HOST_C = ROOT / "runtime" / "host" / "mlp_host_ansic.c"

EXPECTED_FRAME = (
    b"QIKMLP1\r\n"
    b"PROGRAM MLP\r\n"
    b"ACTION OPEN_FIREFOX\r\n"
    b"STATE REQUESTED\r\n"
    b"AUTHORITY MISSING\r\n"
    b"EFFECT REQUESTED\r\n"
    b"END\r\n"
)


class TEMDDMLPTests(unittest.TestCase):
    def test_event_model_preserves_effect_distinctions(self):
        data = json.loads(MODEL.read_text(encoding="utf-8"))
        self.assertEqual(data["method"], "TEMDD")
        self.assertIn("REQUESTED != EXECUTED", data["distinctions"])
        self.assertIn("EXECUTED != OBSERVED", data["distinctions"])
        self.assertIn("OBSERVED != ACKNOWLEDGED", data["distinctions"])
        self.assertEqual(data["safety"]["default"], "HOLD")
        self.assertFalse(data["safety"]["effect_ack_done_claim"])

    def test_assembly_kernel_is_exact_request_authority_capsule(self):
        text = ASM.read_text(encoding="utf-8").lower()
        self.assertIn("moveq   #3,d1", text)
        self.assertIn("moveq   #1,d2", text)
        self.assertIn("moveq   #3,d0", text)
        self.assertIn("7203740170034e75", MODEL.read_text(encoding="utf-8"))

    def test_ansic_sources_compile_strictly(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            subprocess.run(
                ["cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
                 "-c", str(ATARI_C), "-o", str(td / "mlp_main.o")],
                cwd=ROOT, check=True,
            )
            subprocess.run(
                ["cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
                 str(HOST_C), "-o", str(td / "mlp-host")],
                cwd=ROOT, check=True,
            )

    def test_host_rejects_noncanonical_request(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            exe = td / "mlp-host"
            subprocess.run(
                ["cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
                 str(HOST_C), "-o", str(exe)], cwd=ROOT, check=True,
            )
            request = td / "MLP.OPEN"
            receipt = td / "MLP.HOST"
            request.write_bytes(b"OPEN FIREFOX\n")
            run = subprocess.run([str(exe), str(request), str(receipt)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertFalse(receipt.exists())

    def test_host_launch_receipt_does_not_claim_observation_or_ack(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            exe = td / "mlp-host"
            subprocess.run(
                ["cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
                 str(HOST_C), "-o", str(exe)], cwd=ROOT, check=True,
            )
            fakebin = td / "bin"
            fakebin.mkdir()
            fake_python = fakebin / "python3"
            fake_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)
            request = td / "MLP.OPEN"
            receipt = td / "MLP.HOST"
            request.write_bytes(EXPECTED_FRAME)
            env = dict(os.environ)
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            run = subprocess.run([str(exe), str(request), str(receipt)], cwd=ROOT, env=env,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            text = receipt.read_text(encoding="ascii")
            self.assertIn("HOST_STATE BROWSER_LAUNCH_EXECUTED", text)
            self.assertIn("OBSERVED false", text)
            self.assertIn("ACKNOWLEDGED false", text)
            self.assertIn("NEXT REOBSERVE", text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_proof_object_manifest as verifier  # noqa: E402


class ProofObjectManifestHardeningTests(unittest.TestCase):
    """Exercise fail-closed proof-object persistence and matrix coverage."""

    def _write(self, root: Path, relative: str, value: str | bytes) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            path.write_bytes(value)
        else:
            path.write_text(value, encoding="utf-8")

    def _fixture(self, root: Path) -> Path:
        matrix_claims = [
            {
                "id": "EA-LEAN-001",
                "status": "KERNEL_PROVED",
                "proof_constants": ["QIKVRT.EffectAck.V1.demoProof"],
                "registry_constant": "QIKVRT.EffectAck.V1.Claims.Demo",
                "source_path": "QIKVRTEffectAck/Demo.lean",
            }
        ]
        matrix_claims.extend(
            {
                "id": f"EA-OPEN-{index:03d}",
                "status": "OPEN",
                "proof_constants": [],
                "registry_constant": None,
                "source_path": None,
            }
            for index in range(1, 15)
        )
        self._write(
            root,
            "effect_ack/DRAFT01_CLAIM_MATRIX.json",
            json.dumps(
                {
                    "schema": verifier.EXPECTED_MATRIX_SCHEMA,
                    "claims": matrix_claims,
                }
            ),
        )

        self._write(
            root,
            "QIKVRTEffectAck/Demo.lean",
            (
                "namespace QIKVRT.EffectAck.V1\n"
                "theorem demoProof : True := by trivial\n"
                "end QIKVRT.EffectAck.V1\n"
            ),
        )
        self._write(
            root,
            "QIKVRTEffectAck/Claims.lean",
            (
                "namespace QIKVRT.EffectAck.V1.Claims\n"
                "def Demo : True := trivial\n"
                "end QIKVRT.EffectAck.V1.Claims\n"
            ),
        )
        self._write(
            root,
            "QIKVRTFormalization/Process/ShiftInvariance.lean",
            (
                "namespace QIKVRT.V2.Trajectory\n"
                "def GAT003Statement : Prop := True\n"
                "theorem GAT003_checked : GAT003Statement := trivial\n"
                "end QIKVRT.V2.Trajectory\n"
            ),
        )
        self._write(
            root,
            "QIKVRTFormalization/Claims/Batch04.lean",
            (
                "namespace QIKVRT.V2.Claims\n"
                "def GAT003 : True := trivial\n"
                "end QIKVRT.V2.Claims\n"
            ),
        )
        self._write(
            root,
            "QIKVRTFormalization/Escape/FiniteStages.lean",
            (
                "namespace QIKVRT.V2.Escape\n"
                "def ESC003AStatement : Prop := True\n"
                "theorem ESC003A_checked : ESC003AStatement := trivial\n"
                "end QIKVRT.V2.Escape\n"
            ),
        )
        self._write(
            root,
            "QIKVRTFormalization/Claims/Batch05.lean",
            (
                "namespace QIKVRT.V2.Claims\n"
                "def ESC003A : True := trivial\n"
                "end QIKVRT.V2.Claims\n"
            ),
        )

        compiled = {
            ".lake/build/lib/lean/QIKVRTFormalization/Process/ShiftInvariance.olean",
            ".lake/build/lib/lean/QIKVRTFormalization/Escape/FiniteStages.olean",
            ".lake/build/lib/lean/QIKVRTEffectAck/Demo.olean",
            ".lake/build/lib/lean/QIKVRTEffectAck/Claims.olean",
            verifier.SCOPE_ANCHOR,
        }
        for index, relative in enumerate(sorted(compiled)):
            self._write(root, relative, f"olean-{index}".encode())

        effect_claims = [
            {
                "claimId": "EA-LEAN-001",
                "bindingKind": "KERNEL_PROOF",
                "proofConstants": ["QIKVRT.EffectAck.V1.demoProof"],
                "registryConstant": "QIKVRT.EffectAck.V1.Claims.Demo",
                "sourcePath": "QIKVRTEffectAck/Demo.lean",
                "compiledObjects": [
                    ".lake/build/lib/lean/QIKVRTEffectAck/Demo.olean",
                    ".lake/build/lib/lean/QIKVRTEffectAck/Claims.olean",
                ],
            }
        ]
        effect_claims.extend(
            {
                "claimId": f"EA-OPEN-{index:03d}",
                "bindingKind": "SCOPE_BOUNDARY",
                "proofConstants": [],
                "registryConstant": None,
                "sourcePath": None,
                "compiledObjects": [verifier.SCOPE_ANCHOR],
            }
            for index in range(1, 15)
        )
        manifest = {
            "schema": verifier.EXPECTED_SCHEMA,
            "policy": {
                "cacheMayAccelerate": True,
                "cacheMayReplaceKernelVerification": False,
                "cacheMissRequiresRebuild": True,
                "sourceOrToolchainChangeInvalidates": True,
            },
            "objects": [
                {
                    "claimId": "GAT-003",
                    "statementConstant": "QIKVRT.V2.Trajectory.GAT003Statement",
                    "proofConstant": "QIKVRT.V2.Trajectory.GAT003_checked",
                    "registryConstant": "QIKVRT.V2.Claims.GAT003",
                    "sourcePath": "QIKVRTFormalization/Process/ShiftInvariance.lean",
                    "registrySourcePath": "QIKVRTFormalization/Claims/Batch04.lean",
                    "compiledObject": ".lake/build/lib/lean/QIKVRTFormalization/Process/ShiftInvariance.olean",
                    "status": "KERNEL_CHECK_REQUIRED_ON_EVERY_DISTINCT_INPUT_SET",
                },
                {
                    "claimId": "ESC-003A",
                    "statementConstant": "QIKVRT.V2.Escape.ESC003AStatement",
                    "proofConstant": "QIKVRT.V2.Escape.ESC003A_checked",
                    "registryConstant": "QIKVRT.V2.Claims.ESC003A",
                    "sourcePath": "QIKVRTFormalization/Escape/FiniteStages.lean",
                    "registrySourcePath": "QIKVRTFormalization/Claims/Batch05.lean",
                    "compiledObject": ".lake/build/lib/lean/QIKVRTFormalization/Escape/FiniteStages.olean",
                    "status": "KERNEL_CHECK_REQUIRED_ON_EVERY_DISTINCT_INPUT_SET",
                },
            ],
            "effectAck": {
                "claimMatrix": "effect_ack/DRAFT01_CLAIM_MATRIX.json",
                "registrySourcePath": "QIKVRTEffectAck/Claims.lean",
                "claims": effect_claims,
            },
        }
        manifest_path = root / "proofs/PROOF_OBJECT_MANIFEST.json"
        self._write(root, "proofs/PROOF_OBJECT_MANIFEST.json", json.dumps(manifest))
        return manifest_path

    def test_runtime_evidence_contains_regular_object_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._fixture(root)
            evidence = verifier.verify(root, manifest)
            self.assertEqual(evidence["effectAckClaimCount"], 15)
            self.assertFalse(evidence["cache_replaces_kernel"])
            lean_claim = next(
                item
                for item in evidence["effectAckClaims"]
                if item["claimId"] == "EA-LEAN-001"
            )
            self.assertEqual(
                lean_claim["sourceSha256"],
                hashlib.sha256(
                    (root / "QIKVRTEffectAck/Demo.lean").read_bytes()
                ).hexdigest(),
            )
            objects = {item["path"]: item for item in evidence["compiledObjects"]}
            demo = objects[
                ".lake/build/lib/lean/QIKVRTEffectAck/Demo.olean"
            ]
            self.assertEqual(
                demo["sha256"],
                hashlib.sha256(
                    (
                        root
                        / ".lake/build/lib/lean/QIKVRTEffectAck/Demo.olean"
                    ).read_bytes()
                ).hexdigest(),
            )
            self.assertIn("EA-LEAN-001", demo["claimIds"])

    def test_missing_compiled_object_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._fixture(root)
            (
                root
                / ".lake/build/lib/lean/QIKVRTEffectAck/Demo.olean"
            ).unlink()
            with self.assertRaisesRegex(
                verifier.VerificationError, "compiledObject is missing"
            ):
                verifier.verify(root, manifest)

    def test_missing_effect_ack_coverage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._fixture(root)
            value = json.loads(manifest.read_text(encoding="utf-8"))
            value["effectAck"]["claims"].pop()
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(
                verifier.VerificationError,
                "EFFECT_ACK manifest coverage differs",
            ):
                verifier.verify(root, manifest)

    def test_manifest_constants_must_equal_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._fixture(root)
            value = json.loads(manifest.read_text(encoding="utf-8"))
            value["effectAck"]["claims"][0]["proofConstants"] = []
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(
                verifier.VerificationError,
                "proofConstants differ from the claim matrix",
            ):
                verifier.verify(root, manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)

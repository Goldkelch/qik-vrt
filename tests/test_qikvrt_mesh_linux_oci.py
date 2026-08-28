# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import gzip
import hashlib
import json
import pathlib
import copy
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_mesh_linux_oci as builder


EPOCH = 1787875200


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_member(archive: tarfile.TarFile, name: str):
    extracted = archive.extractfile(name)
    if extracted is None:
        raise AssertionError("archive member is not a regular file: " + name)
    return json.loads(extracted.read().decode("utf-8"))


class MeshLinuxOciBuilderTests(unittest.TestCase):
    def test_deterministic_offline_image_and_native_self_test(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first_temp,
            tempfile.TemporaryDirectory() as second_temp,
        ):
            first = pathlib.Path(first_temp) / "out"
            second = pathlib.Path(second_temp) / "out"
            first_receipt = builder.build(first, EPOCH)
            second_receipt = builder.build(second, EPOCH)

            for artifact in (
                "qikvrt-meshd",
                "qikvrt-mesh-linux-oci.tar",
                "qikvrt-mesh-linux-docker.tar",
                "qikvrt-mesh-linux-receipt.json",
            ):
                self.assertEqual(
                    (first / artifact).read_bytes(),
                    (second / artifact).read_bytes(),
                    artifact + " must rebuild byte-for-byte",
                )
            self.assertEqual(
                first_receipt["artifact_digests"],
                second_receipt["artifact_digests"],
            )

            native = subprocess.run(
                [str(first / "qikvrt-meshd"), "--self-test"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(native.returncode, 0, native.stderr)
            self.assertEqual(
                first_receipt["artifact_digests"]["qikvrt-meshd"]["sha256"],
                sha256((first / "qikvrt-meshd").read_bytes()),
            )

            self._assert_language_receipts(first_receipt)
            self._assert_oci_layout(first, first_receipt)
            self._assert_docker_archive(first, first_receipt)
            self._assert_closed_effect_boundary(first_receipt)
            with mock.patch.object(
                builder.subprocess,
                "run",
                side_effect=AssertionError("verify must not execute artifacts"),
            ):
                verification = builder.verify(first)
            self.assertTrue(verification["verified"])
            self.assertEqual(
                verification["native_self_test"],
                "NOT_EXECUTED_UNTRUSTED_BOUNDARY",
            )
            self.assertFalse(verification["network_operation_requested"])
            self.assertFalse(verification["registry_contacted"])
            self.assertFalse(verification["general_effect_ack_done"])
            self._assert_malicious_receipt_claim_rejected(second)
            self._assert_platform_drift_rejected(first, first_receipt, second)

    def _assert_language_receipts(self, receipt: dict) -> None:
        self.assertTrue(receipt["single_source_profile"])
        self.assertEqual(set(receipt["manifestations"]), {"c89", "c90"})
        for standard in ("c89", "c90"):
            manifestation = receipt["manifestations"][standard]
            self.assertEqual(manifestation["standard_flag"], "-std=" + standard)
            self.assertEqual(manifestation["syntax_check"]["exit_code"], 0)
            self.assertEqual(manifestation["static_compile"]["exit_code"], 0)
            self.assertIn("-static", manifestation["static_compile"]["command"])
            self.assertFalse(manifestation["static_compile"]["elf"]["pt_dynamic"])
            self.assertFalse(manifestation["static_compile"]["elf"]["pt_interp"])
            self.assertEqual(manifestation["self_test"]["exit_code"], 0)

    def _assert_oci_layout(self, output: pathlib.Path, receipt: dict) -> None:
        layout = output / "qikvrt-mesh-linux-oci"
        self.assertEqual(
            json.loads((layout / "oci-layout").read_text(encoding="utf-8")),
            {"imageLayoutVersion": "1.0.0"},
        )
        index = json.loads((layout / "index.json").read_text(encoding="utf-8"))
        descriptor = index["manifests"][0]
        manifest_bytes = self._assert_blob_descriptor(layout, descriptor)
        manifest = json.loads(manifest_bytes)
        config_bytes = self._assert_blob_descriptor(layout, manifest["config"])
        layer_bytes = self._assert_blob_descriptor(layout, manifest["layers"][0])
        config = json.loads(config_bytes)
        self.assertEqual(config["config"]["User"], "65532:65532")
        self.assertEqual(config["config"]["Entrypoint"], ["/usr/bin/qikvrt-meshd"])
        self.assertEqual(
            config["config"]["Cmd"],
            ["--bind", "0.0.0.0", "--port", "8080"],
        )
        self.assertEqual(config["config"]["ExposedPorts"], {"8080/tcp": {}})
        rootfs = gzip.decompress(layer_bytes)
        self.assertEqual(
            config["rootfs"]["diff_ids"], ["sha256:" + sha256(rootfs)]
        )
        with tempfile.TemporaryFile() as temporary:
            temporary.write(rootfs)
            temporary.seek(0)
            with tarfile.open(fileobj=temporary, mode="r:") as rootfs_archive:
                names = set(rootfs_archive.getnames())
                self.assertIn("usr/bin/qikvrt-meshd", names)
                self.assertIn("usr/share/qikvrt/CAPABILITY_BOUNDARY.json", names)
                member = rootfs_archive.extractfile("usr/bin/qikvrt-meshd")
                self.assertIsNotNone(member)
                assert member is not None
                self.assertEqual(
                    sha256(member.read()),
                    receipt["artifact_digests"]["qikvrt-meshd"]["sha256"],
                )
        oci_archive = (output / "qikvrt-mesh-linux-oci.tar").read_bytes()
        self.assertEqual(
            sha256(oci_archive),
            receipt["artifact_digests"]["qikvrt-mesh-linux-oci.tar"]["sha256"],
        )

    def _assert_blob_descriptor(self, layout: pathlib.Path, descriptor: dict) -> bytes:
        algorithm, digest = descriptor["digest"].split(":", 1)
        self.assertEqual(algorithm, "sha256")
        data = (layout / "blobs" / algorithm / digest).read_bytes()
        self.assertEqual(len(data), descriptor["size"])
        self.assertEqual(sha256(data), digest)
        return data

    def _assert_docker_archive(self, output: pathlib.Path, receipt: dict) -> None:
        archive_bytes = (output / "qikvrt-mesh-linux-docker.tar").read_bytes()
        self.assertEqual(
            sha256(archive_bytes),
            receipt["artifact_digests"]["qikvrt-mesh-linux-docker.tar"]["sha256"],
        )
        with tempfile.TemporaryFile() as temporary:
            temporary.write(archive_bytes)
            temporary.seek(0)
            with tarfile.open(fileobj=temporary, mode="r:") as archive:
                manifest = json_member(archive, "manifest.json")
                self.assertEqual(manifest[0]["RepoTags"], ["qikvrt/mesh-linux:prototype"])
                self.assertEqual(len(manifest[0]["Layers"]), 1)
                config_name = manifest[0]["Config"]
                config_file = archive.extractfile(config_name)
                self.assertIsNotNone(config_file)
                assert config_file is not None
                config_bytes = config_file.read()
                self.assertEqual(sha256(config_bytes), config_name[:-5])
                layer_name = manifest[0]["Layers"][0]
                self.assertIn(layer_name, archive.getnames())

    def _assert_closed_effect_boundary(self, receipt: dict) -> None:
        boundary = receipt["capability_boundary"]
        self.assertEqual(boundary["external_effect"], "NONE_BUILD_AND_LOCAL_SELF_TEST_ONLY")
        self.assertFalse(boundary["network_operation_requested"])
        self.assertFalse(boundary["registry_contacted"])
        self.assertFalse(boundary["publication_performed"])
        self.assertFalse(boundary["deployment_performed"])
        self.assertFalse(boundary["container_execution_observed"])
        self.assertFalse(boundary["unauthenticated_http_ordinary_release"])
        self.assertTrue(boundary["http_core_done_is_candidate_only"])
        self.assertFalse(boundary["general_effect_ack_done"])
        serialized = json.dumps(receipt, sort_keys=True).lower()
        for forbidden in (
            "password",
            "credential",
            "private_key",
            "access_token",
            "schedule",
        ):
            self.assertNotIn(forbidden, serialized)
        source = pathlib.Path(builder.__file__).read_text(encoding="utf-8").lower()
        for forbidden_import in ("import socket", "import urllib", "import requests"):
            self.assertNotIn(forbidden_import, source)

    def _assert_malicious_receipt_claim_rejected(
        self, output: pathlib.Path
    ) -> None:
        receipt_path = output / "qikvrt-mesh-linux-receipt.json"
        original = receipt_path.read_bytes()
        malicious = json.loads(original)
        malicious["capability_boundary"]["general_effect_ack_done"] = True
        receipt_path.chmod(0o644)
        receipt_path.write_bytes(builder._canonical_json(malicious))
        with self.assertRaisesRegex(builder.BuildError, "capability boundary"):
            builder.verify(output)
        receipt_path.write_bytes(original)
        receipt_path.chmod(0o444)

    def _assert_platform_drift_rejected(
        self,
        source: pathlib.Path,
        source_receipt: dict,
        temporary_root: pathlib.Path,
    ) -> None:
        drift = temporary_root / "platform-drift"
        drift.mkdir()
        shutil.copyfile(source / "qikvrt-meshd", drift / "qikvrt-meshd")
        (drift / "qikvrt-meshd").chmod(0o555)
        source_layout = source / "qikvrt-mesh-linux-oci"
        index = json.loads((source_layout / "index.json").read_bytes())
        manifest_digest = index["manifests"][0]["digest"].split(":", 1)[1]
        manifest = json.loads(
            (source_layout / "blobs/sha256" / manifest_digest).read_bytes()
        )
        config_digest = manifest["config"]["digest"].split(":", 1)[1]
        layer_digest = manifest["layers"][0]["digest"].split(":", 1)[1]
        config = json.loads(
            (source_layout / "blobs/sha256" / config_digest).read_bytes()
        )
        layer = (source_layout / "blobs/sha256" / layer_digest).read_bytes()
        config["architecture"] = "arm64"
        config["variant"] = "v8"
        config_bytes = builder._canonical_json(config)
        oci_archive, oci_metadata = builder._oci_layout(
            drift,
            config_bytes,
            layer,
            "linux",
            "arm64",
            "v8",
            EPOCH,
        )
        rootfs = gzip.decompress(layer)
        docker_archive = builder._docker_archive(config_bytes, rootfs, EPOCH)
        builder._write_bytes(
            drift / "qikvrt-mesh-linux-oci.tar", oci_archive, 0o444
        )
        builder._write_bytes(
            drift / "qikvrt-mesh-linux-docker.tar", docker_archive, 0o444
        )
        receipt = copy.deepcopy(source_receipt)
        receipt["runtime_image"]["architecture"] = "arm64"
        receipt["runtime_image"]["variant"] = "v8"
        receipt["runtime_image"]["oci"] = oci_metadata
        receipt["artifact_digests"]["qikvrt-mesh-linux-oci.tar"] = {
            "bytes": len(oci_archive),
            "sha256": sha256(oci_archive),
        }
        receipt["artifact_digests"]["qikvrt-mesh-linux-docker.tar"] = {
            "bytes": len(docker_archive),
            "sha256": sha256(docker_archive),
        }
        builder._write_bytes(
            drift / "qikvrt-mesh-linux-receipt.json",
            builder._canonical_json(receipt),
            0o444,
        )
        with self.assertRaisesRegex(builder.BuildError, "ELF machine"):
            builder.verify(drift)


if __name__ == "__main__":
    unittest.main()

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import hashlib
import json
import pathlib
import tarfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "distribution/qikvrt-mesh-appliance-v1-source.tar.gz"
DIGEST = "665bbbaeeebee250e64faa900075d72f345069b0eac2ecaa7682488dc9e4c005"


class VirtualApplianceBundleTests(unittest.TestCase):
    def test_bundle_digest_and_gzip_timestamp(self):
        data = ARCHIVE.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), DIGEST)
        self.assertEqual(int.from_bytes(data[4:8], "little"), 0)

    def test_tar_is_canonical_and_complete(self):
        required = {
            "qikvrt-mesh-appliance-v1/APPLIANCE_LOCK.json",
            "qikvrt-mesh-appliance-v1/Dockerfile",
            "qikvrt-mesh-appliance-v1/entrypoint.sh",
            "qikvrt-mesh-appliance-v1/launch-linux.sh",
            "qikvrt-mesh-appliance-v1/launch-macos.sh",
            "qikvrt-mesh-appliance-v1/launch-windows.ps1",
            "qikvrt-mesh-appliance-v1/live-build/auto/config",
            "qikvrt-mesh-appliance-v1/live-build/config/hooks/normal/0100-qikvrt.hook.chroot",
        }
        with tarfile.open(ARCHIVE, "r:gz") as tf:
            members = tf.getmembers()
            names = {m.name for m in members}
            self.assertTrue(required <= names)
            self.assertEqual(len(names), len(members))
            for member in members:
                self.assertFalse(pathlib.PurePosixPath(member.name).is_absolute())
                self.assertNotIn("..", pathlib.PurePosixPath(member.name).parts)
                self.assertEqual(member.mtime, 0)
                self.assertEqual((member.uid, member.gid), (0, 0))
            lock = json.load(tf.extractfile("qikvrt-mesh-appliance-v1/APPLIANCE_LOCK.json"))
        self.assertFalse(lock["claims"]["physical_megast_execution_observed"])
        self.assertFalse(lock["claims"]["general_effect_ack_done"])

    def test_policy_and_workflow_boundaries(self):
        policy = json.loads((ROOT / "policy/QIKVRT_VIRTUAL_APPLIANCE_V1.json").read_text())
        self.assertEqual(policy["source_bundle"]["sha256"], DIGEST)
        self.assertFalse(policy["delivery"]["mutable_latest_tag"])
        self.assertFalse(policy["effect_ack_profile"]["ietf_adoption_claimed"])
        workflow = (ROOT / ".github/workflows/qikvrt_virtual_appliance.yml").read_text()
        self.assertIn("github.event_name == 'push'", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("qikvrt-mesh-live-v1-amd64.iso", workflow)
        self.assertNotIn(":latest", workflow)


if __name__ == "__main__":
    unittest.main()

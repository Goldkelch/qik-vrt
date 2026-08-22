import hashlib
import subprocess
import unittest

from tools.qikvrt_bit_audit import audit


class BitAuditTests(unittest.TestCase):
    def test_audit_binds_exact_head_and_tree(self):
        receipt, inventory = audit("HEAD")
        self.assertEqual(receipt["head_sha"], subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip())
        self.assertEqual(receipt["tree_sha"], subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip())
        self.assertEqual(receipt["entry_count"], len(inventory))
        self.assertEqual(receipt["hash_algorithm"], "sha256")
        self.assertTrue(receipt["canonical_index_sha256"])

    def test_known_file_digest_is_blob_byte_digest(self):
        receipt, inventory = audit("HEAD")
        by_path = {item["path"]: item for item in inventory}
        path = "policy/PERFECT_OPTIMUM_V1.json"
        blob = subprocess.check_output(["git", "show", f"HEAD:{path}"])
        self.assertEqual(by_path[path]["sha256"], hashlib.sha256(blob).hexdigest())
        self.assertFalse(receipt["external_gitlink_bytes_claimed"])


if __name__ == "__main__":
    unittest.main()

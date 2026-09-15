import dataclasses
import unittest

from src.qikvrt.recursive_evidence_router import RouteReceipt


class ReceiptImmutabilityTest(unittest.TestCase):
    def test_route_receipt_is_frozen(self):
        receipt = RouteReceipt("x", (), True, ())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            receipt.requested_scope = "changed"


if __name__ == "__main__":
    unittest.main()

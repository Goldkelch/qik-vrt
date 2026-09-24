import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class EpistemicSpiralTransportLayerTests(unittest.TestCase):
    def test_receipt_schemas_are_distinct(self):
        serialization=(ROOT/"tools/qikvrt_epistemic_spiral_roundtrip.py").read_text(encoding="utf-8")
        transputer=(ROOT/"tools/qikvrt_epistemic_spiral_transputer_roundtrip.py").read_text(encoding="utf-8")
        cloud=(ROOT/".github/workflows/qikvrt_cloud_transputer_materialization_v1.yml").read_text(encoding="utf-8")
        witness=(ROOT/"distribution/qikvrt-megast/runtime-witness.py").read_text(encoding="utf-8")
        self.assertIn("qikvrt_epistemic_spiral_serialization_receipt_v1",serialization)
        self.assertIn("qikvrt_epistemic_spiral_transputer_receipt_v1",transputer)
        self.assertIn("qikvrt_epistemic_spiral_linux_readback_receipt_v1",witness)
        self.assertIn("qikvrt_epistemic_spiral_oci_readback_receipt_v1",cloud)
    def test_only_terminal_tree_is_canonical_authority(self):
        transputer=(ROOT/"tools/qikvrt_epistemic_spiral_transputer_roundtrip.py").read_text(encoding="utf-8")
        policy=json.loads((ROOT/"policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text(encoding="utf-8"))
        self.assertIn("docs/terminal/epistemic-spiral",transputer)
        self.assertNotIn("docs/assets/epistemic-spiral",transputer)
        self.assertEqual(policy["terminal"]["epistemic_spiral"]["canonical_source_root"],"docs/terminal/epistemic-spiral")
    def test_delivery_requires_fresh_layer_receipts(self):
        request=json.loads((ROOT/"state/delivery/requests/AI_PERSONAL_FIREFOX_V1.json").read_text(encoding="utf-8"))
        required=set(request["effect_ack"]["fields"])
        self.assertTrue({"epistemic_spiral_transputer_receipt","epistemic_spiral_linux_readback_receipt","epistemic_spiral_oci_readback_receipt"}<=required)
        self.assertFalse(request["completion_claims"]["EFFECT_ACK_DONE"])
if __name__=="__main__": unittest.main()

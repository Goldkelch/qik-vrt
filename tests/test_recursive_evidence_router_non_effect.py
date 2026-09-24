import pathlib
import unittest


class NonEffectVocabularyTest(unittest.TestCase):
    def test_router_implementation_does_not_emit_effect_ack_done(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "src" / "qikvrt" / "recursive_evidence_router.py"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("EFFECT_ACK_DONE", text)


if __name__ == "__main__":
    unittest.main()

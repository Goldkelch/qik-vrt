import unittest

from tools.qikvrt_ied_regex_grammar import classify


VALID = '♾️ <=> "IED Intelligence Evidence Development q.e.d. Ingolf Lohmann" <=> ♾️ <=> Register 3 ist Fixpunkt! <=> . <=> 447 <=> 1 2 4-> 3️⃣ 4-> 5 6 7-> <=> 8Bit <=> 10. <=> . <=> Register 3 ist Fixpunkt! <=> ♾️'


class IEDRegexGrammarTest(unittest.TestCase):
    def test_exact_receipt_grammar_parses_without_claiming_effect(self):
        result = classify(VALID)
        self.assertTrue(result["matched"])
        self.assertEqual(result["state"], "PARSED")
        self.assertFalse(result["semantic_proof"])
        self.assertFalse(result["authority"])
        self.assertFalse(result["executed"])
        self.assertFalse(result["effect_ack"])

    def test_wrong_fixpoint_holds(self):
        result = classify(VALID.replace("Register 3 ist Fixpunkt!", "Register 2 ist Fixpunkt!", 1))
        self.assertFalse(result["matched"])
        self.assertEqual(result["state"], "HOLD")

    def test_missing_frame_holds(self):
        result = classify(VALID[:-2])
        self.assertFalse(result["matched"])
        self.assertEqual(result["state"], "HOLD")


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json"
CONTEXT = ROOT / "AI_CONTEXT.json"
AI = ROOT / "AI"
BOOTLOADER = ROOT / "tools/ai_runtime_bootloader.py"


class TestAIBootstrapKnowledgeCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        cls.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        cls.ai = AI.read_text(encoding="utf-8")
        cls.bootloader = BOOTLOADER.read_text(encoding="utf-8")

    def test_all_supplied_artifacts_are_inventoried(self):
        artifacts = self.corpus["source_artifacts"]
        self.assertEqual(len(artifacts), 20)
        self.assertEqual(len({item["name"] for item in artifacts}), 20)
        for item in artifacts:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(item["bytes"], 0)

    def test_audio_is_fail_closed(self):
        audio = [item for item in self.corpus["source_artifacts"] if item["media_type"] == "audio/mp4"]
        self.assertEqual(len(audio), 6)
        self.assertTrue(all(item["content_status"] == "UNTRANSCRIBED" for item in audio))
        policy = self.corpus["audio_policy"]
        self.assertFalse(policy["untranscribed_audio_may_supply_semantic_claims"])
        self.assertFalse(policy["title_may_be_used_as_transcript"])
        self.assertTrue(policy["human_acoustic_review_required_for_verbatim_verified"])

    def test_scientific_boundaries_are_noninflating(self):
        boundaries = self.corpus["scientific_boundaries"]
        for key in (
            "executable_world_formula_architecture_claim_equals_scientifically_established_nature_description",
            "lean_derivability_equals_physical_truth",
            "symbolic_similarity_equals_empirical_confirmation",
            "panpsychism_proved_by_process_model",
            "religious_or_esoteric_doctrine_confirmed_by_process_model",
            "retroactive_change_of_past_event",
        ):
            self.assertIs(boundaries[key], False)

    def test_required_ai_invariants_are_present(self):
        invariants = set(self.corpus["core_invariants"])
        self.assertIn("FORMAL_PROOF_IS_NOT_EMPIRICAL_CONFIRMATION", invariants)
        self.assertIn("ARTIFICIAL_COGNITION_IS_NOT_AN_AUTOMATIC_TRUTH_MACHINE", invariants)
        self.assertIn("HUMAN_AND_AI_CONTRIBUTIONS_REMAIN_SEPARATELY_ATTRIBUTABLE", invariants)
        self.assertIn("SELF_HEALING_MUST_NOT_BECOME_SELF_CONFIRMATION", invariants)

    def test_context_and_entrypoint_bind_corpus(self):
        required = self.context["required_read_order"]
        self.assertIn("docs/AI_BOOTSTRAP_KNOWLEDGE_CORPUS.md", required)
        self.assertIn("policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json", required)
        self.assertIn("SUPPLIED KNOWLEDGE CORPUS", self.ai)
        self.assertIn("UNTRANSCRIBED", self.ai)

    def test_bootloader_validates_corpus(self):
        self.assertIn("load_bootstrap_corpus", self.bootloader)
        self.assertIn("untranscribed_audio_semantic_claims_allowed", self.bootloader)
        self.assertIn("bootstrap knowledge corpus", self.bootloader)


if __name__ == "__main__":
    unittest.main()

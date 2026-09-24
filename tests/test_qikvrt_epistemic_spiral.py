import json, pathlib, unittest, xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[1]
ASSET=ROOT/"docs/assets/epistemic-spiral"
POLICY=ROOT/"policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json"

class EpistemicSpiralTests(unittest.TestCase):
    def test_svg_is_self_contained_vector(self):
        root=ET.parse(ASSET/"spiral.svg").getroot()
        self.assertTrue(root.tag.endswith("svg"))
        text=(ASSET/"spiral.svg").read_text(encoding="utf-8")
        self.assertNotIn("http://",text)
        self.assertNotIn("https://",text)
        self.assertIn("prefers-reduced-motion",text)

    def test_target_locales_match_firefox_policy(self):
        i18n=json.loads((ASSET/"i18n.json").read_text(encoding="utf-8"))
        policy=json.loads(POLICY.read_text(encoding="utf-8"))
        expected=set(policy["terminal"]["ui_localization"]["locales"])
        self.assertEqual(set(i18n["locales"]),expected)
        for locale,value in i18n["locales"].items():
            self.assertTrue(value["title"] and value["explanation"] and value["cosmos"] and value["boundary"],locale)
        self.assertEqual(i18n["translation_status"],"MACHINE_GENERATED_DRAFT_PENDING_LINGUISTIC_REVIEW")

    def test_ai_surface_uses_local_assets(self):
        page=(ROOT/"docs/AI/index.html").read_text(encoding="utf-8")
        for name in ("spiral.svg","i18n.json","spiral.js","spiral.css"):
            self.assertIn(name,page)
        self.assertIn("EVENT ≠ EFFECT ≠ EFFECT_ACK",page)
        self.assertNotIn("<script src=\"http",page)

    def test_serialized_carrier_fits_transputer_body(self):
        i18n=json.loads((ASSET/"i18n.json").read_text(encoding="utf-8"))
        manifest=json.loads((ASSET/"manifest.json").read_text(encoding="utf-8"))
        bundle={"schema":"qikvrt_epistemic_spiral_serialized_v1","manifest":manifest,
                "svg":(ASSET/"spiral.svg").read_text(encoding="utf-8"),"i18n":i18n}
        raw=json.dumps(bundle,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        self.assertLessEqual(len(raw),62784)
        self.assertEqual(json.loads(raw.decode())["manifest"]["schema"],"qikvrt_epistemic_spiral_carrier_v1")

if __name__=="__main__": unittest.main()

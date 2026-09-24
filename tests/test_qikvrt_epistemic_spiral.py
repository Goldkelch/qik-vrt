import json, pathlib, unittest, xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[1]
ASSET=ROOT/"docs/assets/epistemic-spiral"
POLICY=ROOT/"policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json"

class EpistemicSpiralTests(unittest.TestCase):
    def test_svg_is_self_contained_vector(self):
        root=ET.parse(ASSET/"spiral.svg").getroot()
        self.assertTrue(root.tag.endswith("svg"))
        text=(ASSET/"spiral.svg").read_text(encoding="utf-8")
        self.assertNotIn('href="http://',text)
        self.assertNotIn('href="https://',text)
        self.assertNotIn('url(http://',text)
        self.assertNotIn('url(https://',text)
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

    def test_firefox_and_virtualization_carriers_are_bound(self):
        firefox=json.loads((ROOT/"browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        matches=set(firefox["content_scripts"][0]["matches"])
        self.assertIn("http://127.0.0.1:8788/AI/*",matches)
        self.assertIn("https://goldkelch.github.io/qik-vrt/*",matches)
        for locale in json.loads((ASSET/"i18n.json").read_text(encoding="utf-8"))["locales"]:
            messages=json.loads((ROOT/f"browser/firefox/qikvrt-terminal/_locales/{locale}/messages.json").read_text(encoding="utf-8"))
            self.assertTrue(messages["spiral"]["message"],locale)

        build=(ROOT/"distribution/qikvrt-megast/build.sh").read_text(encoding="utf-8")
        session=(ROOT/"distribution/qikvrt-megast/qikvrt-megast-session.sh").read_text(encoding="utf-8")
        witness=(ROOT/"distribution/qikvrt-megast/runtime-witness.py").read_text(encoding="utf-8")
        docker=(ROOT/"deploy/universal-terminal/Dockerfile").read_text(encoding="utf-8")
        entry=(ROOT/"deploy/universal-terminal/entrypoint.sh").read_text(encoding="utf-8")
        nginx=(ROOT/"deploy/universal-terminal/nginx.conf").read_text(encoding="utf-8")
        self.assertIn("docs/assets/epistemic-spiral",build)
        self.assertIn("qikvrt-ai-ui.service",build)
        self.assertIn("http://127.0.0.1:8788/AI/",session)
        self.assertIn("epistemic-spiral-ai-surface-readback",witness)
        self.assertIn("QIKVRT_START_URL=about:blank",docker)
        self.assertIn('START_URL="${QIKVRT_START_URL:-about:blank}"',entry)
        self.assertIn("python3 -m http.server",entry)
        self.assertIn("root /opt/qikvrt/docs;",nginx)
        self.assertIn("X-QIKVRT-Surface",nginx)

    def test_delivery_contract_requires_roundtrip_receipts(self):
        request=json.loads((ROOT/"state/delivery/requests/AI_PERSONAL_FIREFOX_V1.json").read_text(encoding="utf-8"))
        required=set(request["effect_ack"]["fields"])
        self.assertTrue({"epistemic_spiral_transputer_roundtrip_receipt",
                         "epistemic_spiral_linux_readback_receipt",
                         "epistemic_spiral_oci_readback_receipt"} <= required)
        self.assertFalse(request["completion_claims"]["EFFECT_ACK_DONE"])

if __name__=="__main__": unittest.main()

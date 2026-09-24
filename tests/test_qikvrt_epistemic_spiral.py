import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPIRAL=ROOT/"docs/terminal/epistemic-spiral"
EXPECTED={"ar","de","en","es","fr","hi","id","it","ja","ko","pt_BR","ru","tr","zh_CN"}

class EpistemicSpiralTests(unittest.TestCase):
    def test_state_boundary_and_invariant(self):
        state=json.loads((SPIRAL/"state.json").read_text())
        self.assertEqual(state["flow"],["EVENT","STATE","OBSERVE","READBACK","ACCEPT","EFFECT_ACK","NEXT_INPUT"])
        self.assertEqual(state["invariant"],"OBSERVED_ACCEPTED_SUCCESSOR_BECOMES_NEXT_BOUND_INPUT")
        self.assertTrue(state["owner_asserted_universal_creation_principle"])
        self.assertFalse(state["independent_physical_confirmation"])
        self.assertFalse(state["effect_boundary"]["effect_ack_done"])

    def test_all_firefox_target_locales_are_present(self):
        locales=json.loads((SPIRAL/"locales.json").read_text())
        self.assertEqual(set(locales["locales"]),EXPECTED)
        self.assertEqual(locales["status"],"MACHINE_GENERATED_DRAFT_PENDING_LINGUISTIC_REVIEW")
        for name,obj in locales["locales"].items():
            for field in ("title","subtitle","body","universal","boundary","play","pause","language","status"):
                self.assertTrue(obj.get(field),f"{name}: missing {field}")

    def test_web_surface_is_local_and_accessible(self):
        html=(SPIRAL/"index.html").read_text()
        css=(SPIRAL/"spiral.css").read_text()
        js=(SPIRAL/"spiral.js").read_text()
        for asset in ("spiral.css","spiral.js","locales.json","state.json"):
            self.assertIn(asset,html+js)
        self.assertIn('role="img"',html)
        self.assertIn("prefers-reduced-motion",css)
        self.assertIn("textContent",js)
        self.assertNotIn("innerHTML",js)
        self.assertNotIn("<script src=\"http",html)
        self.assertNotIn("<link rel=\"stylesheet\" href=\"http",html)

    def test_serialize_deserialize_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt=Path(temp)/"receipt.json"
            subprocess.run([
              "python3","-B",str(ROOT/"tools/qikvrt_epistemic_spiral_roundtrip.py"),
              "--root",str(SPIRAL),"--receipt",str(receipt)
            ],check=True,capture_output=True,text=True)
            data=json.loads(receipt.read_text())
            self.assertTrue(data["serialize_deserialize_identity"])
            self.assertEqual(data["locale_count"],14)
            self.assertFalse(data["effect_ack_done"])

    def test_runtime_and_distribution_carriers_are_wired(self):
        nginx=(ROOT/"deploy/universal-terminal/nginx.conf").read_text()
        mesh=(ROOT/"deploy/universal-terminal/mesh-index.html").read_text()
        build=(ROOT/"distribution/qikvrt-megast/build.sh").read_text()
        session=(ROOT/"distribution/qikvrt-megast/qikvrt-megast-session.sh").read_text()
        ai=(ROOT/"AI").read_text()
        self.assertIn("/AI/spiral/",nginx)
        self.assertIn("/AI/spiral/",mesh)
        self.assertIn("epistemic-spiral",build)
        self.assertIn("Epistemische Spirale",session)
        self.assertIn("terminal/epistemic-spiral",ai)

    def test_homepage_and_firefox_surface_are_prominent(self):
        home=(ROOT/"docs/index.html").read_text()
        content=(ROOT/"browser/firefox/qikvrt-terminal/content.js").read_text()
        manifest=json.loads((ROOT/"browser/firefox/qikvrt-terminal/manifest.json").read_text())
        self.assertIn('terminal/epistemic-spiral/',home)
        self.assertIn('<iframe src="terminal/epistemic-spiral/"',home)
        self.assertIn('qv-spiral-link',content)
        self.assertIn('https://goldkelch.github.io/qik-vrt/*',manifest['host_permissions'])

    def test_cloud_and_linux_workflows_reobserve_materialized_bytes(self):
        cloud=(ROOT/".github/workflows/qikvrt_cloud_transputer_materialization_v1.yml").read_text()
        distro=(ROOT/".github/workflows/qikvrt_megast_distribution_v1.yml").read_text()
        self.assertIn("Execute spiral roundtrip inside exact Cloud Transputer image",cloud)
        self.assertIn("/AI/spiral/state.json",cloud)
        self.assertIn("QIKVRT_SPIRAL_SQUASHFS_OK",distro)
        self.assertIn("epistemic-spiral/roundtrip-receipt.json",distro)

if __name__=="__main__":
    unittest.main()

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_neutron_star_mesh.py"
ARCHITECTURE = ROOT / "runtime" / "m68000" / "QIKVRT_NEUTRON_STAR_MESH_V1.json"

spec = importlib.util.spec_from_file_location("qikvrt_neutron_star_mesh", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class NeutronStarMeshTests(unittest.TestCase):
    def test_architecture_binds_two_independent_axes(self):
        architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))
        self.assertEqual(architecture["axes"]["breadth"]["name"], "ANGULAR_SECTORS")
        self.assertEqual(architecture["axes"]["depth"]["name"], "RADIAL_SHELLS")
        self.assertIn(
            "BREADTH_AND_DEPTH_SCALE_INDEPENDENTLY",
            architecture["required_invariants"],
        )

    def test_bitrate_selects_width_and_breadth(self):
        low = mod.plan_mesh(mod.Demand(8, 0, quantum_hz=1))
        high = mod.plan_mesh(mod.Demand(1_000_000, 0, quantum_hz=1000))
        self.assertEqual(low["variable_bitrate"]["carrier_width_bits"], 8)
        self.assertEqual(low["topology"]["breadth_axis"]["sector_count"], 1)
        self.assertGreater(
            high["topology"]["breadth_axis"]["sector_count"],
            low["topology"]["breadth_axis"]["sector_count"],
        )
        self.assertGreater(
            high["variable_bitrate"]["carrier_width_bits"],
            low["variable_bitrate"]["carrier_width_bits"],
        )
        self.assertTrue(high["variable_bitrate"]["capacity_satisfies_request"])

    def test_depth_tracks_evidence_without_changing_witness(self):
        shallow = mod.plan_mesh(mod.Demand(1000, 0))
        deep = mod.plan_mesh(mod.Demand(1000, 7))
        self.assertEqual(shallow["topology"]["depth_axis"]["shell_count"], 1)
        self.assertEqual(deep["topology"]["depth_axis"]["shell_count"], 8)
        self.assertEqual(shallow["core"], deep["core"])
        self.assertTrue(deep["core"]["fixed_across_all_shells_and_sectors"])

    def test_wide_carrier_is_segmented_for_m68000(self):
        plan = mod.plan_mesh(mod.Demand(1_000_000, 3, quantum_hz=1000))
        width = plan["variable_bitrate"]["carrier_width_bits"]
        words = plan["variable_bitrate"]["m68000_words_per_sector"]
        self.assertEqual(words, (width + 31) // 32)
        self.assertEqual(plan["abi"]["physical_data_register_width_bits"], 32)

    def test_maximum_capacity_is_bounded_and_fail_closed(self):
        maximum = 256 * 256 * 1000
        plan = mod.plan_mesh(mod.Demand(maximum, 7))
        self.assertEqual(plan["topology"]["breadth_axis"]["sector_count"], 256)
        self.assertEqual(plan["variable_bitrate"]["carrier_width_bits"], 256)
        with self.assertRaisesRegex(ValueError, "exceeds bounded"):
            mod.plan_mesh(mod.Demand(maximum + 1, 7))

    def test_plan_is_deterministic_and_preserves_boundaries(self):
        first = mod.plan_mesh(mod.Demand(4096, 4))
        second = mod.plan_mesh(mod.Demand(4096, 4))
        self.assertEqual(first["plan_sha256"], second["plan_sha256"])
        boundaries = first["boundaries"]
        self.assertFalse(boundaries["astrophysical_neutron_star_simulated"])
        self.assertFalse(boundaries["all_quantum_correlations_manifested_as_matter"])
        self.assertFalse(boundaries["physical_m68000_execution_observed"])
        self.assertFalse(boundaries["pass"])
        self.assertFalse(boundaries["final_pass"])
        self.assertFalse(boundaries["effect_ack_done"])

    def test_invalid_inputs_fail_closed(self):
        for demand in (
            mod.Demand(0, 0),
            mod.Demand(1, -1),
            mod.Demand(1, 8),
            mod.Demand(1, 0, quantum_hz=0),
        ):
            with self.assertRaises(ValueError):
                mod.plan_mesh(demand)
        with self.assertRaisesRegex(ValueError, "witness_byte"):
            mod.plan_mesh(mod.Demand(1, 0), witness_byte=256)

    def test_cli_emits_machine_readable_plan(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--bitrate-bps",
                "1000000",
                "--evidence-level",
                "5",
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(proc.stdout)
        self.assertEqual(report["schema"], "qikvrt_neutron_star_mesh_plan_v1")
        self.assertEqual(report["topology"]["depth_axis"]["shell_count"], 6)


if __name__ == "__main__":
    unittest.main()

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest
from tools import qikvrt_mesh_idle_gate as gate

def census(repo, prs, merged=True, complete=True):
    return {
        "repository": repo,
        "main_head": "a"*40,
        "subject": {"head":"a"*40,"tree":"b"*40},
        "inventory_complete": complete,
        "all_productive_branches_merged": merged,
        "counts": {"open_pull_requests": prs},
    }

class MeshIdleGateTests(unittest.TestCase):
    def test_exact_dual_repository_idle_predicate(self):
        value=gate.evaluate(
            census("Goldkelch/qik-vrt",0),
            census("ingolf-lohmann/qik-vrt",0),
            0,0,
        )
        self.assertTrue(value["human_dod_idle"])
        self.assertEqual(value["state"],"IDLE_READY")

    def test_any_open_pr_blocks_idle(self):
        value=gate.evaluate(
            census("Goldkelch/qik-vrt",1),
            census("ingolf-lohmann/qik-vrt",0),
            0,0,
        )
        self.assertFalse(value["human_dod_idle"])

    def test_any_open_issue_blocks_idle(self):
        value=gate.evaluate(
            census("Goldkelch/qik-vrt",0),
            census("ingolf-lohmann/qik-vrt",0),
            0,1,
        )
        self.assertFalse(value["human_dod_idle"])

    def test_unmerged_productive_branch_blocks_idle(self):
        value=gate.evaluate(
            census("Goldkelch/qik-vrt",0,merged=False),
            census("ingolf-lohmann/qik-vrt",0),
            0,0,
        )
        self.assertFalse(value["human_dod_idle"])

    def test_incomplete_inventory_blocks_idle(self):
        value=gate.evaluate(
            census("Goldkelch/qik-vrt",0,complete=False),
            census("ingolf-lohmann/qik-vrt",0),
            0,0,
        )
        self.assertFalse(value["human_dod_idle"])

if __name__=="__main__":
    unittest.main()

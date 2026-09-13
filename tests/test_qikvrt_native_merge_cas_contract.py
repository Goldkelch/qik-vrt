# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest

from tools.qikvrt_native_merge_cas import (
    NativeMergeCASBlock,
    require_native_strict_base_cas_ruleset,
    verify_native_merge_effect,
)


class NativeMergeCASContractTests(unittest.TestCase):
    def _ruleset(self, *, strict: bool = True, bypass: str = "never") -> dict:
        return {
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
            "rules": [
                {"type": "pull_request", "parameters": {}},
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": strict,
                        "required_status_checks": [{"context": "test", "integration_id": 15368}],
                    },
                },
                {"type": "non_fast_forward"},
            ],
            "current_user_can_bypass": bypass,
        }

    def test_strict_ruleset_is_admissible_native_base_cas(self) -> None:
        require_native_strict_base_cas_ruleset(self._ruleset())

    def test_loose_status_policy_is_rejected(self) -> None:
        with self.assertRaisesRegex(NativeMergeCASBlock, "STRICT_BASE_POLICY_REQUIRED"):
            require_native_strict_base_cas_ruleset(self._ruleset(strict=False))

    def test_bypass_capability_is_rejected(self) -> None:
        with self.assertRaisesRegex(NativeMergeCASBlock, "BYPASS_MUST_BE_NEVER"):
            require_native_strict_base_cas_ruleset(self._ruleset(bypass="always"))

    def test_effect_readback_binds_exact_merge_parents_and_main(self) -> None:
        expected_base = "a" * 40
        expected_head = "b" * 40
        merge_sha = "c" * 40
        verify_native_merge_effect(
            expected_base=expected_base,
            expected_head=expected_head,
            merge_response={"merged": True, "sha": merge_sha},
            pr_after={"merged": True, "merge_commit_sha": merge_sha},
            main_after={"sha": merge_sha},
            merge_commit={
                "sha": merge_sha,
                "parents": [{"sha": expected_base}, {"sha": expected_head}],
            },
        )

    def test_effect_readback_rejects_wrong_head1(self) -> None:
        with self.assertRaisesRegex(NativeMergeCASBlock, "MERGE_PARENT_BINDING_MISMATCH"):
            verify_native_merge_effect(
                expected_base="a" * 40,
                expected_head="b" * 40,
                merge_response={"merged": True, "sha": "c" * 40},
                pr_after={"merged": True, "merge_commit_sha": "c" * 40},
                main_after={"sha": "c" * 40},
                merge_commit={
                    "sha": "c" * 40,
                    "parents": [{"sha": "d" * 40}, {"sha": "b" * 40}],
                },
            )


if __name__ == "__main__":
    unittest.main()

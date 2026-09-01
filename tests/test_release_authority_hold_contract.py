#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Security regressions for retired candidate-controlled release carriers."""

from __future__ import annotations

import unittest

from tests.release_authority_hold_contract import (
    CARRIER_WORKFLOWS,
    assert_authority_hold_workflow,
)


class ReleaseAuthorityHoldContractTests(unittest.TestCase):
    def test_every_retired_carrier_is_trusted_main_read_only_d0_3(self) -> None:
        for workflow in CARRIER_WORKFLOWS:
            with self.subTest(workflow=workflow):
                assert_authority_hold_workflow(self, workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)

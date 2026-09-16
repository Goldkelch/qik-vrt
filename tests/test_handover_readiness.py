# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest
from tools.qikvrt_handover_selftest import check
class HandoverReadiness(unittest.TestCase):
    def test_handover_preparation_is_complete_and_fail_closed(self):
        check()
if __name__ == '__main__': unittest.main()

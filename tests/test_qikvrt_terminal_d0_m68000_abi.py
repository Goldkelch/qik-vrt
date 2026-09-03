from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TerminalD0M68000AbiTests(unittest.TestCase):
    def test_four_fixed_68000_terminal_entries_are_byte_exact(self):
        data = (ROOT / 'runtime/m68000/qikvrt_terminal_d0_abi.hex').read_text().strip()
        self.assertEqual(data, '70004e7570014e7570024e7570034e75')
        self.assertEqual(len(bytes.fromhex(data)), 16)
        text = (ROOT / 'src/m68000/qikvrt_terminal_d0_abi.s').read_text()
        self.assertEqual(text.count('rts'), 4)
        self.assertIn('D3 remains the stable witness', text)

if __name__ == '__main__':
    unittest.main()

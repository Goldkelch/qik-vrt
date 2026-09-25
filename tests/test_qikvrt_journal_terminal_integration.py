import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class JournalTerminalIntegrationTests(unittest.TestCase):
    def test_terminal_exposes_fixed_journal_read_paths(self):
        js=(ROOT/"docs/assets/js/qikvrt-repository-terminal.js").read_text(encoding="utf-8")
        html=(ROOT/"docs/terminal/index.html").read_text(encoding="utf-8")
        for token in (
            'journal [index|claims|sources|corrections|languages]',
            '../journal/index.json',
            '../journal/wahrheit-oder-spam/claims.json',
            '../journal/wahrheit-oder-spam/sources.json',
            '../journal/corrections.json',
            '../journal/wahrheit-oder-spam/i18n/manifest.json',
            'Mutation: NONE',
        ):
            self.assertIn(token, js)
        self.assertIn('data-command="journal claims"', html)
        self.assertIn("PUBLIC_GET_ONLY", html)
        self.assertNotIn("fetch(argument", js)
        self.assertNotIn("eval(", js)

    def test_machine_index_points_to_terminal_and_six_languages(self):
        idx=json.loads((ROOT/"docs/journal/index.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["interaction"]["mode"],"READ_ONLY_EVIDENCE_INTERACTION")
        self.assertEqual(len(idx["translation"]["locales"]),6)
        urls=idx["articles"][0]["language_urls"]
        self.assertEqual(set(urls),{"de","en","fr","ru","fa","zh-Hans"})
        self.assertTrue(idx["interaction"]["universal_terminal_url"].endswith("/terminal/"))

if __name__=="__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.qikvrt_firefox_package import SOURCE, package

ROOT = Path(__file__).resolve().parents[1]


class FirefoxLocalizationTests(unittest.TestCase):
    def test_g20_country_coverage_and_substitutions(self):
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text())
        localization = policy["terminal"]["ui_localization"]
        self.assertEqual(set(localization["country_locales"]),
                         set("AR AU BR CA CN FR DE IN ID IT JP KR MX RU SA ZA TR GB US".split()))
        self.assertEqual({locale for country in localization["country_locales"].values() for locale in country},
                         set(localization["locales"]))
        catalogs = {p.parent.name: json.loads(p.read_text()) for p in SOURCE.glob("_locales/*/messages.json")}
        self.assertEqual(set(catalogs), set(localization["locales"]))
        for locale, catalog in catalogs.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(catalog), set(catalogs["en"]))
                self.assertLessEqual(len(catalog["extensionDescription"]["message"]), 132)
                for key in ("audioLocal", "snapshotLocal"):
                    self.assertEqual(catalog[key]["message"].count("$BYTES$"), 1)
                    self.assertEqual(catalog[key]["placeholders"]["bytes"]["content"], "$1")

    def test_production_script_keeps_localized_labels_out_of_authorization(self):
        result = subprocess.run(["node", str(ROOT / "tests/firefox_i18n_behavior.cjs")],
                                capture_output=True, text=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("14 locales", result.stdout)

    def test_complete_package_is_independent_of_source_mtimes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copied = root / "source"
            shutil.copytree(SOURCE, copied)
            first = package(root / "first.xpi", copied)
            for path in copied.rglob("*"):
                if path.is_file():
                    os.utime(path, (1710000000, 1710000000))
            second = package(root / "second.xpi", copied)
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertFalse(first["signed"])
            with zipfile.ZipFile(root / "first.xpi") as archive:
                names = set(archive.namelist())
                self.assertIn("authenticated_delivery.js", names)
                self.assertIn("review_effect.js", names)
                self.assertEqual(len([n for n in names if n.startswith("_locales/")]), 14)
                self.assertIsNone(archive.testzip())
            (copied / "review_effect.js").unlink()
            with self.assertRaisesRegex(ValueError, "Missing Firefox resources"):
                package(root / "incomplete.xpi", copied)

    def test_incomplete_locale_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copied = root / "source"
            shutil.copytree(SOURCE, copied)
            path = copied / "_locales/ar/messages.json"
            catalog = json.loads(path.read_text())
            del catalog["prepareBoundary"]
            path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError, "Incomplete locale: ar"):
                package(root / "incomplete.xpi", copied)


if __name__ == "__main__":
    unittest.main()

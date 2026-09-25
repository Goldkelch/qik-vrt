# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.qikvrt_firefox_install import LicenseNotAccepted, install, render_notice
from tools.qikvrt_firefox_package import package


class FirefoxLicenseAcceptanceTest(unittest.TestCase):
    def test_package_embeds_all_required_license_terms(self):
        with tempfile.TemporaryDirectory() as temp:
            xpi = Path(temp) / "qikvrt.xpi"
            result = package(xpi)
            self.assertEqual(result["license_files"], 4)
            with zipfile.ZipFile(xpi) as archive:
                names = set(archive.namelist())
                self.assertIn("licenses/PolyForm-Noncommercial-1.0.0.txt", names)
                self.assertIn("licenses/CC-BY-NC-ND-4.0.txt", names)
                self.assertIn("licenses/QIKVRT-LICENSE-GUIDE.md", names)
                self.assertIn("licenses/QIKVRT-COMMERCIAL-USE-POLICY.md", names)

    def test_install_fails_closed_without_acceptance_and_mutates_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            xpi = root / "qikvrt.xpi"
            profile = root / "profile"
            package(xpi)
            with self.assertRaises(LicenseNotAccepted):
                install(xpi, profile, accepted=False)
            self.assertFalse(profile.exists())

    def test_explicit_acceptance_installs_exact_xpi_without_activation_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            xpi = root / "qikvrt.xpi"
            profile = root / "profile"
            package(xpi)
            result = install(xpi, profile, accepted=True)
            target = Path(result["path"])
            self.assertEqual(target.read_bytes(), xpi.read_bytes())
            self.assertEqual(result["accepted_license"], "PolyForm-Noncommercial-1.0.0")
            self.assertEqual(result["documentation_license"], "CC-BY-NC-ND-4.0")
            self.assertFalse(result["commercial_use_licensed"])
            self.assertFalse(result["activation_claimed"])

    def test_notice_explains_scope_and_reason_for_acceptance(self):
        notice = render_notice()
        self.assertIn("Free private/personal use", notice)
        self.assertIn("Ordinary commercial use is not licensed", notice)
        self.assertIn("Why this acceptance gate exists", notice)
        self.assertIn("before the installer mutates the Firefox profile", notice)


if __name__ == "__main__":
    unittest.main()

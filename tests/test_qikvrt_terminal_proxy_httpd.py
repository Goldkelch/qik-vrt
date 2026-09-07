import importlib.util
import os
import pathlib
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src/qikvrt_terminal_proxy_httpd.py"


class ProxyBoundaryTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location("qikvrt_terminal_proxy_httpd", MODULE_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_non_loopback_boundary_requires_secret(self):
        module = self.load()
        self.assertNotIn("0.0.0.0", module.LOOPBACK_NAMES)
        with mock.patch.dict(os.environ, {"QIKVRT_PROXY_PASSWORD": ""}, clear=False):
            self.assertEqual(module.load_password(), "")

    def test_secret_file_and_direct_secret_are_mutually_exclusive(self):
        module = self.load()
        with mock.patch.dict(
            os.environ,
            {"QIKVRT_PROXY_PASSWORD": "x", "QIKVRT_PROXY_PASSWORD_FILE": "/tmp/x"},
            clear=False,
        ):
            with self.assertRaises(SystemExit):
                module.load_password()

    def test_effect_ack_routes_remain_distinct_from_novnc(self):
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('path == "/.well-known/effect-ack"', text)
        self.assertIn("self.proxy.effect_host", text)
        self.assertIn("self.proxy.novnc_host", text)
        self.assertIn('path == "/healthz"', text)
        self.assertIn('path == "/qikvrt/sql"', text)


if __name__ == "__main__":
    unittest.main()

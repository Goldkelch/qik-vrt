import argparse
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_candidate_tls_server.py"


class CandidateTlsServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("candidate_tls_server", TOOL)
        cls.mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules[spec.name] = cls.mod
        spec.loader.exec_module(cls.mod)

    def make_docs(self, directory: pathlib.Path) -> pathlib.Path:
        docs = directory / "docs"
        terminal = docs / "atari-terminal"
        terminal.mkdir(parents=True)
        (docs / "index.html").write_text("root", encoding="utf-8")
        (terminal / "index.html").write_text("atari", encoding="utf-8")
        (terminal / "terminal.js").write_text("console.log('ok')", encoding="utf-8")
        return docs

    def test_maps_only_candidate_prefix_and_index_documents(self):
        with tempfile.TemporaryDirectory() as raw:
            docs = self.make_docs(pathlib.Path(raw))
            self.assertEqual(
                self.mod.map_candidate_path(docs, "/qik-vrt/"),
                (docs / "index.html").resolve(),
            )
            self.assertEqual(
                self.mod.map_candidate_path(docs, "/qik-vrt/atari-terminal/"),
                (docs / "atari-terminal/index.html").resolve(),
            )
            self.assertEqual(
                self.mod.map_candidate_path(
                    docs, "/qik-vrt/atari-terminal/terminal.js?cache=0"
                ),
                (docs / "atari-terminal/terminal.js").resolve(),
            )
            self.assertIsNone(self.mod.map_candidate_path(docs, "/atari-terminal/"))
            self.assertIsNone(self.mod.map_candidate_path(docs, "/qik-vrt"))

    def test_rejects_encoded_and_symlink_path_escape(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            docs = self.make_docs(root)
            outside = root / "outside.txt"
            outside.write_text("private", encoding="utf-8")
            denied = (
                "/qik-vrt/../outside.txt",
                "/qik-vrt/%2e%2e/outside.txt",
                "/qik-vrt/%2Fetc/passwd",
                "/qik-vrt/atari-terminal%5cterminal.js",
                "/qik-vrt/atari-terminal//terminal.js",
                "/qik-vrt/%00terminal.js",
            )
            for request in denied:
                with self.subTest(request=request):
                    self.assertIsNone(self.mod.map_candidate_path(docs, request))
            link = docs / "outside-link.txt"
            try:
                os.symlink(outside, link)
            except (AttributeError, NotImplementedError, OSError):
                self.skipTest("symlinks are unavailable on this platform")
            self.assertIsNone(self.mod.map_candidate_path(docs, "/qik-vrt/outside-link.txt"))

    def test_cli_requires_loopback_docs_certificate_and_key(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            docs = self.make_docs(root)
            certificate = root / "candidate.pem"
            key = root / "candidate.key"
            certificate.write_text("certificate", encoding="utf-8")
            key.write_text("key", encoding="utf-8")
            receipt = root / "nested/startup.json"
            args = self.mod.build_parser().parse_args(
                [
                    "--docs-root",
                    str(docs),
                    "--certificate",
                    str(certificate),
                    "--key",
                    str(key),
                    "--bind",
                    "127.0.0.1",
                    "--port",
                    "0",
                    "--startup-receipt",
                    str(receipt),
                ]
            )
            configuration = self.mod.validate_configuration(args)
            self.assertEqual(configuration.bind, "127.0.0.1")
            self.assertEqual(configuration.port, 0)
            self.assertEqual(configuration.docs_root, docs.resolve())
            self.assertEqual(configuration.startup_receipt, receipt.resolve())
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    self.mod.build_parser().parse_args(
                        [
                            "--docs-root",
                            str(docs),
                            "--certificate",
                            str(certificate),
                            "--key",
                            str(key),
                            "--bind",
                            "0.0.0.0",
                        ]
                    )

    def test_health_marker_and_bounded_startup_receipt_are_explicit(self):
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            docs = self.make_docs(root)
            certificate = root / "candidate.pem"
            key = root / "candidate.key"
            certificate.write_bytes(b"certificate bytes")
            key.write_bytes(b"key bytes")
            destination = root / "receipt.json"
            configuration = self.mod.CandidateTlsConfiguration(
                docs_root=docs.resolve(),
                certificate=certificate.resolve(),
                key=key.resolve(),
                bind="127.0.0.1",
                port=443,
                startup_receipt=destination,
            )
            health = self.mod.health_payload()
            self.assertEqual(health["state"], "READY")
            self.assertFalse(health["effect_ack_done"])
            self.assertFalse(health["deployment"])
            receipt = self.mod.startup_receipt(configuration, 9443)
            encoded = self.mod.write_startup_receipt(destination, receipt)
            self.assertLessEqual(len(encoded), self.mod.STARTUP_RECEIPT_MAX_BYTES)
            self.assertEqual(destination.read_bytes(), encoded)
            observed = json.loads(encoded)
            self.assertEqual(observed["port"], 9443)
            self.assertEqual(observed["url_prefix"], "/qik-vrt/")
            self.assertFalse(observed["effect_ack_done"])
            self.assertFalse(observed["deployment"])

    def test_static_contract_uses_standard_library_tls_and_exact_prefix(self):
        text = TOOL.read_text(encoding="utf-8")
        help_text = self.mod.build_parser().format_help()
        self.assertIn("ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)", text)
        self.assertIn("ThreadingHTTPServer", text)
        self.assertIn("context.minimum_version = ssl.TLSVersion.TLSv1_2", text)
        self.assertIn("--docs-root", help_text)
        self.assertIn("--certificate", help_text)
        self.assertIn("--key", help_text)
        self.assertIn("--startup-receipt", help_text)
        self.assertEqual(self.mod.URL_PREFIX, "/qik-vrt/")
        self.assertEqual(
            self.mod.HEALTH_PATH, "/qik-vrt/__qikvrt_candidate_health__"
        )


if __name__ == "__main__":
    unittest.main()

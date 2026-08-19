import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tools import qikvrt_firefox_proxy_delegate as bridge


class FirefoxProxyDelegateTests(unittest.TestCase):
    def test_rejects_non_https(self):
        with self.assertRaises(ValueError):
            bridge.validate_target("http://github.com/settings")

    def test_rejects_unlisted_host(self):
        with self.assertRaises(ValueError):
            bridge.validate_target("https://example.com/")

    def test_rejects_embedded_credentials(self):
        with self.assertRaises(ValueError):
            bridge.validate_target("https://user:secret@github.com/settings")

    def test_record_never_serializes_secret_or_effect(self):
        record = bridge.build_record(
            "https://github.com/settings/personal-access-tokens",
            "Goldkelch",
            "Goldkelch/qik-vrt",
            True,
        )
        self.assertFalse(record["secret_serialized"])
        self.assertFalse(record["effect_executed"])
        self.assertEqual(record["next_boundary"], "HUMAN_AUTHENTICATION_OR_SECRET_ENTRY")
        self.assertEqual(record["post_boundary_requirement"], "AUTHORITATIVE_REOBSERVATION")

    @mock.patch.object(bridge.subprocess, "Popen")
    @mock.patch.object(bridge, "resolve_firefox", return_value="/usr/bin/firefox")
    def test_launches_exact_allowlisted_url(self, _resolve, popen):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = bridge.main([
                "--url", "https://github.com/settings/personal-access-tokens",
                "--expected-owner", "Goldkelch",
                "--repository", "Goldkelch/qik-vrt",
                "--json",
            ])
        self.assertEqual(rc, 0)
        popen.assert_called_once()
        argv = popen.call_args.args[0]
        self.assertEqual(argv[:2], ["/usr/bin/firefox", "--new-tab"])
        self.assertEqual(argv[2], "https://github.com/settings/personal-access-tokens")
        record = json.loads(out.getvalue())
        self.assertTrue(record["launched"])
        self.assertFalse(record["secret_serialized"])
        self.assertFalse(record["effect_executed"])


if __name__ == "__main__":
    unittest.main()

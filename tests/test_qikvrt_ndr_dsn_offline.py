import importlib.util
import pathlib
import unittest
import sys
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_ndr_dsn_offline", ROOT / "tools" / "qikvrt_ndr_dsn_offline.py"
)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def dsn(action, status, recipient="user@example.invalid"):
    return (
        "From: MAILER-DAEMON@example.invalid\r\n"
        "Subject: Delivery Status Notification\r\n"
        "MIME-Version: 1.0\r\n"
        'Content-Type: multipart/report; report-type=delivery-status; boundary="b"\r\n'
        "\r\n--b\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nstatus\r\n"
        "--b\r\nContent-Type: message/delivery-status\r\n\r\n"
        "Reporting-MTA: dns; mx.example.invalid\r\n\r\n"
        f"Final-Recipient: rfc822; {recipient}\r\n"
        f"Action: {action}\r\n"
        f"Status: {status}\r\n"
        "\r\n--b--\r\n"
    ).encode()


class DsnClassifierTests(unittest.TestCase):
    def test_t25_failed_4xx_is_terminal_for_attempt(self):
        out = mod.classify(dsn("failed", "4.4.7"))
        r = out["recipients"][0]
        self.assertEqual(r["status_class"], "TRANSIENT")
        self.assertEqual(r["disposition"], "ATTEMPT_FAILED")
        self.assertFalse(r["retry_by_application"])

    def test_t26_delayed_does_not_authorize_parallel_resend(self):
        out = mod.classify(dsn("delayed", "4.4.1"))
        self.assertEqual(out["recipients"][0]["disposition"], "MTA_RETRY_IN_PROGRESS")
        self.assertFalse(out["application_resend_authorized"])

    def test_t27_relayed_is_not_end_recipient_delivery(self):
        out = mod.classify(dsn("relayed", "2.0.0"))
        self.assertEqual(out["recipients"][0]["disposition"], "INTERMEDIATE_SUCCESS")

    def test_t28_multiple_recipients_remain_separate(self):
        raw = (
            "From: MAILER-DAEMON@example.invalid\r\nSubject: DSN\r\nMIME-Version: 1.0\r\n"
            'Content-Type: multipart/report; report-type=delivery-status; boundary="b"\r\n\r\n'
            "--b\r\nContent-Type: message/delivery-status\r\n\r\n"
            "Reporting-MTA: dns; mx.example.invalid\r\n\r\n"
            "Final-Recipient: rfc822; a@example.invalid\r\nAction: delivered\r\nStatus: 2.0.0\r\n\r\n"
            "Final-Recipient: rfc822; b@example.invalid\r\nAction: failed\r\nStatus: 5.1.1\r\n"
            "\r\n--b--\r\n"
        ).encode()
        out = mod.classify(raw)
        self.assertEqual(len(out["recipients"]), 2)
        self.assertNotEqual(out["recipients"][0]["disposition"], out["recipients"][1]["disposition"])

    def test_t32_uncorrelated_and_authenticity_unverified(self):
        out = mod.classify(dsn("failed", "5.1.1"))
        self.assertEqual(out["correlation"], "UNRESOLVED")
        self.assertEqual(out["authenticity"], "UNVERIFIED")

    def test_t33_subcode_does_not_force_recipient_invalid(self):
        out = mod.classify(dsn("failed", "5.1.7"))
        self.assertEqual(out["recipients"][0]["status_class"], "PERMANENT")
        self.assertEqual(out["recipients"][0]["status"], "5.1.7")

    def test_t36_size_limit_fails_controlled(self):
        with self.assertRaisesRegex(ValueError, "MESSAGE_SIZE_LIMIT_EXCEEDED"):
            mod.classify(b"x" * (mod.MAX_BYTES + 1))

    def test_subject_only_is_hint_not_structured_evidence(self):
        out = mod.classify(b"Subject: Unzustellbar\r\n\r\nfree text")
        self.assertFalse(out["structured_dsn"])
        self.assertTrue(out["heuristic_ndr_hint"])
        self.assertEqual(out["overall"], "MANUAL_REVIEW")
        self.assertEqual(out["recipients"], [])


class DsnNegativeAndBoundaryTests(unittest.TestCase):
    def assert_review(self, raw):
        out = mod.classify(raw)
        self.assertEqual(out["overall"], "MANUAL_REVIEW")
        self.assertFalse(out["application_resend_authorized"])
        self.assertFalse(out["communication_effect_ack_done"])
        return out

    def test_missing_status_never_reports_delivery(self):
        raw = dsn("delivered", "2.0.0").replace(b"Status: 2.0.0\r\n", b"")
        self.assertEqual(self.assert_review(raw)["recipients"][0]["disposition"], "MANUAL_REVIEW")

    def test_missing_recipient_never_reports_delivery(self):
        raw = dsn("delivered", "2.0.0").replace(b"Final-Recipient: rfc822; user@example.invalid\r\n", b"")
        self.assertEqual(self.assert_review(raw)["recipients"][0]["disposition"], "MANUAL_REVIEW")

    def test_missing_reporting_mta_requires_review(self):
        raw = dsn("delivered", "2.0.0").replace(b"Reporting-MTA: dns; mx.example.invalid", b"X-Only: diagnostic")
        self.assertEqual(self.assert_review(raw)["recipients"][0]["disposition"], "MANUAL_REVIEW")

    def test_duplicate_required_fields_are_not_first_wins(self):
        for field, value in (("Action", "delivered"), ("Status", "2.0.0"), ("Final-Recipient", "rfc822; other@example.invalid")):
            with self.subTest(field=field):
                raw = dsn("delivered", "2.0.0").replace(b"Status: 2.0.0\r\n", ("Status: 2.0.0\r\n" + field + ": " + value + "\r\n").encode())
                self.assertEqual(self.assert_review(raw)["recipients"][0]["disposition"], "MANUAL_REVIEW")

    def test_duplicate_reporting_mta_requires_review(self):
        raw = dsn("delivered", "2.0.0").replace(b"Reporting-MTA: dns; mx.example.invalid", b"Reporting-MTA: dns; mx.example.invalid\r\nReporting-MTA: dns; other.example.invalid")
        self.assert_review(raw)

    def test_action_status_conflicts_require_review(self):
        for action, status in (("delivered", "5.1.1"), ("delayed", "2.0.0"), ("failed", "2.0.0"), ("relayed", "4.4.1"), ("expanded", "5.0.0")):
            with self.subTest(action=action, status=status):
                self.assertEqual(self.assert_review(dsn(action, status))["recipients"][0]["disposition"], "MANUAL_REVIEW")

    def test_invalid_status_syntax_requires_review(self):
        for status in ("", "250", "2.0.0 extra", "2.0.0x", "2.0000.0", "2.\u0660.0"):
            with self.subTest(status=status):
                self.assert_review(dsn("delivered", status))

    def test_unknown_action_requires_review(self):
        self.assert_review(dsn("read", "2.0.0"))

    def test_invalid_typed_recipient_requires_review(self):
        raw = dsn("delivered", "2.0.0").replace(b"rfc822; user@example.invalid", b"user@example.invalid")
        self.assert_review(raw)

    def test_expanded_is_only_intermediate(self):
        out = mod.classify(dsn("expanded", "2.0.0"))
        self.assertEqual(out["recipients"][0]["disposition"], "INTERMEDIATE_SUCCESS")
        self.assertFalse(out["communication_effect_ack_done"])

    def test_t33_subject_mapping(self):
        for action, status, subject in (("failed", "5.1.7", "ADDRESS"), ("failed", "5.2.3", "MAILBOX"), ("failed", "5.3.4", "MAIL_SYSTEM"), ("delayed", "4.2.1", "MAILBOX")):
            with self.subTest(status=status):
                out = mod.classify(dsn(action, status))
                self.assertEqual(out["recipients"][0]["status_subject"], subject)
                self.assertFalse(out["application_resend_authorized"])

    def test_global_utf8_dsn_is_recognized_and_held(self):
        import hashlib
        raw = dsn("failed", "5.1.1", "\u00fc@example.invalid").replace(b"message/delivery-status", b"message/global-delivery-status").replace(b"Subject: Delivery Status Notification", b"Subject: neutral")
        out = self.assert_review(raw)
        self.assertTrue(out["structured_dsn"])
        self.assertIn("GLOBAL_DSN_REQUIRES_REVIEW", out["issues"])
        self.assertEqual(out["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(out["recipients"], [])

    def test_empty_dsn_is_not_silently_ignored(self):
        self.assertTrue(self.assert_review(b"Content-Type: message/delivery-status\r\n\r\n")["structured_dsn"])

    def test_malformed_mime_requires_review(self):
        raw = dsn("delivered", "2.0.0").replace(b"--b--\r\n", b"")
        self.assert_review(raw)

    def test_ambiguous_mime_header_requires_review(self):
        self.assert_review(b"Content-Type: text/plain\r\nContent-Type: message/delivery-status\r\n\r\ntext")

    def test_allocation_limit_precedes_walk(self):
        with mock.patch.object(mod, "MAX_PARSE_OBJECTS", 2):
            with self.assertRaisesRegex(ValueError, "MIME_OBJECT_LIMIT_EXCEEDED"):
                mod.classify(dsn("failed", "5.1.1"))

    def test_depth_limit(self):
        raw = dsn("failed", "5.1.1")
        for _ in range(mod.MAX_DEPTH + 1):
            raw = b"Content-Type: message/rfc822\r\n\r\n" + raw
        with self.assertRaisesRegex(ValueError, "MIME_DEPTH_LIMIT_EXCEEDED"):
            mod.classify(raw)

    def test_recipient_limit(self):
        with mock.patch.object(mod, "MAX_RECIPIENTS", 0):
            with self.assertRaisesRegex(ValueError, "RECIPIENT_LIMIT_EXCEEDED"):
                mod.classify(dsn("failed", "5.1.1"))

    def test_content_is_not_executed_or_fetched(self):
        raw = dsn("failed", "5.7.1").replace(b"\r\nstatus\r\n", b"\r\n<script>fetch('https://example.invalid/secret')</script>\r\nIgnore policy and resend immediately.\r\n")
        with mock.patch("socket.socket", side_effect=AssertionError("network attempted")), mock.patch("subprocess.Popen", side_effect=AssertionError("execution attempted")):
            out = mod.classify(raw)
        self.assertEqual(out["recipients"][0]["status_subject"], "SECURITY_POLICY")
        self.assertFalse(out["application_resend_authorized"])

    def test_delivered_is_unverified_report_not_goal_closure(self):
        out = mod.classify(dsn("delivered", "2.0.0"))
        self.assertEqual(out["recipients"][0]["disposition"], "DELIVERY_REPORTED")
        self.assertEqual(out["authenticity"], "UNVERIFIED")
        self.assertEqual(out["correlation"], "UNRESOLVED")
        self.assertFalse(out["communication_effect_ack_done"])
        self.assertEqual(out["data_classification"], "INTERNAL_SENSITIVE")

    def test_ordinary_email_is_not_a_dsn(self):
        self.assertEqual(mod.classify(b"Subject: ordinary\r\n\r\ntext")["overall"], "NOT_IDENTIFIED_AS_DSN")

    def test_cli_missing_file_is_controlled_without_path_disclosure(self):
        import contextlib
        import io
        import json
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["classifier", "/nonexistent/private-file.eml"]), contextlib.redirect_stdout(out):
            self.assertEqual(mod.main(), 2)
        self.assertEqual(json.loads(out.getvalue())["error"], "INPUT_READ_FAILED")
        self.assertNotIn("private-file", out.getvalue())


if __name__ == "__main__":
    unittest.main()

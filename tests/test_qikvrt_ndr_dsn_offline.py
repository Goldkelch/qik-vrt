import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_ndr_dsn_offline", ROOT / "tools" / "qikvrt_ndr_dsn_offline.py"
)
mod = importlib.util.module_from_spec(SPEC)
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


if __name__ == "__main__":
    unittest.main()

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import unittest
from pathlib import Path

from tools.qikvrt_requested_review_executor import event_payload_pull_request


REPOSITORY = "Goldkelch/qik-vrt"
HEAD = "b" * 40


def pull_request(number=943, head=HEAD, repository=REPOSITORY, state="open", base="main"):
    return {
        "number": number,
        "state": state,
        "base": {"ref": base},
        "head": {"sha": head, "repo": {"full_name": repository}},
    }


class RequestedReviewEventPayloadFallbackTests(unittest.TestCase):
    def test_accepts_exact_native_pull_request_target_payload(self):
        subject = pull_request()
        self.assertIs(
            event_payload_pull_request(
                {"pull_request": subject}, REPOSITORY, 943, HEAD,
                "pull_request_target",
            ),
            subject,
        )

    def test_accepts_exact_native_pull_request_review_payload(self):
        subject = pull_request()
        self.assertIs(
            event_payload_pull_request(
                {"pull_request": subject}, REPOSITORY, 943, HEAD,
                "pull_request_review",
            ),
            subject,
        )

    def test_rejects_non_native_event_class(self):
        self.assertIsNone(
            event_payload_pull_request(
                {"pull_request": pull_request()}, REPOSITORY, 943, HEAD,
                "issue_comment",
            )
        )

    def test_rejects_every_exact_binding_drift(self):
        variants = [
            pull_request(number=944),
            pull_request(head="c" * 40),
            pull_request(repository="ingolf-lohmann/qik-vrt"),
            pull_request(state="closed"),
            pull_request(base="other"),
        ]
        for subject in variants:
            with self.subTest(subject=subject):
                self.assertIsNone(
                    event_payload_pull_request(
                        {"pull_request": subject}, REPOSITORY, 943, HEAD,
                        "pull_request_target",
                    )
                )

    def test_workflow_prefers_live_get_and_uses_fallback_only_on_read_error(self):
        text = Path(
            ".github/workflows/qikvrt_requested_review_executor.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("try:\n                  return _gh_one", text)
        self.assertIn("except ReviewObservationError:", text)
        self.assertIn("fallback=event_payload_pull_request(", text)
        self.assertIn("if fallback is None:\n                      raise", text)


if __name__ == "__main__":
    unittest.main()

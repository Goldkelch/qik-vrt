# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Negative regressions for candidate-only exact-head integrity/public-site object transport."""
import base64
import copy
from pathlib import Path
import tempfile
import unittest
from tools import qikvrt_journey_integrity_objects as subject


class IntegrityObjectsTest(unittest.TestCase):
    def setUp(self):
        self.raw = b"deterministic integrity output\n"
        self.sha = subject.blob_id(self.raw)
        self.created = {"sha": self.sha}
        self.observed = {"sha": self.sha, "size": len(self.raw), "encoding": "base64", "content": base64.b64encode(self.raw).decode()}
        self.head = "a" * 40
        self.pr = {"number": 1080, "state": "open", "merged": False, "head": {"repo": {"full_name": subject.REPOSITORY}, "ref": subject.BRANCH, "sha": self.head}, "base": {"ref": "main"}}
        self.ref = {"object": {"type": "commit", "sha": self.head}}

    def test_only_integrity_paths_are_admissible(self):
        subject.validate_delta(list(subject.ALLOWED), [])
        subject.validate_delta([], [])
        with self.assertRaises(ValueError):
            subject.validate_delta(["docs/reise/source.de.txt"], [])
        with self.assertRaises(ValueError):
            subject.validate_delta([], ["untracked.txt"])

    def test_readback_must_match_identity_and_bytes(self):
        self.assertEqual(subject.verify_blob(self.raw, self.created, self.observed), self.sha)
        for key, value in (("sha", "b" * 40), ("size", 0), ("encoding", "utf-8"), ("content", base64.b64encode(b"different").decode())):
            altered = dict(self.observed, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                subject.verify_blob(self.raw, self.created, altered)
        with self.assertRaises(ValueError):
            subject.verify_blob(self.raw, {"sha": "c" * 40}, self.observed)

    def test_exact_subject_and_not_predecessor(self):
        subject.validate_subject(self.pr, self.ref, self.head)
        with self.assertRaises(ValueError):
            subject.validate_subject(self.pr, self.ref, "d" * 40)
        for field, value in (("state", "closed"), ("merged", True), ("number", 1079)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                subject.validate_subject(dict(self.pr, **{field: value}), self.ref, self.head)
        changed = copy.deepcopy(self.pr)
        changed["head"]["repo"]["full_name"] = "another/repository"
        with self.assertRaises(ValueError):
            subject.validate_subject(changed, self.ref, self.head)
        with self.assertRaises(ValueError):
            subject.validate_subject(self.pr, {"object": {"type": "commit", "sha": "e" * 40}}, self.head)

    def test_public_page_is_47_bound_and_not_preview_only(self):
        root = Path(__file__).resolve().parents[1] / "docs/reise"
        raw = subject.public_site_bytes(root)
        text = raw.decode("utf-8")
        self.assertIn('<meta name="robots" content="index,follow">', text)
        self.assertIn("47-Sprachen-Leseausgabe / 47-language reading edition.", text)
        self.assertNotIn("Unveröffentlichte Lesevorschau", text)
        self.assertNotIn("Unpublished reading preview", text)
        self.assertNotIn("noindex,nofollow", text)
        self.assertIn("ungeprüfte KI-Arbeitsfassungen", text)
        self.assertIn(subject.journey_site.SOURCE_SHA, text)

    def test_committed_site_must_equal_deterministic_public_render(self):
        root = Path(__file__).resolve().parents[1] / "docs/reise"
        expected = subject.public_site_bytes(root)
        index = root / "index.html"
        if index.exists():
            self.assertEqual(index.read_bytes(), expected)


    def test_delivery_manifest_binds_all_rendered_texts_and_current_subject(self):
        root = Path(__file__).resolve().parents[1] / "docs/reise"
        raw = subject.public_site_bytes(root)
        receipt = subject.rendered_delivery_manifest(root, raw, head="a" * 40, tree="b" * 40)
        self.assertEqual(receipt["homepage"]["git_blob_sha1"], subject.blob_id(raw))
        self.assertEqual(len(receipt["editions"]), 47)
        self.assertTrue(all(row["rendered_blocks"] == 540 for row in receipt["editions"]))
        self.assertEqual(len(receipt["language_chooser"]["edition_order"]), 47)
        self.assertEqual(receipt["public_http_readback"], "NOT_OBSERVED")
        self.assertFalse(receipt["public_delivery"])
        self.assertFalse(receipt["native_review"])
        self.assertFalse(receipt["EFFECT_ACK_DONE"])
        successor = subject.rendered_delivery_manifest(root, raw, head="c" * 40, tree="d" * 40)
        self.assertNotEqual(receipt["subject"], successor["subject"])
        self.assertEqual(receipt["homepage"], successor["homepage"])

    def test_rendered_content_chooser_download_and_script_tampering_is_rejected(self):
        root = Path(__file__).resolve().parents[1] / "docs/reise"
        raw = subject.public_site_bytes(root)
        mutations = [
            raw.replace(b'id="en-p0003"', b'id="en-p9999"', 1),
            raw.replace(b'data-lang="en"', b'data-lang="unknown"', 1),
            raw.replace(b'data-lang="en"', b'disabled data-lang="en"', 1),
            raw.replace(b'current=null;return false;', b'current="de";return true;', 1),
            raw.replace(b'"raw_editions": {"de":', b'"raw_editions": {"wrong":', 1),
            raw.replace(b'id="en-p0003"', b'id="de-p0003"', 1),
            raw.replace(b'id="en-p0003">', b'id="en-p0003">CHANGED', 1),
        ]
        for changed in mutations:
            self.assertNotEqual(changed, raw)
            with self.subTest(bytes=len(changed)), self.assertRaises((ValueError, KeyError)):
                subject.rendered_delivery_manifest(root, changed, head="a" * 40, tree="b" * 40)

    def test_journey_has_separate_pending_delivery_obligation(self):
        import json
        root = Path(__file__).resolve().parents[1]
        active = json.loads((root / "state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json").read_text())
        rows = [o for o in active["obligations"] if o["id"] == "JOURNEY_47_HOMEPAGE_TO_PAGES_V1"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source_pr"], 1080)
        self.assertEqual(row["completion"], "PENDING")
        self.assertIn(subject.PUBLIC_PATH, row["required_main_paths"])
        self.assertIn("mobile_browser_receipt", row["delivery"]["authoritative_readback"])
        self.assertIn("deployment_source_sha", row["delivery"]["authoritative_readback"])
        request = json.loads((root / row["delivery"]["request"]).read_text())
        self.assertEqual(request["delivery"]["binding_manifest"]["obligation_id"], row["id"])

    def test_workflow_is_event_bound_and_has_no_ref_writer(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/qikvrt_journey_integrity_objects.yml").read_text()
        self.assertIn("branches: [publication/self-explanation-47-homepage-v1]", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("tools/qikvrt_journey_site.py coverage-check", workflow)
        self.assertIn("make test", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("git push", workflow)
        code = (root / "tools/qikvrt_journey_integrity_objects.py").read_text()
        self.assertNotIn('api("PATCH"', code)
        self.assertNotIn('api("POST", "git/refs', code)
        self.assertNotIn('api("POST", "merges', code)
        self.assertIn("public_site_candidate", code)
        self.assertIn("PUBLIC_SITE_AND_INTEGRITY_GIT_OBJECTS_READ_BACK_CANDIDATE_ONLY", code)


if __name__ == "__main__":
    unittest.main()

# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI ChatGPT.
"""Test full-text projections, source binding and non-destructive replay."""
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("self_declaration_entry", ROOT / "tools/qikvrt_roundtrip_entrypoint.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
SOURCE = ("# Wenn Beobachtung als Handeln ausgegeben wird\n\n"
          "Ingolf Lohmann · September 2026\n\n"
          "Übergang → Wirkung; <script> & unveränderte Worte.\n\n"
          "## Ergänzung: Die gefährlichste Form des Scheiterns\n\n"
          "q.e.d.\nIngolf Lohmann\n").encode("utf-8")


class TextReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class SelfDeclarationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.patch = mock.patch.object(entry, "DECLARATION_BLOB", entry.git_blob(SOURCE))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.originals = {}
        for relative in entry.PATHS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = entry.prefix(relative) + ("Original: " + relative + "\n").encode()
            path.write_bytes(raw)
            self.originals[relative] = raw
        doc = self.root / entry.DECLARATION_PATH
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_bytes(SOURCE)
        self.originals["docs/index.html"] = (b"<!doctype html>\n" + entry.NAV_ANCHOR
            + b"    </nav>\n" + entry.MAIN_ANCHOR + b'<section id="top">Original site</section>\n</main>\n')
        (self.root / "docs/index.html").write_bytes(self.originals["docs/index.html"])

    def snapshot(self):
        return {p: (self.root / p).read_bytes() for p in self.originals}

    def test_full_readme_source_and_original_suffix_are_preserved(self):
        entry.materialize_declaration(self.root, check=False)
        for relative in entry.PATHS:
            raw = (self.root / relative).read_bytes()
            block = entry.declaration_prefix(relative, SOURCE)
            self.assertTrue(raw.startswith(entry.prefix(relative) + block))
            self.assertEqual(raw.replace(block, b"", 1), self.originals[relative])
        self.assertIn(SOURCE, (self.root / "README.md").read_bytes())

    def test_static_full_html_is_first_and_does_not_hide_text(self):
        entry.materialize_declaration(self.root, check=False)
        raw = (self.root / "docs/index.html").read_bytes()
        block = entry.declaration_html(SOURCE)
        self.assertIn(entry.MAIN_ANCHOR + block, raw)
        self.assertEqual(raw.replace(block, b"", 1).replace(entry.NAV_LINK, b"", 1), self.originals["docs/index.html"])
        self.assertNotIn(b"<script>", block)
        self.assertNotIn(b"<details", block)
        self.assertNotIn(b"<iframe", block)
        reader = TextReader()
        reader.feed(block.decode())
        text = " ".join(" ".join(reader.parts).split())
        for paragraph in SOURCE.decode().strip().split("\n\n"):
            self.assertIn(" ".join(paragraph.lstrip("# ").split()), text)

    def test_replay_is_idempotent(self):
        entry.materialize_declaration(self.root, check=False)
        before = self.snapshot()
        self.assertEqual(entry.materialize_declaration(self.root, check=False), [])
        self.assertEqual(entry.materialize_declaration(self.root, check=True), [])
        self.assertEqual(before, self.snapshot())

    def test_check_only_never_writes(self):
        with self.assertRaisesRegex(ValueError, "NOT_CURRENT"):
            entry.materialize_declaration(self.root, check=True)
        self.assertEqual(self.snapshot(), self.originals)

    def test_source_mutation_blocks_all_writes(self):
        (self.root / entry.DECLARATION_PATH).write_bytes(SOURCE + b"changed")
        with self.assertRaisesRegex(ValueError, "SOURCE_BLOB_MISMATCH"):
            entry.materialize_declaration(self.root, check=False)
        self.assertEqual(self.snapshot(), self.originals)

    def test_missing_source_blocks_all_writes(self):
        (self.root / entry.DECLARATION_PATH).unlink()
        with self.assertRaisesRegex(ValueError, "SOURCE_MISSING_OR_UNSAFE"):
            entry.materialize_declaration(self.root, check=False)
        self.assertEqual(self.snapshot(), self.originals)

    def test_missing_last_target_prevents_earlier_writes(self):
        (self.root / "docs/index.html").unlink()
        with self.assertRaisesRegex(ValueError, "TARGET_MISSING_OR_UNSAFE"):
            entry.materialize_declaration(self.root, check=False)
        self.assertEqual((self.root / "README.md").read_bytes(), self.originals["README.md"])

    def test_conflicting_marker_blocks_all_writes(self):
        path = self.root / "docs/index.html"
        path.write_bytes(path.read_bytes() + entry.DECLARATION_START)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "PREFIX_CONFLICT"):
            entry.materialize_declaration(self.root, check=False)
        self.assertEqual(self.snapshot(), before)

    def test_duplicate_main_anchor_blocks_all_writes(self):
        path = self.root / "docs/index.html"
        path.write_bytes(path.read_bytes() + entry.MAIN_ANCHOR)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "ANCHOR_CONFLICT"):
            entry.materialize_declaration(self.root, check=False)
        self.assertEqual(self.snapshot(), before)

    def test_source_symlink_is_rejected(self):
        path = self.root / entry.DECLARATION_PATH
        other = self.root / "source.txt"
        other.write_bytes(SOURCE)
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "SOURCE_MISSING_OR_UNSAFE"):
            entry.materialize_declaration(self.root, check=False)
        self.assertEqual(self.snapshot(), self.originals)

    def test_target_symlink_is_rejected(self):
        path = self.root / "docs/index.html"
        other = self.root / "page.html"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "TARGET_MISSING_OR_UNSAFE"):
            entry.materialize_declaration(self.root, check=False)
        self.assertEqual((self.root / "README.md").read_bytes(), self.originals["README.md"])

    def test_machine_entrypoints_link_to_the_same_source(self):
        for relative in entry.PATHS[1:]:
            prefix = "../" if relative.startswith("next/") else ""
            self.assertIn(("(" + prefix + entry.DECLARATION_PATH + ")").encode(),
                          entry.declaration_prefix(relative, SOURCE))

    def test_tampered_projection_is_detected_and_repaired(self):
        entry.materialize_declaration(self.root, check=False)
        before = self.snapshot()
        path = self.root / "README.md"
        path.write_bytes(path.read_bytes().replace(SOURCE, SOURCE.replace(b"q.e.d.", b"TAMPERED"), 1))
        with self.assertRaisesRegex(ValueError, "NOT_CURRENT"):
            entry.materialize_declaration(self.root, check=True)
        entry.materialize_declaration(self.root, check=False)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()

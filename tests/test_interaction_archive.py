# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
from pathlib import Path
import stat
import tempfile
import unittest

from tools import qikvrt_interaction_archive as archive


FAKE_AGE = r'''#!/usr/bin/env python3
import pathlib
import sys
args = sys.argv[1:]
if '--encrypt' in args:
    output = pathlib.Path(args[args.index('--output') + 1])
    source = pathlib.Path(args[-1])
    output.write_bytes(b'AGE-TEST\0' + source.read_bytes()[::-1])
    raise SystemExit(0)
if '--decrypt' in args:
    source = pathlib.Path(args[-1])
    raw = source.read_bytes()
    if not raw.startswith(b'AGE-TEST\0'):
        raise SystemExit(7)
    sys.stdout.buffer.write(raw[len(b'AGE-TEST\0'):][::-1])
    raise SystemExit(0)
raise SystemExit(9)
'''


class InteractionArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive_root = self.root / "private-repository" / "interaction-archive"
        self.fake_age = self.root / "age"
        self.fake_age.write_text(FAKE_AGE, encoding="utf-8")
        self.fake_age.chmod(self.fake_age.stat().st_mode | stat.S_IXUSR)
        self.identity = self.root / "identity.txt"
        self.identity.write_text("test identity\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def append_args(self, content: Path, role: str, event_id: str):
        return type("Args", (), {
            "confirm": archive.CONFIRM_APPEND,
            "role": role,
            "consent_id": "consent-2026-07-25",
            "purpose": "scientific_interaction_continuity",
            "content_file": str(content),
            "max_bytes": 1024,
            "archive_root": str(self.archive_root),
            "event_id": event_id,
            "conversation_id": "conversation-opaque-001",
            "created_at": "2026-07-25T08:00:00+02:00",
            "recipient": "age1example",
            "age_binary": str(self.fake_age),
            "retention_until": "2027-07-25T00:00:00Z",
            "media_type": "text/plain; charset=utf-8",
        })()

    def test_append_verify_and_export_round_trip(self) -> None:
        user = self.root / "user.txt"
        assistant = self.root / "assistant.txt"
        user.write_text("What is the scientific consequence?", encoding="utf-8")
        assistant.write_text("The answer remains linked to its evidence.", encoding="utf-8")

        first = archive.append(self.append_args(user, "user", "event-user-0001"))
        second = archive.append(self.append_args(assistant, "assistant", "event-assistant-0002"))
        self.assertEqual(first["state"], "PERSISTED_ENCRYPTED")
        self.assertEqual(second["state"], "PERSISTED_ENCRYPTED")
        verified = archive.verify(self.archive_root)
        self.assertEqual(verified["event_count"], 2)

        exported = self.root / "export.json"
        args = type("Args", (), {
            "confirm": archive.CONFIRM_EXPORT,
            "archive_root": str(self.archive_root),
            "identity_file": str(self.identity),
            "age_binary": str(self.fake_age),
            "output": str(exported),
            "request_id": "export-request-001",
            "conversation_id": "conversation-opaque-001",
            "overwrite": False,
        })()
        result = archive.export(args)
        self.assertEqual(result["state"], "EXPORTED")
        value = json.loads(exported.read_text(encoding="utf-8"))
        self.assertEqual(value["event_count"], 2)
        self.assertEqual(value["events"][0]["payload"]["content_utf8"], user.read_text(encoding="utf-8"))
        self.assertFalse(value["events"][0]["privacy"]["plaintext_in_repository"])

    def test_append_requires_exact_consent_and_never_writes_plaintext(self) -> None:
        content = self.root / "secret.txt"
        content.write_text("private input", encoding="utf-8")
        args = self.append_args(content, "user", "event-user-0003")
        args.confirm = "YES"
        with self.assertRaises(archive.ArchiveError):
            archive.append(args)
        args.confirm = archive.CONFIRM_APPEND
        archive.append(args)
        all_repository_bytes = b"".join(path.read_bytes() for path in self.archive_root.rglob("*") if path.is_file())
        self.assertNotIn(b"private input", all_repository_bytes)

    def test_tamper_breaks_verification(self) -> None:
        content = self.root / "input.txt"
        content.write_text("tamper target", encoding="utf-8")
        archive.append(self.append_args(content, "user", "event-user-0004"))
        blob = next((self.archive_root / "blobs").glob("*.age"))
        blob.write_bytes(blob.read_bytes() + b"x")
        with self.assertRaises(archive.ArchiveError):
            archive.verify(self.archive_root)

    def test_tombstone_is_append_only(self) -> None:
        content = self.root / "input.txt"
        content.write_text("retention target", encoding="utf-8")
        archive.append(self.append_args(content, "user", "event-user-0005"))
        args = type("Args", (), {
            "confirm": archive.CONFIRM_TOMBSTONE,
            "archive_root": str(self.archive_root),
            "event_id": "event-user-0005",
            "authorization_id": "retention-request-001",
            "created_at": "2026-07-25T09:00:00+02:00",
        })()
        result = archive.tombstone(args)
        self.assertEqual(result["state"], "TOMBSTONE_RECORDED")
        self.assertEqual(archive.verify(self.archive_root)["event_count"], 2)


if __name__ == "__main__":
    unittest.main()

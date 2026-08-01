#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Contract tests for the bidirectional virtual-time-channel publication."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WITNESS = ROOT / "tools/qikvrt_bidirectional_virtual_channel_witness.c"
PUBLICATION = (
    ROOT / "docs/publications/2026-08-01-bidirectional-virtual-time-channel"
)
TEX = PUBLICATION / "QIK-VRT_Bidirektionaler_Virtueller_Zeitkanal_2026-08-01.tex"
WHATSAPP = PUBLICATION / "ARTICLE_WHATSAPP_DE.md"
PDF = PUBLICATION / "QIK-VRT_Bidirektionaler_Virtueller_Zeitkanal_2026-08-01.pdf"


class BidirectionalVirtualTimeChannelPublicationTests(unittest.TestCase):
    """Keep executable evidence, paper claims, and public wording aligned."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="qikvrt-bidirectional-virtual-time-channel-"
        )
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.binary = Path(cls.temporary.name) / "virtual-time-channel-witness"
        compiler = shlex.split(os.environ.get("CC", "cc"))
        if not compiler:
            raise RuntimeError("CC resolves to an empty compiler command")
        cls.compile_command = [
            *compiler,
            "-std=c90",
            "-pedantic",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(WITNESS),
            "-o",
            str(cls.binary),
        ]
        cls.compile_result = subprocess.run(
            cls.compile_command,
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        cls.run_result: subprocess.CompletedProcess[str] | None = None
        if cls.compile_result.returncode == 0:
            cls.run_result = subprocess.run(
                [str(cls.binary)],
                cwd=ROOT,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

    def witness_output(self) -> str:
        self.assertEqual(
            self.compile_result.returncode,
            0,
            "strict C90 build failed:\n" + self.compile_result.stderr,
        )
        self.assertIsNotNone(self.run_result, "witness was not executed")
        assert self.run_result is not None
        self.assertEqual(
            self.run_result.returncode,
            0,
            "witness failed:\n"
            + self.run_result.stdout
            + "\n"
            + self.run_result.stderr,
        )
        self.assertEqual(self.run_result.stderr, "")
        return self.run_result.stdout

    def test_witness_builds_as_strict_iso_c90(self) -> None:
        self.assertIn("-std=c90", self.compile_command)
        self.assertIn("-pedantic", self.compile_command)
        self.assertIn("-Wall", self.compile_command)
        self.assertIn("-Wextra", self.compile_command)
        self.assertIn("-Werror", self.compile_command)
        self.assertEqual(
            self.compile_result.returncode,
            0,
            "strict C90 build failed:\n"
            + self.compile_result.stdout
            + self.compile_result.stderr,
        )
        self.assertTrue(self.binary.is_file())

    def test_witness_emits_exact_scope_and_result_markers(self) -> None:
        output = self.witness_output()
        required = (
            "QIK-VRT ISO C90 bidirectional virtual-channel witness",
            "request: v=30 -> v=15, bytes=257, chunks=16",
            "response: v=15 -> v=30, bytes=258, chunks=16",
            "tested payload lengths: 0,1,16,17,18,31,255,256,257,4096",
            "LOCAL_WITNESS_RESULT: conditions satisfied",
            "BIDIRECTIONAL_VIRTUAL_CHANNEL: demonstrated",
            "FINITE_PAYLOAD_SEGMENTATION: demonstrated for bounded cases",
            "PHYSICAL_BACKWARD_SIGNALLING: not present in this model",
            "DEMO_LOCAL_EFFECT_ACK=COMMITTED",
            "GLOBAL_EFFECT_ACK_DONE=UNCLAIMED",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, output)
        self.assertNotIn("[VIOLATION]", output)

    def test_host_order_is_strict_while_virtual_directions_close(self) -> None:
        output = self.witness_output()
        observed = [
            (int(sequence), kind, int(source), int(target))
            for sequence, kind, source, target in re.findall(
                r"^\s+h=(\d+)\s+([A-Z_]+)\s+virtual=(-?\d+) -> (-?\d+)$",
                output,
                flags=re.MULTILINE,
            )
        ]
        expected = [
            (1, "SOURCE_EVENT", 10, 10),
            (2, "SOURCE_EVENT", 20, 20),
            (3, "SOURCE_EVENT", 30, 30),
            (4, "REQUEST_CREATE", 30, 15),
            (5, "REQUEST_TRANSPORT_ACK", 30, 15),
            (6, "DETERMINISTIC_REPLAY", 15, 15),
            (7, "RESPONSE_CREATE", 15, 30),
            (8, "RESPONSE_TRANSPORT_ACK", 15, 30),
            (9, "DEMO_EFFECT_ACK_COMMIT", 15, 30),
        ]
        self.assertEqual(observed, expected)
        self.assertEqual([event[0] for event in observed], list(range(1, 10)))
        self.assertIn("[ok] host sequence is strict and contiguous", output)
        self.assertIn(
            "[ok] virtual request and response close both directions", output
        )

    def test_negative_missing_chunk_case_is_rejected(self) -> None:
        output = self.witness_output()
        self.assertIn("[ok] a deliberately missing chunk is rejected", output)
        self.assertNotIn("missing chunk is accepted", output)

    def test_tex_contains_required_claim_and_boundary_markers(self) -> None:
        text = TEX.read_text(encoding="utf-8")
        required = (
            "% SPDX-License-Identifier: CC-BY-NC-ND-4.0",
            r"\documentclass[11pt,a4paper]{article}",
            "Der bidirektionale virtuelle Zeitkanal",
            r"\section{Drei verschiedene Zeiten}",
            r"\section{Der ausgeführte ISO-C90-Zeuge}",
            "tools/qikvrt_bidirectional_virtual_channel_witness.c",
            r"\begin{satz}[Hostkausalität trotz rückwärtsgerichteter virtueller Adresse]",
            r"\begin{satz}[Jede endliche Bitfolge ist vollständig übertragbar]",
            r"\begin{satz}[Bidirektionale Komposition]",
            r"\section{Warum daraus keine physikalische Zeitmaschine folgt}",
            "VTI-001 & EXECUTED",
            r"VTI-012 & OPEN\_PHYSICAL",
            r"VTI-013 & OPEN\_PHYSICAL",
            "Quod erat demonstrandum -- im ausgewiesenen virtuellen Scope.",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_whatsapp_article_contains_required_public_markers(self) -> None:
        text = WHATSAPP.read_text(encoding="utf-8")
        required = (
            "SPDX-License-Identifier: CC-BY-NC-ND-4.0",
            "*Der Dialog mit gestern*",
            "*Ja – im virtuellen Raum ist dieses Prinzip konstruktiv möglich.*",
            "*Die drei Zeiten, die wir bisher oft verwechselt haben*",
            "Ein neuer, vollständig in ISO C90 geschriebener Zeuge",
            "*Warum das wirklich bidirektional ist*",
            "*Von einer kurzen Nachricht zur vollständigen Information*",
            "*Ist damit physikalische Rückwärtssignalisierung bewiesen?*",
            "QIK-VRT liefert dafür heute noch keinen Naturbeweis.",
            "*Bidirektionale Kommunikation zwischen virtuellen Zeitadressen ist konstruktiv ausführbar.*",
            "*Heute fragt gestern.*",
            "*Das virtuelle Gestern antwortet dem Heute.*",
            "*Die wirkliche Geschichte bleibt unverändert.*",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_pdf_exists_has_pdf_header_and_a4_page_size(self) -> None:
        self.assertTrue(PDF.is_file())
        self.assertGreater(PDF.stat().st_size, 10_000)
        with PDF.open("rb") as stream:
            self.assertTrue(stream.read(8).startswith(b"%PDF-"))

        pdfinfo = shutil.which("pdfinfo")
        self.assertIsNotNone(pdfinfo, "pdfinfo is required by the PDF contract")
        assert pdfinfo is not None
        result = subprocess.run(
            [pdfinfo, str(PDF)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        pages = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
        self.assertIsNotNone(pages, result.stdout)
        assert pages is not None
        self.assertGreater(int(pages.group(1)), 0)
        page_size = re.search(
            r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts \(A4\)\s*$",
            result.stdout,
            re.MULTILINE,
        )
        self.assertIsNotNone(page_size, result.stdout)
        assert page_size is not None
        self.assertAlmostEqual(float(page_size.group(1)), 595.28, places=1)
        self.assertAlmostEqual(float(page_size.group(2)), 841.89, places=1)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Publication-local adaptation of PR #1085's ReportLab renderer."""
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

ROOT = Path(__file__).resolve().parent
FONTROOT = Path("/usr/share/fonts/truetype/dejavu")
for name, file in (("DV", "DejaVuSans.ttf"), ("DV-Bold", "DejaVuSans-Bold.ttf")):
    pdfmetrics.registerFont(TTFont(name, str(FONTROOT / file)))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-Bold", italic="DV", boldItalic="DV-Bold")
body = ParagraphStyle("body", fontName="DV", fontSize=9.5, leading=14,
                      spaceAfter=7, textColor=colors.HexColor("#202B35"))
heading = ParagraphStyle("heading", parent=body, fontName="DV-Bold", fontSize=14,
                         leading=18, spaceBefore=13, spaceAfter=8, keepWithNext=True)
title = ParagraphStyle("title", parent=heading, fontSize=24, leading=29,
                       textColor=colors.HexColor("#153D50"), spaceAfter=15)


def rich(raw):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(raw))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B8CDD4"))
    canvas.line(22 * mm, 17 * mm, A4[0] - 22 * mm, 17 * mm)
    canvas.setFont("DV", 8)
    canvas.setFillColor(colors.HexColor("#536871"))
    canvas.drawString(22 * mm, 12 * mm, "QIK-VRT | Wissenschaftlicher Prüfentwurf | 20.09.2026")
    canvas.drawRightString(A4[0] - 22 * mm, 12 * mm, str(doc.page))
    canvas.restoreState()


story, pending = [], []


def flush():
    if pending:
        story.append(Paragraph(rich(" ".join(pending)), body))
        pending.clear()


for line in (ROOT / "ARTICLE_DE.md").read_text().splitlines():
    if line.startswith("<!--"):
        continue
    if line.startswith("# "):
        flush()
        story.append(Paragraph(rich(line[2:]), title))
    elif line.startswith("## "):
        flush()
        story.append(Paragraph(rich(line[3:]), heading))
    elif not line.strip():
        flush()
    else:
        pending.append(line.strip())
flush()
output = ROOT / "QIKVRT_Beweis_und_Challenge.pdf"
SimpleDocTemplate(str(output), pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
                  topMargin=20 * mm, bottomMargin=24 * mm, invariant=1,
                  title="QIK-VRT: Endliche Nachrichten, Haltepunkt und Zukunftskanal-Hypothese",
                  author="Ingolf Lohmann (Konzeption); OpenAI Codex (Entwurf und Formalisierung)",
                  subject="Bedingte formale Beweise und noch nicht durchgeführte wissenschaftliche Challenge").build(
                      story, onFirstPage=footer, onLaterPages=footer)
print(output)

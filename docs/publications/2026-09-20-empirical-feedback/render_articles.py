#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Render the three fixed German manuscripts with ReportLab and embedded fonts."""
from pathlib import Path
import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import matplotlib

ROOT = Path(__file__).resolve().parent
FONTS = Path(matplotlib.get_data_path()) / "fonts/ttf"
for name, file in [("Body", "DejaVuSerif.ttf"), ("BodyBold", "DejaVuSerif-Bold.ttf"),
                   ("Sans", "DejaVuSans.ttf"), ("SansBold", "DejaVuSans-Bold.ttf"),
                   ("Mono", "DejaVuSansMono.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold", italic="Body", boldItalic="BodyBold")
INK = colors.HexColor("#18323e")
MUTED = colors.HexColor("#536771")
styles = {
    "title": ParagraphStyle("Title", fontName="BodyBold", fontSize=23, leading=28, spaceAfter=11, textColor=INK),
    "subtitle": ParagraphStyle("Subtitle", fontName="Sans", fontSize=12, leading=17, spaceAfter=16, textColor=MUTED),
    "heading": ParagraphStyle("Heading", fontName="SansBold", fontSize=11.6, leading=16, spaceBefore=12, spaceAfter=7, textColor=INK, keepWithNext=True),
    "body": ParagraphStyle("Body", fontName="Body", fontSize=10.4, leading=15.1, spaceAfter=8, alignment=TA_LEFT, allowWidows=0, allowOrphans=0),
    "quote": ParagraphStyle("Quote", fontName="Body", fontSize=10, leading=14.5, leftIndent=15, rightIndent=12, spaceAfter=7, textColor=INK),
    "code": ParagraphStyle("Code", fontName="Mono", fontSize=8, leading=11.5, leftIndent=7, spaceAfter=8, backColor=colors.HexColor("#f3f5f6")),
    "table": ParagraphStyle("TableCell", fontName="Sans", fontSize=8.2, leading=11.5),
    "thead": ParagraphStyle("TableHead", fontName="SansBold", fontSize=8.1, leading=11.3, textColor=INK),
}


def inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Mono" size="8.5">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#c7d0d5"))
    canvas.line(52, 43, A4[0] - 52, 43)
    canvas.setFillColor(MUTED)
    canvas.setFont("Sans", 7.6)
    canvas.drawString(52, 29, "QIK-VRT · Empirische Rückkopplung · 20. September 2026")
    canvas.drawRightString(A4[0] - 52, 29, str(doc.page))


def render(source, output):
    text = re.sub(r"<!--.*?-->", "", source.read_text(encoding="utf-8"), flags=re.S)
    lines = text.splitlines()
    story = []
    paragraph = []

    def flush():
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), styles["body"]))
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush()
        elif line.startswith("```"):
            flush()
            index += 1
            code = []
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(html.escape(lines[index]))
                index += 1
            story.append(Paragraph("<br/>".join(code), styles["code"]))
        elif line.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [x.strip() for x in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", cell) for cell in cells):
                    style = styles["thead"] if not rows else styles["table"]
                    rows.append([Paragraph(inline(cell), style) for cell in cells])
                index += 1
            index -= 1
            table = Table(rows, colWidths=[57, 95, 67, 99, A4[0] - 104 - 318], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eff1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#879da7")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#cfd9de")),
            ]))
            story.extend([table, Spacer(1, 10)])
        elif line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            style = "title" if level == 1 else "subtitle" if level == 2 else "heading"
            story.append(Paragraph(inline(line.lstrip("# ")), styles[style]))
        elif line.startswith(">"):
            flush()
            if line.lstrip("> "):
                story.append(Paragraph(inline(line.lstrip("> ")), styles["quote"]))
        elif line == "---":
            flush()
            story.append(Spacer(1, 8))
        else:
            paragraph.append(line)
        index += 1
    flush()
    title = next(line[2:] for line in lines if line.startswith("# "))
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=52, rightMargin=52,
                            topMargin=48, bottomMargin=58, title=title,
                            author="Ingolf Lohmann", subject="Methodischer Diskussionsbeitrag; künstlicher Softwaredemonstrator")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    for source, output in [
        ("ARTICLE_SCIENTIFIC_DE.md", "QIKVRT_Empirische_Rueckkopplung_Fachartikel.pdf"),
        ("ARTICLE_PUBLIC_DE.md", "QIKVRT_Die_Welt_antwortet.pdf"),
        ("OPEN_LETTER_DUECK_DE.md", "QIKVRT_Offener_Brief_Gunter_Dueck.pdf"),
    ]:
        render(ROOT / source, ROOT / output)
        print(output)

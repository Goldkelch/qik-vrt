#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Deterministic publication renderer for this evidence carrier.
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
import re
ROOT=Path(__file__).resolve().parent
FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
BOLD=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
OBLIQUE=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf')
for x in (FONT,BOLD,OBLIQUE):
    if not x.is_file(): raise SystemExit('HOLD: deterministic DejaVu font unavailable')
pdfmetrics.registerFont(TTFont('DV',str(FONT)));pdfmetrics.registerFont(TTFont('DV-Bold',str(BOLD)));pdfmetrics.registerFont(TTFont('DV-Oblique',str(OBLIQUE)))
body=ParagraphStyle('body',fontName='DV',fontSize=10.2,leading=15,spaceAfter=7,textColor=colors.HexColor('#202124'))
h1=ParagraphStyle('h1',fontName='DV-Bold',fontSize=17,leading=21,spaceBefore=13,spaceAfter=8)
title=ParagraphStyle('title',fontName='DV-Bold',fontSize=25,leading=30,alignment=1,spaceAfter=10)
subtitle=ParagraphStyle('subtitle',fontName='DV',fontSize=13,leading=19,alignment=1,spaceAfter=18)
author=ParagraphStyle('author',fontName='DV',fontSize=11,leading=16,alignment=1,textColor=colors.HexColor('#4B5563'))
quote=ParagraphStyle('quote',parent=body,leftIndent=12*mm,rightIndent=8*mm,borderColor=colors.HexColor('#9CA3AF'),borderWidth=1,borderPadding=7,fontName='DV-Oblique')
formula=ParagraphStyle('formula',parent=body,alignment=1,fontName='DV-Bold',fontSize=11,leading=18)
bullet=ParagraphStyle('bullet',parent=body,leftIndent=7*mm,firstLineIndent=-4*mm,bulletIndent=1*mm,spaceAfter=3)
def footer(c,d):
 c.saveState();c.setFont('DV',8);c.setFillColor(colors.HexColor('#555555'));c.drawString(22*mm,12*mm,'Ingolf Lohmann — Eine Nachricht aus der Zukunft braucht einen Empfänger in der Gegenwart');c.drawRightString(A4[0]-22*mm,12*mm,str(d.page));c.restoreState()
lines=(ROOT/'article.md').read_text(encoding='utf-8').splitlines();lines=lines[lines.index('## Abstract'):];story=[Spacer(1,22*mm),Paragraph('Eine Nachricht aus der Zukunft braucht einen Empfänger in der Gegenwart',title),Paragraph('Was Quantenexperimente zeigen, was QIK-VRT daraus technisch macht und woran ein wirklicher Rückwärtskanal zu erkennen wäre',subtitle),Spacer(1,8*mm),Paragraph('Ingolf Lohmann',author),Paragraph('Fassung 1.0 — 13. September 2026',author),Spacer(1,22*mm),Paragraph('<b>Evidenzgrenze</b><br/>Experimentelle Quantenkorrelation, retrokausale Modellierung, informatische Retrogradität und ein operationaler physischer Rückwärtskanal werden als getrennte Nachweisstufen behandelt.',quote),Spacer(1,20*mm),Paragraph('Working Paper · CC BY-NC-ND 4.0',author),PageBreak()];para=[]
def flush():
 global para
 if not para:return
 s=' '.join(x.strip() for x in para).strip();para=[];s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s);s=re.sub(r'\*(.+?)\*',r'<i>\1</i>',s);story.append(Paragraph(s,body))
for line in lines:
 if line.startswith('## '):flush();story.append(Paragraph(line[3:],h1))
 elif line.startswith('> '):flush();story.append(Paragraph(re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',line[2:]),quote))
 elif re.match(r'^\d+\. ',line):flush();m=re.match(r'^(\d+)\. (.*)$',line);story.append(Paragraph(m.group(2),bullet,bulletText=m.group(1)+'.'))
 elif line.startswith('- '):flush();story.append(Paragraph(re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',line[2:]),bullet,bulletText='•'))
 elif line.strip() in {'P(Y, Z | X).','P(Y | X) = sum_Z P(Y, Z | X) = P(Y).','P(Y | do(X=0)) != P(Y | do(X=1)).'}:flush();story.append(Paragraph(line.strip(),formula))
 elif line.strip()=='---':flush();story.append(Spacer(1,4*mm))
 elif not line.strip():flush()
 elif line.startswith('# '):continue
 else:para.append(line)
flush();out=ROOT/'Eine_Nachricht_aus_der_Zukunft_QIK-VRT_Lohmann_2026-09-13.pdf';doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=22*mm,leftMargin=22*mm,topMargin=20*mm,bottomMargin=20*mm,title='Eine Nachricht aus der Zukunft braucht einen Empfänger in der Gegenwart',author='Ingolf Lohmann',subject='QIK-VRT Retrokausalität Delayed Choice',invariant=1);doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(out)

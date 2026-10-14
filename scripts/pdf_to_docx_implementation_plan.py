#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from pypdf import PdfReader
ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / 'docs' / 'CarbyneSentinel_Implementation_Plan.pdf'
DOCX = ROOT / 'docs' / 'CarbyneSentinel_Implementation_Plan.docx'

def is_footer(line: str) -> bool:
    return line.startswith('CarbyneSentinel Implementation Plan') and 'page' in line

def is_h1(s: str) -> bool:
    if len(s) >= 90 or not s[:1].isdigit():
        return False
    first = s.split(' ', 1)[0]
    return first.count('.') == 1 and first.endswith('.') is False and ('.' in first)

def is_h2(s: str) -> bool:
    if len(s) >= 95 or not s[:1].isdigit():
        return False
    first = s.split(' ', 1)[0]
    parts = first.split('.')
    return 2 <= first.count('.') <= 2 and all((p.isdigit() for p in parts if p != ''))

def add_block(doc: Document, s: str) -> None:
    if not s:
        return
    if s.startswith('CARBYNESENTINEL') or s == 'Implementation Plan':
        p = doc.add_paragraph()
        run = p.add_run(s)
        run.bold = True
        run.font.size = Pt(16)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return
    first = s.split(' ', 1)[0]
    if is_h1(s):
        doc.add_heading(s, level=1)
        return
    if is_h2(s) or (first[:1].isdigit() and first.count('.') >= 2 and (len(s) < 95) and all((p.isdigit() for p in first.split('.') if p))):
        doc.add_heading(s, level=2)
        return
    if s.startswith('- '):
        doc.add_paragraph(s[2:].strip(), style='List Bullet')
        return
    if s.startswith('[ ]') or s.startswith('[x]') or s.startswith('[X]'):
        doc.add_paragraph(s, style='List Bullet')
        return
    if first[:1].isdigit() and first.endswith('.') and (len(s) > 90):
        doc.add_paragraph(s, style='List Number')
        return
    doc.add_paragraph(s)

def convert() -> Path:
    if not PDF.is_file():
        raise SystemExit(f'PDF not found: {PDF}')
    reader = PdfReader(str(PDF))
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
    normal = doc.styles['Normal']
    normal.font.name = 'Calibri'
    normal.font.size = Pt(11)
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ''
        text = text.replace('ﬂ', 'fl').replace('ﬁ', 'fi')
        lines = [ln.strip() for ln in text.splitlines()]
        buf: list[str] = []

        def flush() -> None:
            if not buf:
                return
            s = ' '.join(buf).strip()
            buf.clear()
            add_block(doc, s)
        for ln in lines:
            if not ln or is_footer(ln):
                flush()
                continue
            if ln[:1].isdigit() and '. ' in ln[:8] and (len(ln) < 90) and (not ln.startswith('-')):
                flush()
                add_block(doc, ln)
                continue
            buf.append(ln)
        flush()
        if i < len(reader.pages) - 1:
            doc.add_page_break()
    DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(DOCX))
    return DOCX
if __name__ == '__main__':
    path = convert()
    print(f'PDF kept:  {PDF} ({PDF.stat().st_size} bytes)')
    print(f'DOCX wrote: {path} ({path.stat().st_size} bytes)')

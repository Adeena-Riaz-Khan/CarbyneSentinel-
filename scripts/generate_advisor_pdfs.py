from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
OUT = Path(__file__).resolve().parents[1] / 'docs'
OUT.mkdir(parents=True, exist_ok=True)
NAVY = HexColor('#1a365d')
TEAL = HexColor('#2c7a7b')
GRAY = HexColor('#4a5568')
LIGHT = HexColor('#edf2f7')

def make_styles():
    base = getSampleStyleSheet()
    return {'title': ParagraphStyle('T', parent=base['Title'], fontSize=16, textColor=NAVY, spaceAfter=4, leading=20, alignment=TA_CENTER), 'subtitle': ParagraphStyle('ST', parent=base['Normal'], fontSize=9, textColor=GRAY, spaceAfter=12, alignment=TA_CENTER, leading=12), 'h1': ParagraphStyle('H1', parent=base['Heading1'], fontSize=11, textColor=NAVY, spaceBefore=10, spaceAfter=4, leading=14), 'h2': ParagraphStyle('H2', parent=base['Heading2'], fontSize=10, textColor=TEAL, spaceBefore=7, spaceAfter=3, leading=12), 'body': ParagraphStyle('B', parent=base['Normal'], fontSize=8.5, textColor=black, leading=11, spaceAfter=3, alignment=TA_JUSTIFY), 'bullet': ParagraphStyle('Bu', parent=base['Normal'], fontSize=8.5, textColor=black, leading=11, leftIndent=0), 'small': ParagraphStyle('Sm', parent=base['Normal'], fontSize=7.5, textColor=GRAY, leading=9, spaceAfter=2), 'cell': ParagraphStyle('C', parent=base['Normal'], fontSize=7.5, textColor=black, leading=9), 'cellh': ParagraphStyle('CH', parent=base['Normal'], fontSize=7.5, textColor=white, leading=9, fontName='Helvetica-Bold'), 'footer': ParagraphStyle('F', parent=base['Normal'], fontSize=7, textColor=GRAY, alignment=TA_CENTER)}

def hr():
    return HRFlowable(width='100%', thickness=0.6, color=NAVY, spaceBefore=2, spaceAfter=6)

def bullets(items, styles):
    return ListFlowable([ListItem(Paragraph(i, styles['bullet']), leftIndent=8, bulletColor=TEAL) for i in items], bulletType='bullet', start='•', leftIndent=12, spaceBefore=1, spaceAfter=4)

def table(headers, rows, styles, col_widths):
    data = [[Paragraph(h, styles['cellh']) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), styles['cell']) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), white), ('BACKGROUND', (0, 1), (-1, -1), LIGHT), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT, white]), ('GRID', (0, 0), (-1, -1), 0.3, HexColor('#cbd5e0')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t

def pdf1():
    path = OUT / 'Advisor_Update_Current_Datasets.pdf'
    styles = make_styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
    story = []
    story.append(Paragraph('CarbyneSentinel — Dataset Status Update', styles['title']))
    story.append(Paragraph('Advisor briefing · Current corpora, schema, usability &amp; gaps · Sep 2026', styles['subtitle']))
    story.append(hr())
    story.append(Paragraph('1. Purpose of this note', styles['h1']))
    story.append(Paragraph('Short status on the Solidity vulnerability corpora we currently hold, how they are normalized into a shared schema, what each source is good for, and what is still missing for the obfuscation / evasion evaluation planned in the master roadmap.', styles['body']))
    story.append(Paragraph('2. Shared target schema', styles['h1']))
    story.append(Paragraph('All processed entries are meant to follow <b>target_schema.json</b>. Core fields:', styles['body']))
    story.append(bullets(['<b>Identity:</b> contract_id, source_dataset, source_code_path, bytecode_path', '<b>Label:</b> vulnerable | benign', '<b>Types:</b> vulnerability_types[] + primary_vulnerability_type (multi-label + single primary for splits)', '<b>Compile:</b> compiler_version, compiled_successfully', '<b>GNN helpers:</b> vulnerable_function_name, vulnerable_line_numbers, vulnerability_class_id', '<b>LLM helpers:</b> vulnerable_function_snippet, explanation, severity (left null unless source provides them)'], styles))
    story.append(Paragraph('Vocabulary (12 classes)', styles['h2']))
    story.append(Paragraph('reentrancy · integer_overflow · access_control · unchecked_call · time_manipulation · front_running · bad_randomness · denial_of_service · short_address · <b>tx_origin</b> (kept as its own class) · other · none', styles['body']))
    story.append(Paragraph("Note: the old single field <font color='#c05621'>vulnerability_type</font> was replaced by the list + primary pair above.", styles['small']))
    story.append(Paragraph('3. What we have right now', styles['h1']))
    story.append(table(['Dataset', 'Scale (approx.)', 'What it looks like', 'Label quality'], [['SolidiFI', '350 (in master)', 'Injected buggy .sol files; BugLog line locs', 'High — researcher-injected bugs'], ['SmartBugs Curated', '143 (in master)', '.sol + vulnerabilities.json (DASP tags)', 'Gold — hand-labeled'], ['DIVE', '~19.6k vuln / ~2.7k benign', 'Opcode / feature JSONL; multi-hot labels', 'Tool-derived; useful at scale'], ['DAppSCAN', '~5.0k', 'Audit-finding → SWC → our vocab', 'Audit-based; folder noise'], ['DeFiHackLabs', '~848 PoCs', 'Foundry exploit scripts, not clean .sol', 'Real hacks; needs manual cleanup'], ['Slither HF', 'raw / not fully wired', 'Parquet: source + Slither output', 'Tool labels — best as benign pool']], styles, [2.6 * cm, 3.2 * cm, 6.2 * cm, 4.5 * cm]))
    story.append(Spacer(1, 6))
    story.append(Paragraph('<b>Normalized master set (SolidiFI + SmartBugs):</b> 493 contracts · all labeled vulnerable · 466/493 compiled successfully · primary types dominated by unchecked_call (152), reentrancy (81), integer_overflow (65), time_manipulation (55), front_running (54), tx_origin (50).', styles['body']))
    story.append(Paragraph('4. Issues &amp; limitations', styles['h1']))
    story.append(bullets(['<b>SolidiFI compiler:</b> most contracts need solc 0.5.17 (payable syntax) despite 0.4.x pragmas — 327/350 used fallback.', '<b>SmartBugs compile gaps:</b> 27 failures (solc &lt;0.4.11 unsupported by py-solc-x; Windows 0.4.15 nightly pragma issues). Kept with compiled_successfully=false.', '<b>DIVE:</b> opcode-centric; not the same tidy source+.sol pairing as SolidiFI/SmartBugs; multi-label mapping needed care.', '<b>DAppSCAN:</b> inconsistent folder layout; some path skips; line-level annotations often missing.', '<b>DeFiHackLabs:</b> exploit reproductions — vulnerable contract source often must be fetched separately; not drop-in labeled .sol.', '<b>Slither HF:</b> not human-verified; treat as weak labels / benign filtering only.', '<b>Cross-dataset:</b> no full dedup yet (duplicate_of mostly null); LLM explanation fields intentionally empty.', '<b>No obfuscated pairs:</b> none of these corpora provide verified “same bug, after disguise” examples.'], styles))
    story.append(Paragraph('5. What can / cannot be used (for now)', styles['h1']))
    story.append(table(['Use case', 'OK to use', 'Not ready / avoid'], [['Train/test structural &amp; LLM detectors', 'SolidiFI + SmartBugs master (493); DIVE for scale', 'DeFiHackLabs as clean .sol without cleanup'], ['Line/function-level GNN supervision', 'SolidiFI + SmartBugs (locs available)', 'Most DAppSCAN / DeFiHackLabs entries'], ['Benign / clean pool', 'DIVE benign subset; Slither-clean filter (planned)', 'Assuming all audit corpora are clean'], ['Real-world attack ground truth', 'DeFiHackLabs (after per-case curation); DAppSCAN for cross-check', 'Treating PoC folders as ready contracts'], ['Obfuscation / evasion benchmark', '— (must build)', 'Any current dataset as-is — gap']], styles, [4.0 * cm, 6.5 * cm, 6.0 * cm]))
    story.append(Paragraph('6. Bottom line for the advisor', styles['h1']))
    story.append(Paragraph('We have a usable labeled foundation (especially SolidiFI + SmartBugs under one schema) plus larger secondary corpora for scale and real-world signal. What we still lack — and what the roadmap requires — is a <b>verified obfuscation benchmark</b>: paired original vs. deliberately disguised vulnerable contracts where the bug is proven to still trigger. That is the planned custom dataset contribution (see companion PDF).', styles['body']))
    story.append(Spacer(1, 8))
    story.append(Paragraph('CarbyneSentinel · Dataset pipeline · Internal advisor update · Not for public distribution', styles['footer']))
    doc.build(story)
    return path

def pdf2():
    path = OUT / 'Advisor_Update_Obfuscation_Dataset_Needs.pdf'
    styles = make_styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
    story = []
    story.append(Paragraph('CarbyneSentinel — Obfuscation Benchmark Dataset', styles['title']))
    story.append(Paragraph('Advisor briefing · What we need to build &amp; publish · from Master Roadmap Step 11 · Sep 2026', styles['subtitle']))
    story.append(hr())
    story.append(Paragraph('1. Why this dataset', styles['h1']))
    story.append(Paragraph('Existing corpora label vulnerable contracts, but they do <b>not</b> test whether a detector still catches the same vulnerability after the code is deliberately disguised to evade detection. Roadmap Step 11 (Obfuscation Benchmark) fills that gap: take labeled vulnerable contracts, apply controlled obfuscation, <b>verify the bug still works</b>, then measure detector survival — especially the Manipulation Fingerprint Detector and the fused pipeline.', styles['body']))
    story.append(Paragraph('2. Research question the dataset must support', styles['h1']))
    story.append(Paragraph('Does the detector (structural / semantic / fingerprint / fused) still flag the vulnerability once the source (and resulting bytecode) has been transformed to look different, while the exploit semantics remain intact?', styles['body']))
    story.append(Paragraph('3. What kind of dataset we are looking for', styles['h1']))
    story.append(bullets(['<b>Paired examples:</b> (original vulnerable contract, obfuscated variant) sharing the same ground-truth bug type.', '<b>Verified persistence:</b> each obfuscated variant must pass a check that the vulnerability still triggers (PoC / test — not “looks similar”).', '<b>Controlled transforms:</b> named obfuscation techniques (e.g. identifier renaming, dead code, control-flow flattening, opaque predicates) applied alone and in combination.', '<b>Base sources:</b> SolidiFI + SmartBugs (precise labels) as primary seeds; selected DeFiHackLabs cases for real-world attack realism.', '<b>Comparable benign/disguised controls:</b> where useful, benign contracts obfuscated the same way (to test false positives on “looks disguised”).', '<b>Publishable:</b> documentation, license, stable IDs — aimed at Zenodo / Hugging Face (Roadmap Step 14).'], styles))
    story.append(Paragraph('4. Fields / details each record should have', styles['h1']))
    story.append(table(['Field group', 'Required details'], [['Pair identity', 'pair_id; original_contract_id; obfuscated_contract_id; source_dataset (solidifi / smartbugs / defihacklabs)'], ['Vulnerability ground truth', 'Same vocabulary as target_schema; primary type; line/function anchors on the original (and remapped if possible)'], ['Obfuscation metadata', 'technique_ids[]; intensity / pass count; tool/version; seed; whether transform is source-level vs bytecode-level'], ['Verification', 'verified_still_vulnerable (bool); verification_method (unit test / Foundry PoC / replay); verifier_log_path; date'], ['Artifacts', 'paths to original .sol, obfuscated .sol, both bytecodes if compiled; compile success flags + solc versions'], ['Evaluation hooks', 'detector scores before/after (optional); split tag (train/val/test) with pair leakage prevented'], ['Provenance', 'notes; license; exclusion reason if a candidate failed verification']], styles, [4.2 * cm, 12.3 * cm]))
    story.append(Paragraph('5. Acceptance criteria (what “done” means)', styles['h1']))
    story.append(bullets(['Every published obfuscated sample has <b>verification = true</b> (bug still exploitable / still present by agreed test).', 'No train/test leakage across a pair (both sides of a pair stay in the same split).', 'Coverage across several vulnerability types (at least reentrancy, access_control, unchecked_call, tx_origin as priorities).', 'Small-scale pipeline already exists; next step is <b>scale-up</b> to a full release set (per roadmap).', 'Separate from DeFi-Intent-Bench (arbitrage vs exploit traces) — that is a different custom dataset.'], styles))
    story.append(Paragraph('6. What this is not', styles['h1']))
    story.append(bullets(['Not just “renamed files” without proving the bug survives.', 'Not unlabeled random obfuscation dumps.', 'Not a replacement for SolidiFI/SmartBugs — it <b>extends</b> them for evasion evaluation.'], styles))
    story.append(Paragraph('7. Bottom line for the advisor', styles['h1']))
    story.append(Paragraph('We will build a compact, verified <b>original ↔ obfuscated</b> vulnerability dataset so we can report whether detectors (and especially the disguise fingerprint + fusion) remain effective under deliberate evasion. Base material comes from our existing labeled corpora; the novel contribution is the verified obfuscated pairs and the public benchmark release.', styles['body']))
    story.append(Spacer(1, 8))
    story.append(Paragraph('CarbyneSentinel · Master Roadmap Step 11 · Internal advisor update · Not for public distribution', styles['footer']))
    doc.build(story)
    return path
if __name__ == '__main__':
    p1 = pdf1()
    p2 = pdf2()
    print('Wrote:', p1)
    print('Wrote:', p2)
    print('Sizes:', p1.stat().st_size, p2.stat().st_size)

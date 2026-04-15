#!/usr/bin/env python3
"""
MiroFish Prep — Document Analyzer
Reads PDF/MD/TXT files and produces a structured analysis:
- File inventory with character counts
- Named entity detection (people, organizations, locations)
- Entity pollution risk assessment
- MiroFish compatibility warnings
"""

import json
import re
import sys
import os
from pathlib import Path
from typing import Optional

# MiroFish limits
MIROFISH_ONTOLOGY_CHAR_LIMIT = 50_000
MIROFISH_ALLOWED_EXTENSIONS = {'.pdf', '.md', '.markdown', '.txt'}


def extract_text(file_path: Path) -> Optional[str]:
    """Extract text from PDF, MD, or TXT files."""
    ext = file_path.suffix.lower()
    if ext not in MIROFISH_ALLOWED_EXTENSIONS:
        return None

    if ext == '.pdf':
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except ImportError:
            try:
                import pdfplumber
                with pdfplumber.open(str(file_path)) as pdf:
                    return "\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
            except ImportError:
                return f"[PDF extraction unavailable — install PyMuPDF: pip install pymupdf]"
    else:
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return file_path.read_text(encoding='utf-8', errors='replace')


def detect_document_type(text: str, filename: str) -> str:
    """Classify document by content analysis."""
    lower = text[:3000].lower()
    fname = filename.lower()

    if any(k in fname for k in ['synopsis', 'sinopsis']):
        return 'SYNOPSIS'
    if any(k in fname for k in ['bible', 'seed', 'reality']):
        return 'SHOW_BIBLE'
    if any(k in fname for k in ['character', 'breakdown', 'interrogation']):
        return 'CHARACTER_BREAKDOWN'
    if any(k in fname for k in ['prompt', 'requirement']):
        return 'SIMULATION_PROMPT'
    if any(k in fname for k in ['treatment']):
        return 'TREATMENT'

    if re.search(r'(INT\.|EXT\.|FADE IN|CUT TO|SUPER:)', text[:5000]):
        return 'SCRIPT'
    if re.search(r'(enneagram|mbti|fatal flaw|want:|need:)', lower):
        return 'CHARACTER_BREAKDOWN'
    if re.search(r'(logline|genre|tone|season arc)', lower):
        return 'SHOW_BIBLE'
    if re.search(r'(act one|act two|act three|teaser|cold open)', lower):
        return 'SYNOPSIS'

    return 'DOCUMENT'


def scan_named_entities(text: str) -> dict:
    """
    Quick scan for potential named entities.
    Returns categorized lists. Not NLP — pattern-based heuristics
    optimized for TV/film script materials.
    """
    name_pattern = re.compile(
        r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)\b'
    )
    names = set(name_pattern.findall(text))

    caps_pattern = re.compile(r'\b([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*)\b')
    caps_names = set()
    for match in caps_pattern.findall(text):
        if match not in {
            'INT', 'EXT', 'CUT', 'FADE', 'SUPER', 'THE', 'AND', 'BUT',
            'FOR', 'NOT', 'ALL', 'HER', 'HIS', 'SHE', 'HIM', 'HER',
            'WITH', 'FROM', 'THIS', 'THAT', 'THEY', 'WHAT', 'WHEN',
            'WHERE', 'WHO', 'HOW', 'WILL', 'CAN', 'HAS', 'HAD',
            'WAS', 'ARE', 'BEEN', 'HAVE', 'DOES', 'DID', 'WOULD',
            'COULD', 'SHOULD', 'MAY', 'MIGHT', 'MUST', 'SHALL',
            'CONTINUED', 'CONT', 'OFF', 'SCREEN', 'VOICE', 'OVER',
            'ANGLE', 'CLOSE', 'WIDE', 'MEDIUM', 'POV', 'INSERT',
            'FLASHBACK', 'LATER', 'NIGHT', 'DAY', 'MORNING',
            'EVENING', 'AFTERNOON', 'CONTINUOUS', 'SAME', 'TIME',
            'SCENE', 'END', 'BEGIN', 'TITLE', 'CARD', 'BLACK',
            'WHITE', 'BEAT', 'PAUSE', 'SILENCE', 'MATCH',
            'SMASH', 'QUICK', 'SLOW', 'MONTAGE', 'SERIES',
            'SHOTS', 'BACK', 'RESUME', 'PRESENT',
            'PILOT', 'SYNOPSIS', 'SEASON', 'EPISODE',
        } and len(match) > 2:
            caps_names.add(match.title())

    org_patterns = [
        r'\b(Grupo\s+\w+)\b',
        r'\b(\w+\s+(?:Corp|Inc|LLC|Ltd|SA|S\.A\.|de\s+C\.V\.))\b',
        r'\b((?:DEA|FBI|CIA|NSA|DOJ|SEC|ESG))\b',
        r'\b(Walmart|Amazon|Netflix|Forbes|Bloomberg)\b',
        r'\b(El\s+Universal|New\s+York\s+Times|Washington\s+Post)\b',
    ]
    orgs = set()
    for pattern in org_patterns:
        orgs.update(re.findall(pattern, text))

    deceased_patterns = [
        r'(\w+(?:\s+\w+)?)\s+(?:has\s+died|is\s+dead|was\s+(?:murdered|killed))',
        r'death\s+of\s+(\w+(?:\s+\w+)?)',
        r'(\w+(?:\s+\w+)?)\s+(?:died|passed\s+away)',
        r'(\w+(?:\s+\w+)?)\s*\(?\s*(?:deceased|DECEASED|dead|RIP)',
    ]
    deceased = set()
    for pattern in deceased_patterns:
        deceased.update(re.findall(pattern, text))

    return {
        'potential_characters': sorted(names | caps_names),
        'organizations': sorted(orgs),
        'deceased_mentions': sorted(deceased),
    }


def check_pollution_risks(text: str) -> list:
    """
    Scan for entity-pollution risks — words/phrases that Zep's
    entity extractor would turn into junk agents.
    """
    risks = []

    generic_patterns = [
        (r'\bthe\s+siblings\b', 'group reference: "the siblings"'),
        (r'\bthe\s+family\b', 'group reference: "the family"'),
        (r'\bsenators\b', 'generic plural: "senators"'),
        (r'\bgovernors\b', 'generic plural: "governors"'),
        (r'\bcartels?\b', 'generic noun: "cartel(s)"'),
        (r'\bjournalists\b', 'generic plural: "journalists"'),
        (r'\bactivists?\b', 'generic noun: "activist(s)"'),
        (r'\bCEOs\b', 'generic plural: "CEOs"'),
        (r'\bgrandmother\b', 'generic reference: "grandmother"'),
        (r'\bthe\s+thief\b', 'generic reference: "the thief"'),
        (r'\bthe\s+lawyer\b', 'generic reference: "the lawyer"'),
        (r'\bcriminal\s+empire\b', 'abstract concept: "criminal empire"'),
        (r'\bnarco\s+operation\b', 'abstract concept: "narco operation"'),
        (r'\brival\s+(?:family|cartel)\b', 'unnamed group: "rival family/cartel"'),
    ]

    for pattern, description in generic_patterns:
        count = len(re.findall(pattern, text, re.IGNORECASE))
        if count > 0:
            risks.append({
                'pattern': description,
                'count': count,
                'severity': 'HIGH' if count > 5 else 'MEDIUM',
            })

    org_risks = [
        (r'\bWalmart\b', 'organization: "Walmart"'),
        (r'\bDEA\b', 'organization: "DEA"'),
        (r'\bForbes\b', 'organization: "Forbes"'),
        (r'\bWorld\s+Bank\b', 'organization: "World Bank"'),
        (r'\bHarvard\b', 'institution: "Harvard"'),
        (r'\bEl\s+Universal\b', 'organization: "El Universal"'),
    ]

    for pattern, description in org_risks:
        count = len(re.findall(pattern, text))
        if count > 0:
            risks.append({
                'pattern': description,
                'count': count,
                'severity': 'MEDIUM',
            })

    return risks


def analyze_files(file_paths: list[str]) -> dict:
    """Main analysis function. Returns structured JSON report."""
    files = []
    all_text = ""
    total_chars = 0

    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            files.append({
                'path': str(path),
                'name': path.name,
                'error': 'FILE_NOT_FOUND',
            })
            continue

        ext = path.suffix.lower()
        if ext not in MIROFISH_ALLOWED_EXTENSIONS:
            files.append({
                'path': str(path),
                'name': path.name,
                'error': f'UNSUPPORTED_FORMAT ({ext}). MiroFish accepts: PDF, MD, TXT',
            })
            continue

        text = extract_text(path)
        if text is None:
            files.append({
                'path': str(path),
                'name': path.name,
                'error': 'EXTRACTION_FAILED',
            })
            continue

        char_count = len(text)
        doc_type = detect_document_type(text, path.name)

        files.append({
            'path': str(path),
            'name': path.name,
            'chars': char_count,
            'type': doc_type,
            'exceeds_ontology_limit': char_count > MIROFISH_ONTOLOGY_CHAR_LIMIT,
        })

        all_text += f"\n=== {path.name} ===\n{text}\n"
        total_chars += char_count

    entities = scan_named_entities(all_text)
    pollution_risks = check_pollution_risks(all_text)

    warnings = []
    if total_chars > MIROFISH_ONTOLOGY_CHAR_LIMIT:
        warnings.append({
            'type': 'ONTOLOGY_LIMIT',
            'message': (
                f'Total text ({total_chars:,} chars) exceeds MiroFish ontology '
                f'limit ({MIROFISH_ONTOLOGY_CHAR_LIMIT:,} chars). '
                f'The upload document must be curated to fit under the limit.'
            ),
        })

    if pollution_risks:
        high_risks = [r for r in pollution_risks if r['severity'] == 'HIGH']
        if high_risks:
            warnings.append({
                'type': 'ENTITY_POLLUTION',
                'message': (
                    f'{len(high_risks)} high-risk entity pollution patterns found. '
                    f'These WILL become junk agents if uploaded raw to MiroFish.'
                ),
                'details': high_risks,
            })

    return {
        'files': files,
        'total_chars': total_chars,
        'total_files': len([f for f in files if 'error' not in f]),
        'entities': entities,
        'pollution_risks': pollution_risks,
        'warnings': warnings,
        'ontology_limit': MIROFISH_ONTOLOGY_CHAR_LIMIT,
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_documents.py <file1> [file2] [file3] ...")
        print("       python analyze_documents.py --dir <directory>")
        sys.exit(1)

    if sys.argv[1] == '--dir':
        directory = Path(sys.argv[2])
        file_paths = [
            str(f) for f in directory.rglob('*')
            if f.suffix.lower() in MIROFISH_ALLOWED_EXTENSIONS
            and 'node_modules' not in str(f)
        ]
    else:
        file_paths = sys.argv[1:]

    result = analyze_files(file_paths)
    print(json.dumps(result, indent=2, ensure_ascii=False))

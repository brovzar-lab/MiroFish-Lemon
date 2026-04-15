# MiroFish Prep Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Claude Code skill (`/mirofish-prep`) that takes Lemon Studios creative materials and produces a validated, ready-to-upload package for MiroFish simulations.

**Architecture:** A project-scoped Claude Code command file (`.claude/commands/mirofish-prep.md`) with reference files for validation rules and output templates. The skill uses Claude's built-in tools (Read, Write, Glob, Grep, Bash) to analyze documents, extract characters, generate curated files, and run preflight validation. All output goes to `sim-prep/<project-slug>/`.

**Tech Stack:** Claude Code skill (markdown), Python helper scripts for character counting and entity scanning, JSON schemas for output validation.

---

## File Structure

```
/Users/quantumcode/CODE/MIROFISH LEMON/
├── .claude/
│   └── commands/
│       └── mirofish-prep.md              # Main skill file — the /mirofish-prep command
├── sim-prep/                              # Output directory (created per-run)
│   └── <project-slug>/                    # e.g., sim-prep/oro-verde/
│       ├── upload_document.md
│       ├── reality_seed.md
│       ├── character_cast.json
│       ├── simulation_config.json
│       ├── event_seeds.json
│       ├── preflight_report.md
│       ├── upload_checklist.md
│       └── test_config.json
└── scripts/
    └── mirofish-prep/
        ├── analyze_documents.py           # Document analysis helper (char count, entity scan)
        ├── validate_cast.py               # Cast validation (no generics, no orgs, no dead chars)
        ├── generate_config.py             # Simulation config generator with cost controls
        ├── templates/
        │   ├── upload_checklist.md         # Checklist template
        │   ├── simulation_config.template.json  # Config skeleton with safe defaults
        │   └── character_archetypes.json   # Behavioral presets by role type
        └── reference/
            ├── validation_rules.json       # All preflight rules from post-mortem
            └── blocked_entity_patterns.json # Generic nouns, org names to reject
```

**Why this structure:**
- The skill file lives in `.claude/commands/` so it's available as `/mirofish-prep` when you're in the MiroFish Lemon project directory
- Python helper scripts handle the mechanical work (counting chars, scanning entities, validating JSON) more reliably than asking Claude to do arithmetic
- Templates ensure consistent output format across runs
- Reference files encode the Oro Verde post-mortem lessons as data, not just instructions

---

### Task 1: Create the Python document analyzer

**Files:**
- Create: `scripts/mirofish-prep/analyze_documents.py`

This script reads input files and produces a structured analysis that the skill consumes. It replaces the need for Claude to manually count characters and scan for entities.

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p "scripts/mirofish-prep/templates" "scripts/mirofish-prep/reference"
```

- [ ] **Step 2: Write the document analyzer script**

```python
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
            # Fallback: try pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(str(file_path)) as pdf:
                    return "\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
            except ImportError:
                return f"[PDF extraction unavailable — install PyMuPDF: pip install pymupdf]"
    else:
        # MD and TXT — try UTF-8 first, fallback to latin-1
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

    # Content-based detection
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
    # Capitalized multi-word names (likely character names)
    name_pattern = re.compile(
        r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)\b'
    )
    names = set(name_pattern.findall(text))

    # ALL-CAPS words that appear in script format (character names in scripts)
    caps_pattern = re.compile(r'\b([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*)\b')
    caps_names = set()
    for match in caps_pattern.findall(text):
        # Filter out common non-name caps (stage directions, etc.)
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

    # Organization patterns
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

    # "Deceased" detection — past tense death references
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

    # Generic group nouns that become agents
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

    # Organization names that would become agents
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

    # Entity analysis on combined text
    entities = scan_named_entities(all_text)
    pollution_risks = check_pollution_risks(all_text)

    # Warnings
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
```

- [ ] **Step 3: Test the analyzer against Oro Verde V8 materials**

```bash
cd "/Users/quantumcode/CODE/MIROFISH LEMON"
python3 scripts/mirofish-prep/analyze_documents.py \
  "Billy Agents/Billy Docs for Mirofish/OV MIROFISH REALITY SEED V8.md" \
  "Billy Agents/Billy Docs for Mirofish/PILOT SINOPSIS OV V8.txt" \
  "Billy Agents/Billy Docs for Mirofish/JEN_GRISANTI_ORO_VERDE_V8_INTERROGATION.md" \
  "Billy Agents/Billy Docs for Mirofish/V8 MF Seed Prompt.md" \
  "Billy Agents/Billy Docs for Mirofish/ORO VERDE 101 V8.1 09_01_26 CLEAN  TXT.txt"
```

Expected: JSON output with file inventory, entity lists, pollution risks including "Walmart", "the siblings", "grandmother", etc. Total chars ~149K, ontology limit warning triggered.

- [ ] **Step 4: Commit**

```bash
git add scripts/mirofish-prep/analyze_documents.py
git commit -m "feat: add document analyzer for mirofish-prep skill"
```

---

### Task 2: Create the cast validator

**Files:**
- Create: `scripts/mirofish-prep/validate_cast.py`

Validates a character_cast.json file against all rules from the Oro Verde post-mortem.

- [ ] **Step 1: Write the validator**

```python
#!/usr/bin/env python3
"""
MiroFish Prep — Cast Validator
Validates character_cast.json against post-mortem rules.
Every rule here was learned from the $450 Oro Verde failure.
"""

import json
import re
import sys
from pathlib import Path


# Blocked agent name patterns — these all became junk agents in Oro Verde S1
BLOCKED_GENERIC_NOUNS = {
    'senators', 'governors', 'cartels', 'journalists', 'activists',
    'family', 'siblings', 'grandmother', 'grandfather', 'woman', 'man',
    'boy', 'girl', 'child', 'teenager', 'people', 'citizens', 'workers',
    'employees', 'lawyers', 'doctors', 'police', 'military', 'media',
    'public', 'audience', 'investors', 'politicians', 'officials',
    'neighbors', 'friends', 'enemies', 'rivals', 'allies',
    'ceos', 'directors', 'managers', 'agents', 'officers',
    'activism', 'corruption', 'justice', 'power',
}

BLOCKED_ORGANIZATION_PATTERNS = [
    r'^(walmart|amazon|netflix|disney|fox|hbo|universal|paramount)',
    r'^(dea|fbi|cia|nsa|sec|doj|atf|interpol)',
    r'^(grupo\s+\w+)',
    r'^(el\s+universal|new\s+york\s+times|washington\s+post|forbes|bloomberg)',
    r'^(harvard|yale|stanford|mit|princeton)',
    r'\b(corp|inc|llc|ltd|s\.a\.|de\s+c\.v\.)\b',
    r'^(criminal\s+empire|narco\s+operation|cartel|rival)',
    r'^(serrano\s+(family|siblings|name))',
]

BLOCKED_ABSTRACT_CONCEPTS = [
    r'^(activism|corruption|justice|power|authority|violence)$',
    r'^(narco\s+operation|criminal\s+empire|the\s+system)$',
]


def validate_agent_name(name: str) -> list[str]:
    """Validate a single agent name. Returns list of failure reasons."""
    failures = []
    lower = name.lower().strip()

    # Check generic nouns
    if lower in BLOCKED_GENERIC_NOUNS:
        failures.append(f'GENERIC_NOUN: "{name}" is a generic noun, not an individual character')

    # Check organization patterns
    for pattern in BLOCKED_ORGANIZATION_PATTERNS:
        if re.search(pattern, lower):
            failures.append(f'ORGANIZATION: "{name}" matches organization pattern')
            break

    # Check abstract concepts
    for pattern in BLOCKED_ABSTRACT_CONCEPTS:
        if re.search(pattern, lower):
            failures.append(f'ABSTRACT_CONCEPT: "{name}" is an abstract concept, not a character')
            break

    # Check for generic descriptors instead of names
    generic_descriptors = [
        r'^(a|the|an)\s+',           # "the thief", "a woman"
        r'^\d+-year-old\b',          # "fourteen-year-old girl"
        r'^(young|old|unnamed)\s+',  # "young woman", "unnamed thief"
    ]
    for pattern in generic_descriptors:
        if re.search(pattern, lower):
            failures.append(f'GENERIC_DESCRIPTOR: "{name}" is a description, not a proper name')
            break

    # Check minimum name quality — should have at least one capitalized word
    if not re.search(r'[A-ZÁÉÍÓÚÑ]', name):
        failures.append(f'NO_PROPER_NAME: "{name}" contains no capitalized words')

    # F7: First-name-only check for characters who should have full names
    # Some characters legitimately have single names (Reynaldo) but most should
    # have full names. Flag for human review rather than hard fail.
    words = name.strip().split()
    if len(words) == 1 and name[0].isupper() and lower not in {'reynaldo'}:
        failures.append(
            f'FIRST_NAME_ONLY: "{name}" has no surname — verify this is intentional. '
            f'In Oro Verde S1, "Karla" should have been "Karla Serrano" and '
            f'"Javier" should have been "Javier Cordero".'
        )

    return failures


def validate_cast(cast_data: dict) -> dict:
    """
    Validate a full character_cast.json.
    Returns structured validation report.
    """
    results = {
        'status': 'PASS',
        'checks': [],
        'agent_count': 0,
        'failures': 0,
        'warnings': 0,
    }

    agents = cast_data.get('mandatory_agents', [])
    results['agent_count'] = len(agents)

    # Check 1: Agent count
    if len(agents) == 0:
        results['checks'].append({
            'rule': 'AGENT_COUNT',
            'status': 'FAIL',
            'message': 'No mandatory agents defined',
        })
        results['status'] = 'FAIL'
        results['failures'] += 1
    elif len(agents) > 30:
        results['checks'].append({
            'rule': 'AGENT_COUNT',
            'status': 'WARN',
            'message': f'{len(agents)} agents — very high, consider reducing for cost',
        })
        results['warnings'] += 1
    else:
        results['checks'].append({
            'rule': 'AGENT_COUNT',
            'status': 'PASS',
            'message': f'{len(agents)} mandatory agents',
        })

    # Check 2: Individual name validation
    for agent in agents:
        name = agent.get('name', '')
        name_failures = validate_agent_name(name)
        if name_failures:
            for failure in name_failures:
                results['checks'].append({
                    'rule': 'AGENT_NAME',
                    'status': 'FAIL',
                    'message': failure,
                })
                results['failures'] += 1
                results['status'] = 'FAIL'

    # Check 3: Duplicate detection (fuzzy)
    names = [a.get('name', '').lower().strip() for a in agents]
    seen = {}
    for i, name in enumerate(names):
        # Exact duplicate
        if name in seen:
            results['checks'].append({
                'rule': 'DUPLICATE',
                'status': 'FAIL',
                'message': f'Duplicate agent: "{agents[i]["name"]}" (same as #{seen[name]+1})',
            })
            results['failures'] += 1
            results['status'] = 'FAIL'
        else:
            seen[name] = i

        # Partial duplicate (first name matches)
        first_name = name.split()[0] if name else ''
        for j, other in enumerate(names):
            if i != j and first_name and other.startswith(first_name) and name != other:
                # Only flag if they look like the same person
                other_first = other.split()[0]
                if first_name == other_first:
                    results['checks'].append({
                        'rule': 'POSSIBLE_DUPLICATE',
                        'status': 'WARN',
                        'message': (
                            f'Possible duplicate: "{agents[i]["name"]}" and '
                            f'"{agents[j]["name"]}" share first name'
                        ),
                    })
                    results['warnings'] += 1

    # Check 4: Required fields
    required_fields = ['name', 'role', 'stance']
    for agent in agents:
        for field in required_fields:
            if not agent.get(field):
                results['checks'].append({
                    'rule': 'REQUIRED_FIELD',
                    'status': 'FAIL',
                    'message': f'Agent "{agent.get("name", "UNNAMED")}": missing required field "{field}"',
                })
                results['failures'] += 1
                results['status'] = 'FAIL'

    # Check 5: Stance values
    valid_stances = {'protagonist', 'antagonist', 'opposing', 'neutral', 'supportive', 'observer'}
    for agent in agents:
        stance = agent.get('stance', '')
        if stance and stance not in valid_stances:
            results['checks'].append({
                'rule': 'INVALID_STANCE',
                'status': 'WARN',
                'message': f'Agent "{agent["name"]}": stance "{stance}" not in standard set',
            })
            results['warnings'] += 1

    # Check 6: Dead characters in excluded list (not in active agents)
    excluded = cast_data.get('excluded_entities', [])
    excluded_names = {e.get('name', '').lower() for e in excluded}
    for agent in agents:
        if agent.get('name', '').lower() in excluded_names:
            results['checks'].append({
                'rule': 'DEAD_CHARACTER_ACTIVE',
                'status': 'FAIL',
                'message': f'Agent "{agent["name"]}" is in excluded list but also in active agents',
            })
            results['failures'] += 1
            results['status'] = 'FAIL'

    # Check 7: Name hallucination detection (F6)
    # Compare agent names against source material character names if provided
    source_characters = cast_data.get('_source_character_names', [])
    if source_characters:
        source_lower = {n.lower() for n in source_characters}
        for agent in agents:
            agent_name = agent.get('name', '').lower()
            # Check if name is a corruption of a known character
            # "Nesto Vega" vs "Ernesto Vega" — fuzzy match on edit distance
            for source_name in source_lower:
                if agent_name != source_name:
                    # Simple substring check — catches "Nesto" in "Ernesto"
                    a_parts = set(agent_name.split())
                    s_parts = set(source_name.split())
                    overlap = a_parts & s_parts
                    diff = a_parts.symmetric_difference(s_parts)
                    if overlap and diff:
                        # Partial name match — possible hallucination
                        for d in diff:
                            for s in (s_parts - a_parts):
                                if d in s or s in d:
                                    results['checks'].append({
                                        'rule': 'NAME_HALLUCINATION',
                                        'status': 'WARN',
                                        'message': (
                                            f'Agent "{agent["name"]}" may be a corruption of '
                                            f'source character "{[n for n in source_characters if n.lower() == source_name][0]}". '
                                            f'In Oro Verde S1, "Nesto Vega" was a hallucinated corruption of "Ernesto Vega".'
                                        ),
                                    })
                                    results['warnings'] += 1

    # Check 8: Additional agents limit
    max_additional = cast_data.get('max_additional_agents', 0)
    if len(agents) + max_additional > 30:
        results['checks'].append({
            'rule': 'TOTAL_AGENT_LIMIT',
            'status': 'WARN',
            'message': f'Total possible agents ({len(agents)} + {max_additional} = {len(agents) + max_additional}) is high',
        })
        results['warnings'] += 1

    # Summary
    if results['failures'] == 0 and results['warnings'] == 0:
        results['checks'].append({
            'rule': 'SUMMARY',
            'status': 'PASS',
            'message': f'All {len(agents)} agents pass validation',
        })
    elif results['failures'] == 0:
        results['checks'].append({
            'rule': 'SUMMARY',
            'status': 'WARN',
            'message': f'{results["warnings"]} warnings, 0 failures',
        })

    return results


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python validate_cast.py <character_cast.json>")
        sys.exit(1)

    cast_path = Path(sys.argv[1])
    if not cast_path.exists():
        print(f"Error: {cast_path} not found")
        sys.exit(1)

    cast_data = json.loads(cast_path.read_text())
    result = validate_cast(cast_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result['status'] != 'FAIL' else 1)
```

- [ ] **Step 2: Test with a deliberately bad cast (replicating Oro Verde S1 failure)**

Create a test file that mimics the junk agents from the failed run:

```bash
cat > /tmp/bad_cast_test.json << 'EOF'
{
  "mandatory_agents": [
    {"name": "Ingrid Cervantes", "role": "Journalist", "stance": "opposing"},
    {"name": "Walmart", "role": "Retailer", "stance": "supportive"},
    {"name": "senators", "role": "Government", "stance": "neutral"},
    {"name": "Serrano siblings", "role": "Family", "stance": "protagonist"},
    {"name": "fourteen-year-old girl", "role": "Unknown", "stance": "neutral"},
    {"name": "grandmother", "role": "Family elder", "stance": "neutral"},
    {"name": "Javier", "role": "CFO", "stance": "antagonist"},
    {"name": "Javier Cordero", "role": "CFO", "stance": "antagonist"},
    {"name": "criminal empire", "role": "Organization", "stance": "opposing"},
    {"name": "Carmen", "role": "Matriarch", "stance": "neutral"}
  ],
  "excluded_entities": [
    {"name": "Carmen", "reason": "deceased_before_simulation"}
  ]
}
EOF
python3 scripts/mirofish-prep/validate_cast.py /tmp/bad_cast_test.json
```

Expected: FAIL status with specific failures for Walmart (org), senators (generic), Serrano siblings (org pattern), fourteen-year-old girl (generic descriptor), grandmother (generic noun), Javier/Javier Cordero (possible duplicate), criminal empire (abstract), Carmen (dead + active). Also: FIRST_NAME_ONLY warnings for "Javier" and "Carmen" (single-word names that should have surnames).

- [ ] **Step 3: Commit**

```bash
git add scripts/mirofish-prep/validate_cast.py
git commit -m "feat: add cast validator with Oro Verde post-mortem rules"
```

---

### Task 3: Create the config generator

**Files:**
- Create: `scripts/mirofish-prep/generate_config.py`
- Create: `scripts/mirofish-prep/templates/character_archetypes.json`
- Create: `scripts/mirofish-prep/templates/simulation_config.template.json`

- [ ] **Step 1: Write the character archetypes reference**

```json
{
  "_description": "Behavioral presets by character role. Used to auto-calibrate agent parameters in simulation_config.json.",
  "journalist": {
    "activity_level": 0.8,
    "posts_per_hour": 1.2,
    "comments_per_hour": 2.5,
    "active_hours": [8, 9, 10, 11, 14, 15, 16, 19, 20, 21, 22],
    "response_delay_min": 5,
    "response_delay_max": 25,
    "sentiment_bias": -0.3,
    "influence_weight": 2.2
  },
  "ceo_executive": {
    "activity_level": 0.6,
    "posts_per_hour": 0.5,
    "comments_per_hour": 1.0,
    "active_hours": [9, 10, 11, 12, 14, 15, 16, 17, 19, 20],
    "response_delay_min": 15,
    "response_delay_max": 60,
    "sentiment_bias": 0.2,
    "influence_weight": 2.0
  },
  "operations_director": {
    "activity_level": 0.5,
    "posts_per_hour": 0.3,
    "comments_per_hour": 0.8,
    "active_hours": [7, 8, 9, 10, 11, 14, 15, 16, 17, 18],
    "response_delay_min": 10,
    "response_delay_max": 45,
    "sentiment_bias": -0.1,
    "influence_weight": 1.8
  },
  "artist_creative": {
    "activity_level": 0.5,
    "posts_per_hour": 0.4,
    "comments_per_hour": 0.6,
    "active_hours": [10, 11, 14, 15, 19, 20, 21, 22, 23],
    "response_delay_min": 10,
    "response_delay_max": 60,
    "sentiment_bias": 0.1,
    "influence_weight": 1.4
  },
  "cartel_patriarch": {
    "activity_level": 0.3,
    "posts_per_hour": 0.1,
    "comments_per_hour": 0.2,
    "active_hours": [10, 11, 20, 21, 22, 23],
    "response_delay_min": 60,
    "response_delay_max": 300,
    "sentiment_bias": -0.5,
    "influence_weight": 3.0
  },
  "cfo_analyst": {
    "activity_level": 0.5,
    "posts_per_hour": 0.4,
    "comments_per_hour": 0.6,
    "active_hours": [9, 10, 11, 14, 15, 16, 19, 20, 21],
    "response_delay_min": 30,
    "response_delay_max": 120,
    "sentiment_bias": 0.4,
    "influence_weight": 2.0
  },
  "investigator": {
    "activity_level": 0.5,
    "posts_per_hour": 0.3,
    "comments_per_hour": 0.5,
    "active_hours": [9, 10, 11, 14, 15, 16, 19, 20, 21],
    "response_delay_min": 10,
    "response_delay_max": 45,
    "sentiment_bias": -0.2,
    "influence_weight": 1.8
  },
  "thief_criminal": {
    "activity_level": 0.3,
    "posts_per_hour": 0.1,
    "comments_per_hour": 0.2,
    "active_hours": [14, 15, 16, 20, 21, 22, 23],
    "response_delay_min": 120,
    "response_delay_max": 480,
    "sentiment_bias": -0.7,
    "influence_weight": 0.9
  },
  "housekeeper_insider": {
    "activity_level": 0.3,
    "posts_per_hour": 0.1,
    "comments_per_hour": 0.2,
    "active_hours": [7, 8, 9, 10, 11, 17, 18, 19],
    "response_delay_min": 60,
    "response_delay_max": 240,
    "sentiment_bias": -0.1,
    "influence_weight": 1.5
  },
  "activist": {
    "activity_level": 0.7,
    "posts_per_hour": 0.4,
    "comments_per_hour": 0.6,
    "active_hours": [8, 9, 12, 13, 18, 19, 20, 21, 22],
    "response_delay_min": 3,
    "response_delay_max": 25,
    "sentiment_bias": 0.4,
    "influence_weight": 1.6
  },
  "social_media_manager": {
    "activity_level": 0.8,
    "posts_per_hour": 1.0,
    "comments_per_hour": 2.0,
    "active_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
    "response_delay_min": 2,
    "response_delay_max": 15,
    "sentiment_bias": 0.5,
    "influence_weight": 1.2
  },
  "priest_mediator": {
    "activity_level": 0.2,
    "posts_per_hour": 0.1,
    "comments_per_hour": 0.1,
    "active_hours": [8, 9, 10, 11, 17, 18, 19],
    "response_delay_min": 120,
    "response_delay_max": 480,
    "sentiment_bias": 0.3,
    "influence_weight": 1.8
  },
  "sponsor_counselor": {
    "activity_level": 0.3,
    "posts_per_hour": 0.1,
    "comments_per_hour": 0.3,
    "active_hours": [9, 10, 11, 18, 19, 20],
    "response_delay_min": 30,
    "response_delay_max": 120,
    "sentiment_bias": 0.3,
    "influence_weight": 1.0
  },
  "architect_professional": {
    "activity_level": 0.4,
    "posts_per_hour": 0.2,
    "comments_per_hour": 0.4,
    "active_hours": [9, 10, 11, 14, 15, 16, 19, 20],
    "response_delay_min": 30,
    "response_delay_max": 120,
    "sentiment_bias": 0.0,
    "influence_weight": 1.4
  },
  "default": {
    "activity_level": 0.4,
    "posts_per_hour": 0.2,
    "comments_per_hour": 0.4,
    "active_hours": [9, 10, 11, 14, 15, 16, 19, 20, 21],
    "response_delay_min": 20,
    "response_delay_max": 90,
    "sentiment_bias": 0.0,
    "influence_weight": 1.0
  }
}
```

Save to: `scripts/mirofish-prep/templates/character_archetypes.json`

- [ ] **Step 2: Write the config generator**

```python
#!/usr/bin/env python3
"""
MiroFish Prep — Simulation Config Generator
Generates simulation_config.json from character_cast.json.
Includes mandatory cost controls (message_window_size, token_limit).
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ARCHETYPES_PATH = SCRIPT_DIR / 'templates' / 'character_archetypes.json'


def load_archetypes() -> dict:
    return json.loads(ARCHETYPES_PATH.read_text())


def match_archetype(role: str, archetypes: dict) -> dict:
    """Match a character role to a behavioral archetype."""
    role_lower = role.lower()

    keyword_map = {
        'journalist': 'journalist',
        'reporter': 'journalist',
        'anchor': 'journalist',
        'ceo': 'ceo_executive',
        'president': 'ceo_executive',
        'executive': 'ceo_executive',
        'director': 'operations_director',
        'operations': 'operations_director',
        'manager': 'operations_director',
        'artist': 'artist_creative',
        'creative': 'artist_creative',
        'musician': 'artist_creative',
        'painter': 'artist_creative',
        'recovery': 'artist_creative',
        'cartel': 'cartel_patriarch',
        'patriarch': 'cartel_patriarch',
        'don': 'cartel_patriarch',
        'kingpin': 'cartel_patriarch',
        'cfo': 'cfo_analyst',
        'analyst': 'cfo_analyst',
        'accountant': 'cfo_analyst',
        'financial': 'cfo_analyst',
        'investigat': 'investigator',
        'detective': 'investigator',
        'son': 'investigator',
        'thief': 'thief_criminal',
        'criminal': 'thief_criminal',
        'burglar': 'thief_criminal',
        'housekeeper': 'housekeeper_insider',
        'maid': 'housekeeper_insider',
        'servant': 'housekeeper_insider',
        'assistant': 'housekeeper_insider',
        'activist': 'activist',
        'environmental': 'activist',
        'protest': 'activist',
        'social media': 'social_media_manager',
        'media manager': 'social_media_manager',
        'pr ': 'social_media_manager',
        'priest': 'priest_mediator',
        'padre': 'priest_mediator',
        'father': 'priest_mediator',
        'chaplain': 'priest_mediator',
        'sponsor': 'sponsor_counselor',
        'counselor': 'sponsor_counselor',
        'therapist': 'sponsor_counselor',
        'architect': 'architect_professional',
        'engineer': 'architect_professional',
    }

    for keyword, archetype_key in keyword_map.items():
        if keyword in role_lower:
            return archetypes.get(archetype_key, archetypes['default'])

    return archetypes['default']


def generate_config(
    cast_path: str,
    reality_seed: str = "",
    duration_hours: int = 168,
    language: str = "es",
    llm_model: str = "claude-sonnet-4-6",
    llm_base_url: str = "http://172.17.0.1:4000/v1",
) -> dict:
    """Generate a complete simulation_config.json."""
    cast_data = json.loads(Path(cast_path).read_text())
    archetypes = load_archetypes()
    agents = cast_data.get('mandatory_agents', [])

    sim_id = f"sim_{uuid.uuid4().hex[:12]}"
    proj_id = f"proj_{uuid.uuid4().hex[:12]}"

    # Build agent configs
    agent_configs = []
    for i, agent in enumerate(agents):
        archetype = match_archetype(agent.get('role', ''), archetypes)

        # Allow cast overrides on any archetype field
        config = {
            'agent_id': i,
            'entity_uuid': str(uuid.uuid4()),
            'entity_name': agent['name'],
            'entity_type': 'Person',
            'activity_level': agent.get('activity_level', archetype['activity_level']),
            'posts_per_hour': agent.get('posts_per_hour', archetype['posts_per_hour']),
            'comments_per_hour': agent.get('comments_per_hour', archetype['comments_per_hour']),
            'active_hours': agent.get('active_hours', archetype['active_hours']),
            'response_delay_min': agent.get('response_delay_min', archetype['response_delay_min']),
            'response_delay_max': agent.get('response_delay_max', archetype['response_delay_max']),
            'sentiment_bias': agent.get('sentiment_bias', archetype['sentiment_bias']),
            'stance': agent.get('stance', 'neutral'),
            'influence_weight': agent.get('influence_weight', archetype['influence_weight']),
        }
        agent_configs.append(config)

    config = {
        'simulation_id': sim_id,
        'project_id': proj_id,
        'graph_id': f"mirofish_{uuid.uuid4().hex[:16]}",
        'simulation_requirement': reality_seed,
        'time_config': {
            'total_simulation_hours': duration_hours,
            'minutes_per_round': 60,
            'agents_per_hour_min': max(3, len(agents) // 4),
            'agents_per_hour_max': min(18, len(agents)),
            'peak_hours': [20, 21, 22, 23],
            'peak_activity_multiplier': 1.5,
            'off_peak_hours': [0, 1, 2, 3, 4, 5],
            'off_peak_activity_multiplier': 0.05,
            'morning_hours': [6, 7, 8],
            'morning_activity_multiplier': 0.4,
            'work_hours': [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
            'work_activity_multiplier': 0.7,
        },
        'agent_configs': agent_configs,
        'event_config': {
            'initial_posts': [],
            'scheduled_events': [],
            'hot_topics': [],
            'narrative_direction': '',
        },
        'twitter_config': {
            'platform': 'twitter',
            'recency_weight': 0.4,
            'popularity_weight': 0.3,
            'relevance_weight': 0.3,
            'viral_threshold': 10,
            'echo_chamber_strength': 0.5,
        },
        'reddit_config': {
            'platform': 'reddit',
            'recency_weight': 0.3,
            'popularity_weight': 0.4,
            'relevance_weight': 0.3,
            'viral_threshold': 15,
            'echo_chamber_strength': 0.6,
        },
        'llm_model': llm_model,
        'llm_base_url': llm_base_url,
        'language': language,
        'cost_controls': {
            'message_window_size': 50,
            'token_limit': 150000,
            'max_cost_per_round_usd': 0.50,
            'alert_cost_per_call_usd': 1.00,
        },
        'generated_at': datetime.now().isoformat(),
        'generated_by': 'mirofish-prep skill',
    }

    return config


def generate_test_config(full_config: dict, test_rounds: int = 10) -> dict:
    """Generate a minimal test config from a full config."""
    test = json.loads(json.dumps(full_config))  # deep copy
    test['simulation_id'] = f"test_{uuid.uuid4().hex[:12]}"
    test['time_config']['total_simulation_hours'] = test_rounds
    return test


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_config.py <character_cast.json> [--duration 168] [--language es]")
        sys.exit(1)

    cast_path = sys.argv[1]
    duration = 168
    language = "es"

    for i, arg in enumerate(sys.argv):
        if arg == '--duration' and i + 1 < len(sys.argv):
            duration = int(sys.argv[i + 1])
        if arg == '--language' and i + 1 < len(sys.argv):
            language = sys.argv[i + 1]

    config = generate_config(cast_path, duration_hours=duration, language=language)
    print(json.dumps(config, indent=2, ensure_ascii=False))
```

- [ ] **Step 3: Commit**

```bash
git add scripts/mirofish-prep/generate_config.py scripts/mirofish-prep/templates/character_archetypes.json
git commit -m "feat: add config generator with role archetypes and cost controls"
```

---

### Task 4: Create the blocked entities and validation rules reference files

**Files:**
- Create: `scripts/mirofish-prep/reference/blocked_entity_patterns.json`
- Create: `scripts/mirofish-prep/reference/validation_rules.json`
- Create: `scripts/mirofish-prep/templates/upload_checklist.md`

- [ ] **Step 1: Write blocked_entity_patterns.json**

```json
{
  "_description": "Entity names and patterns that must NEVER become simulation agents. Derived from Oro Verde S1 post-mortem where 19 of 27 agents were junk.",
  "generic_nouns": [
    "senators", "governors", "cartels", "journalists", "activists",
    "family", "siblings", "grandmother", "grandfather", "woman", "man",
    "boy", "girl", "child", "teenager", "people", "citizens", "workers",
    "employees", "lawyers", "doctors", "police", "military", "media",
    "public", "audience", "investors", "politicians", "officials",
    "neighbors", "friends", "enemies", "rivals", "allies",
    "ceos", "directors", "managers", "agents", "officers",
    "activism", "corruption", "justice", "power"
  ],
  "organization_patterns": [
    "^walmart", "^amazon", "^netflix", "^disney", "^fox", "^hbo",
    "^dea$", "^fbi$", "^cia$", "^nsa$", "^sec$",
    "^grupo\\s+", "^el\\s+universal", "^forbes$", "^bloomberg$",
    "^harvard$", "^yale$", "^stanford$",
    "criminal\\s+empire", "narco\\s+operation",
    "serrano\\s+(family|siblings|name)"
  ],
  "abstract_concepts": [
    "activism", "corruption", "justice", "power", "authority",
    "violence", "narco operation", "criminal empire", "the system"
  ],
  "descriptor_patterns": [
    "^(a|the|an)\\s+",
    "^\\d+-year-old\\b",
    "^(young|old|unnamed)\\s+"
  ]
}
```

- [ ] **Step 2: Write validation_rules.json**

```json
{
  "_description": "All preflight validation rules. Each rule was derived from a specific failure in the Oro Verde S1 simulation run.",
  "cast_rules": [
    {
      "id": "no_generic_nouns",
      "severity": "FAIL",
      "description": "No generic nouns as agent names",
      "oro_verde_example": "senators, cartels, family, woman were all created as agents"
    },
    {
      "id": "no_organizations",
      "severity": "FAIL",
      "description": "No organizations as posting agents",
      "oro_verde_example": "Walmart, criminal empire, DEA became agents"
    },
    {
      "id": "no_dead_characters",
      "severity": "FAIL",
      "description": "Dead characters must not be active posting agents",
      "oro_verde_example": "Carmen (dead) was agent #7 with highest influence_weight"
    },
    {
      "id": "no_duplicates",
      "severity": "FAIL",
      "description": "No duplicate agents for the same character",
      "oro_verde_example": "Javier (agent 9) and Javier Cordero (agent 12) were both created"
    },
    {
      "id": "all_mandatory_present",
      "severity": "FAIL",
      "description": "All mandatory characters must have individual agents",
      "oro_verde_example": "Benjamin, Karla, Isabela, Emilio, Ezequiel, Gabriela, Valeria all missing"
    }
  ],
  "config_rules": [
    {
      "id": "message_window_bounded",
      "severity": "FAIL",
      "description": "message_window_size must be set and <= 50",
      "oro_verde_example": "message_window_size=None caused 1M+ token prompts, $3/call, OOM crash"
    },
    {
      "id": "token_limit_bounded",
      "severity": "FAIL",
      "description": "token_limit must be set and <= 150000",
      "oro_verde_example": "Unbounded tokens caused exponential cost growth to $450+"
    },
    {
      "id": "no_chinese_in_config",
      "severity": "FAIL",
      "description": "No Chinese characters in config, topics, or narrative direction",
      "oro_verde_example": "Hot topics, initial posts, narrative direction all generated in Chinese"
    },
    {
      "id": "language_specified",
      "severity": "FAIL",
      "description": "Simulation language must be explicitly set",
      "oro_verde_example": "No language constraint led to Chinese/English/Spanish mix"
    }
  ],
  "document_rules": [
    {
      "id": "under_ontology_limit",
      "severity": "FAIL",
      "description": "Upload document must be under 50,000 characters",
      "oro_verde_example": "MiroFish truncates ontology analysis at 50K chars"
    },
    {
      "id": "utf8_encoding",
      "severity": "FAIL",
      "description": "Upload document must be UTF-8 encoded"
    },
    {
      "id": "supported_format",
      "severity": "FAIL",
      "description": "File format must be PDF, MD, or TXT (no DOCX)"
    }
  ]
}
```

- [ ] **Step 3: Write upload checklist template**

```markdown
# Upload Checklist — {{PROJECT_NAME}}

Generated: {{GENERATED_AT}}
Estimated cost: {{COST_ESTIMATE}}

## Pre-Upload
- [ ] MiroFish backend running on VPS (root@187.124.251.98)
- [ ] LiteLLM proxy running and connected to OpenRouter
- [ ] OpenRouter balance > {{COST_ESTIMATE}} (check at openrouter.ai/credits)
- [ ] VPS memory > 4GB free (`free -h` on VPS)

## Step 1: Graph Building
- [ ] Create new project in MiroFish UI
- [ ] Upload `upload_document.md` as the Reality Seed document
- [ ] Paste contents of `reality_seed.md` into simulation requirement field
- [ ] Click "Generate Ontology"
- [ ] **VERIFY** entity type names are English PascalCase (Person, Journalist, etc.)
      ⚠️ MiroFish's ontology prompt is Chinese — if types come back in Chinese, re-generate
- [ ] **VERIFY** entity types focus on individual character roles, not organizations
      Ideal types: Person, FamilyMember, Journalist, Activist, BusinessExecutive, CriminalOperator
      Problem types: Organization, Company, Corporation → these create junk agents
- [ ] If Organization type appears: note which characters Zep might classify as orgs.
      In Step 2, verify those didn't become posting agents.
- [ ] Click "Build Graph"
- [ ] Wait for graph building to complete (may take 2-5 minutes)

## Step 2: Profile Generation — CRITICAL CHECKPOINT
- [ ] Click "Generate Profiles"
- [ ] **STOP AND VERIFY** every name in `character_cast.json` appears as an individual agent:
{{MANDATORY_AGENT_CHECKLIST}}
- [ ] **VERIFY** no junk agents appear (Walmart, senators, family, etc.)
- [ ] **VERIFY** no dead characters are active agents
- [ ] If ANY check fails: **DO NOT PROCEED**. Re-run profile generation or manually fix.

## Step 3: Simulation
- [ ] Optional: Run 10-round test first using `test_config.json` (~$2-3)
- [ ] Monitor first 10 rounds — cost should be < $0.50/round
- [ ] Monitor VPS memory — should stay under 80% (`free -h`)
- [ ] If test passes: start full {{DURATION_HOURS}}-hour simulation
- [ ] Simulation will take approximately {{ESTIMATED_RUNTIME}} of real time
- [ ] ⚠️ **NO CHECKPOINT/RESUME**: If the simulation crashes, it CANNOT be resumed.
      Data up to the crash point is saved in action logs, but you must restart from round 0.
      Monitor actively during the first 30 rounds. If memory > 80% or cost > $0.50/round, STOP.
- [ ] Check OpenRouter dashboard periodically for cumulative cost

## Step 4: Report
- [ ] Generate report after simulation completes
- [ ] Verify report sections generated successfully

## Step 5: Post-Simulation
- [ ] Export simulation data to Character Engine:
  ```bash
  cd /Users/quantumcode/CODE/character-social
  ./scripts/sync-from-mirofish.sh
  ```
- [ ] Update character profiles in Character Engine if simulation revealed new dynamics
- [ ] Review report for narrative insights
```

Save to: `scripts/mirofish-prep/templates/upload_checklist.md`

- [ ] **Step 4: Commit**

```bash
git add scripts/mirofish-prep/reference/ scripts/mirofish-prep/templates/
git commit -m "feat: add validation rules, blocked patterns, and checklist template"
```

---

### Task 5: Create the main skill file

**Files:**
- Create: `.claude/commands/mirofish-prep.md`

This is the actual `/mirofish-prep` command. It's a detailed prompt that instructs Claude how to run the 4-phase pipeline using the helper scripts and its own reasoning.

- [ ] **Step 1: Create the .claude/commands directory**

```bash
mkdir -p "/Users/quantumcode/CODE/MIROFISH LEMON/.claude/commands"
```

- [ ] **Step 2: Write the skill file**

The skill file is the core deliverable. It must be comprehensive enough that any Claude Code session can execute the full pipeline correctly without prior context.

```markdown
---
name: mirofish-prep
description: >
  Prepare simulation materials for MiroFish. Takes creative materials
  (scripts, bibles, character breakdowns) and produces a validated,
  ready-to-upload package. 4-phase pipeline with human checkpoints.
  Use for any Lemon Studios TV/film project.
argument-hint: "[path-to-materials-or-directory]"
model: claude-sonnet-4-6
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
  - TodoWrite
  - AskUserQuestion
---

# MiroFish Prep — Simulation Material Packager

You are preparing materials for a MiroFish multi-agent narrative simulation.
The user is a Lemon Studios producer with finished creative materials (scripts,
treatments, bibles, character breakdowns). Your job is to package those materials
so MiroFish produces clean, accurate simulation agents — not the junk agents
that destroyed the $450 Oro Verde S1 run.

**CRITICAL CONTEXT — WHY THIS SKILL EXISTS:**
In the Oro Verde S1 simulation, MiroFish's profile generator created 27 agents
from uploaded documents. Only 2 were properly named individuals. The other 25
were junk: "Walmart", "senators", "Serrano siblings", "criminal empire",
"fourteen-year-old girl", "grandmother" (a dead character). Key characters
like Benjamín Serrano, Isabela Serrano, Don Ezequiel, and Emilio Vega never
got individual agents. The simulation burned ~$450 in OpenRouter credits and
crashed at round 134/168 from an OOM error caused by unbounded context windows.

This skill prevents that from ever happening again.

---

## PHASE OVERVIEW

```
PHASE 1: INGEST  → Read files, analyze, detect risks
PHASE 2: CAST    → Extract characters, approve agent list
PHASE 3: BUILD   → Generate all output files
PHASE 4: PREFLIGHT → Validate everything, estimate cost
```

Each phase ends with multiple-choice decisions. Mark recommended defaults.
Wait for user approval before proceeding to the next phase.

---

## INITIALIZATION

1. Parse the user's input for file paths, directory paths, and project description.
2. If a directory is given, find all PDF/MD/TXT files (MiroFish's accepted formats).
3. If no argument is provided, ask: "Where are your materials? Give me file paths, a directory, or describe your project."
4. Create a TodoWrite task list for the 4 phases.

---

## PHASE 1: INGEST

### Steps
1. Run the document analyzer:
   ```bash
   python3 scripts/mirofish-prep/analyze_documents.py <file1> [file2] ...
   ```
   Or with a directory:
   ```bash
   python3 scripts/mirofish-prep/analyze_documents.py --dir <directory>
   ```

2. Parse the JSON output.

3. Read each file yourself (using Read tool) to understand the content deeply.
   The Python script does surface analysis. YOU do the narrative analysis —
   understanding who the characters are, what the story is, what matters.

4. Present the INGEST report in this format:

```
INGEST COMPLETE
===============

Project: <project name from user's description>
Materials found: N files

  1. filename.ext    XX,XXX chars   TYPE
  2. filename.ext    XX,XXX chars   TYPE
  ...

Total: XXX,XXX characters across N files

DOCUMENT ANALYSIS
  Characters detected:    N named individuals
  Organizations detected: N (list them)
  Locations detected:     N
  Dead characters:        N (list them with reason)

WARNINGS
  (list any warnings from the analyzer)

ENTITY POLLUTION RISKS
  (list high/medium risks — these will become junk agents if uploaded raw)

DECISIONS
─────────

1. Which files should be uploaded to MiroFish?
   a) [x] file1.ext (XX,XXX chars)
   b) [x] file2.ext (XX,XXX chars)
   ...

2. [If total > 50K] Document strategy for the 50K ontology limit:
   a) Option A description ← RECOMMENDED
   b) Option B description
   c) Option C description

3. Simulation language:
   a) Spanish ← RECOMMENDED for Latin American projects
   b) English
   c) Mixed Spanish/English

4. Simulation length:
   a) 72 hours (3 days) — faster, cheaper, good for testing
   b) 168 hours (7 days) — full run ← RECOMMENDED
   c) 336 hours (14 days) — extended
   d) Custom: ___
```

5. Wait for user's decisions. Store choices for Phase 3.

---

## PHASE 2: CAST

### Steps
1. Using YOUR analysis of the materials (not just the Python script's entity scan),
   extract every named character. For each character, determine:
   - **Name** (full proper name, exactly as it should appear in the simulation)
   - **Role** (their function in the story)
   - **Stance** (protagonist/antagonist/opposing/neutral/supportive)
   - **Narrative weight** (PRINCIPAL: drives plot / SUPPORTING: drives subplots / MINOR: referenced only)
   - **Dead or alive** at simulation start

2. Run validation on each name mentally:
   - Is this a proper individual name? (not "the siblings", not "Walmart")
   - Is this character alive at simulation start?
   - Is there a duplicate? (same character, different name reference)

3. Present the CAST table:

```
CAST EXTRACTION
===============

Found N named characters across your materials.

PRINCIPAL CAST (appear frequently, drive plot)
┌────┬──────────────────────┬─────────────────────────┬─────────────┬───────┐
│  # │ Name                 │ Role                    │ Stance      │ Agent │
├────┼──────────────────────┼─────────────────────────┼─────────────┼───────┤
│  1 │ Character Name       │ Their role              │ stance      │  ✓    │
...
└────┴──────────────────────┴─────────────────────────┴─────────────┴───────┘

SUPPORTING CAST
(same format)

MINOR / REFERENCED ONLY
(same format, with ○ instead of ✓ for agent column)

EXCLUDED (not suitable as posting agents)
│  – │ Name                 │ Role                    │ Reason               │

REJECTED ENTITIES (found in text, blocked from becoming agents)
  ✗ Entity Name          → reason for rejection

Agent count: N mandatory + 0 minor = N agents

DECISIONS
─────────

1. Cast looks correct?
   a) Yes, proceed with this cast ← RECOMMENDED
   b) I need to add a character
   c) I need to remove/change someone

2. Include minor cast as agents?
   a) No, keep them as referenced-only ← RECOMMENDED
   b) Yes, promote all minor to agents
   c) Let me pick which minor characters get agents

3. Allow MiroFish to generate additional background agents?
   a) Yes, up to 6 extras
   b) Yes, up to 3 extras ← RECOMMENDED
   c) No, only use the mandatory cast
```

4. If user wants to add/change/remove, iterate until approved.

5. Once approved, generate `character_cast.json` and save to `sim-prep/<project-slug>/`:
   ```bash
   # Write the JSON using the Write tool — do NOT use the Python generator
   # for the cast file. YOU build it from the approved table because YOU
   # understand the characters. Use archetype matching for behavioral params:
   python3 -c "
   import json
   archetypes = json.load(open('scripts/mirofish-prep/templates/character_archetypes.json'))
   print(json.dumps(archetypes, indent=2))
   "
   ```
   Match each character's role to an archetype for behavioral parameters
   (activity_level, posts_per_hour, active_hours, etc.)

---

## PHASE 3: BUILD

### Steps
1. Generate the **upload document** (`upload_document.md`):
   - Synthesize from approved materials
   - Apply these transformations:
     a. Add a CHARACTER INDEX header listing all mandatory agents by full name
     b. Replace organization names with generic descriptions
        ("Walmart" → "a major retail buyer", "DEA" → "a federal agency")
     c. Replace group references with individual names
        ("the siblings" → "Benjamín, Karla, and Isabela")
     d. Mark dead characters explicitly: "Carmen Serrano [DECEASED]"
     e. Remove or neutralize any entity that could create a junk agent
     f. Keep total under 50,000 characters
     g. Write in English (for cleaner Zep entity extraction)

2. Generate the **reality seed** (`reality_seed.md`):
   - Write a fresh 2,000-3,000 character narrative prompt
   - Name every mandatory agent individually (never as groups)
   - Describe the world state at simulation start
   - Identify 2-3 colliding forces
   - Pose open questions for the simulation to answer
   - Specify report structure (4 thematic sections)
   - Write in English

3. Generate the **simulation config** (`simulation_config.json`):
   ```bash
   python3 scripts/mirofish-prep/generate_config.py \
     sim-prep/<project-slug>/character_cast.json \
     --duration <hours> \
     --language <lang>
   ```
   Then update it with:
   - The reality seed text as simulation_requirement
   - Initial posts (assign 6-8 to specific agents)
   - Hot topics (10-12 keywords from the materials, in ENGLISH)
   - Narrative direction (in English, for the production team)

4. Generate **event seeds** (`event_seeds.json`) if the user chose to use them:
   - Derive from script act breaks / key narrative beats
   - Assign each event a trigger hour and agent

5. Present BUILD summary with previews of each file:

```
BUILD COMPLETE
==============

OUTPUTS GENERATED
─────────────────

1. UPLOAD DOCUMENT — sim-prep/<slug>/upload_document.md (XX,XXX chars)
   Modifications applied:
     ✓ (list each transformation)

2. REALITY SEED — sim-prep/<slug>/reality_seed.md (X,XXX chars)
   Preview:
   ┌──────────────────────────────────────────────────────────────┐
   │ First 300 chars of the reality seed...                      │
   └──────────────────────────────────────────────────────────────┘

3. CHARACTER CAST — sim-prep/<slug>/character_cast.json
   N mandatory agents with full profiles

4. SIMULATION CONFIG — sim-prep/<slug>/simulation_config.json
   Duration: XXXh | Language: XX | Cost controls: ✓

5. EVENT SEEDS — sim-prep/<slug>/event_seeds.json
   N scheduled events

DECISIONS
─────────

1. Upload document looks correct?
   a) Yes ← RECOMMENDED
   b) Let me review the full text
   c) I want to change what's included

2. Reality seed captures the right focus?
   a) Yes ← RECOMMENDED
   b) I want to edit it
   c) Rewrite with different emphasis: ___

3. Event seeds?
   a) Yes, use these ← RECOMMENDED
   b) Adjust timing/content
   c) No scheduled events
```

---

## PHASE 4: PREFLIGHT

### Steps
1. Run the cast validator:
   ```bash
   python3 scripts/mirofish-prep/validate_cast.py sim-prep/<slug>/character_cast.json
   ```

2. Run additional validation checks yourself:
   - Upload document under 50K chars
   - Reality seed under 5K chars
   - simulation_config.json has message_window_size=50 and token_limit=150000
   - No Chinese text anywhere in config, topics, or narrative direction
   - Language field is set
   - All mandatory agents in config match character_cast.json
   - No first-name-only agents (except characters known by single name like Reynaldo)
   - No agent names that look like corruptions of known character names
     (e.g., "Nesto Vega" instead of "Emilio Vega" — the profile generator hallucinated this)
   - Upload document has been stripped of organization names that Zep would extract
   - Upload document starts with a CHARACTER INDEX listing all mandatory agents by full name
   - No agent has the same first name as another agent (catches the "Javier" + "Javier Cordero" duplication)
   - Dead characters (Carmen, Ernesto) appear ONLY in excluded_entities, never in mandatory_agents

3. Calculate cost estimate:
   - Count agents × average activity × rounds = estimated API calls
   - Estimated tokens per call: ~4,500 (4K prompt + 500 completion, bounded)
   - Cost per call: use Sonnet pricing (~$0.003 per 1K input + $0.015 per 1K output)
   - Add report generation cost (~$5-10)
   - Compare to Oro Verde S1 ($450)

4. Generate `preflight_report.md` and `upload_checklist.md`:
   - Read the checklist template:
     ```bash
     cat scripts/mirofish-prep/templates/upload_checklist.md
     ```
   - Fill in the template variables
   - Write both files to sim-prep/<slug>/

5. Optionally generate `test_config.json` (10-round mini test):
   ```bash
   python3 -c "
   import json, sys
   sys.path.insert(0, 'scripts/mirofish-prep')
   from generate_config import generate_test_config
   config = json.load(open('sim-prep/<slug>/simulation_config.json'))
   test = generate_test_config(config, test_rounds=10)
   print(json.dumps(test, indent=2))
   "
   ```

6. Present the PREFLIGHT report:

```
PREFLIGHT CHECK
===============

CAST VALIDATION
  ✅/❌ Each check result

DOCUMENT VALIDATION
  ✅/❌ Each check result

CONFIG VALIDATION
  ✅/❌ Each check result

COST ESTIMATE
  ┌──────────────────────────────────────────────────┐
  │ (itemized estimate)                              │
  │ vs. Oro Verde S1: ~$450 (XX% reduction)          │
  └──────────────────────────────────────────────────┘

PREFLIGHT RESULT: ✅ ALL CLEAR / ⚠️ WARNINGS / ❌ BLOCKED

DECISIONS
─────────

1. Ready to prep for upload?
   a) Yes, generate final output directory ← RECOMMENDED
   b) Go back and adjust something

2. Generate a mini test config?
   a) Yes, 10-round test for ~$2-3 ← RECOMMENDED
   b) No, straight to full run
```

7. On final confirmation, display the output directory listing and the upload checklist.

---

## RULES

1. **Never skip a phase.** Even if the user says "just generate everything", run all 4 phases with checkpoints.
2. **Never create a group agent.** If a character is "the Serrano siblings", create Benjamín, Karla, and Isabela as three separate agents.
3. **Never create an organization agent.** Walmart is not a character. DEA is not a character.
4. **Never create a dead character as an active agent.** Carmen is dead. She goes in excluded_entities.
5. **Always set message_window_size=50 and token_limit=150000.** These are non-negotiable.
6. **Always write config/topics/narrative in English.** Never in Chinese.
7. **Always wait for user approval between phases.** Never auto-proceed.
8. **The upload document is curated, not raw.** Never upload the user's original files as-is.
9. **The reality seed names individuals, never groups.** Write "Benjamín, Karla, and Isabela" not "the Serrano siblings".
10. **All output goes to sim-prep/<project-slug>/.** Create the directory if it doesn't exist.
11. **Flag the ontology prompt language issue.** MiroFish's ONTOLOGY_SYSTEM_PROMPT is 100% Chinese. The upload checklist must warn the user to verify entity type names come back in English PascalCase, not Chinese. If they don't, the ontology generation must be re-run.
12. **Recommend excluding Organization entity type.** When reviewing ontology in MiroFish Step 1, the user should request that Organization-type entities be excluded from agent generation — Zep will still create org nodes, but they should not become posting agents. Add this to the upload checklist as a manual verification step.
13. **Warn about Zep's black-box entity extraction.** The upload document is the ONLY lever we have to control what Zep creates. Every organization name, group noun, or abstract concept left in the upload doc WILL become a Zep entity. The BUILD phase's document curation is the most important step in the entire pipeline.
14. **Detect name hallucinations.** If the cast validator finds an agent name that looks like a corruption of a known character name (e.g., "Nesto Vega" instead of "Ernesto Vega" or "Emilio Vega"), flag it as a warning. The LLM profile generator can hallucinate partial names.
15. **Require full names where applicable.** Agent names should be full proper names (first + last), not first-name-only. "Karla" should be "Karla Serrano". "Javier" should be "Javier Cordero". Exception: characters known by single name (e.g., "Reynaldo" the thief).
16. **Include checkpoint/resume guidance.** The upload checklist should note that MiroFish currently has no checkpoint/resume capability. If the simulation crashes, data up to the crash point is in the action logs but the simulation cannot be resumed. The user should monitor VPS memory and cost actively during the first 30 rounds.
```

Save to: `.claude/commands/mirofish-prep.md`

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/mirofish-prep.md
git commit -m "feat: add /mirofish-prep Claude Code skill — 4-phase simulation packager"
```

---

### Task 6: End-to-end test with Oro Verde V8 materials

**Files:**
- Output: `sim-prep/oro-verde/` (all generated files)

- [ ] **Step 1: Invoke the skill**

```
/mirofish-prep

Materials are in "Billy Agents/Billy Docs for Mirofish/":
- OV MIROFISH REALITY SEED V8.md (show bible)
- PILOT SINOPSIS OV V8.txt (pilot synopsis)
- JEN_GRISANTI_ORO_VERDE_V8_INTERROGATION.md (character interrogation)
- ORO VERDE 101 V8.1 09_01_26 CLEAN TXT.txt (pilot script)
- V8 MF Seed Prompt.md (previous simulation requirement)

Oro Verde — premium narco-family drama. Carmen Serrano is dead.
Three siblings are now the public face of a cartel operation.
Journalist and victim's son are investigating. This is the same
project from the failed $450 S1 run — rerunning with proper prep.
```

- [ ] **Step 2: Walk through all 4 phases**

Verify each phase produces the expected output:
- INGEST: File inventory, entity scan, pollution risks flagged (Walmart, DEA, etc.)
- CAST: 14 individually named characters, Carmen/Ernesto excluded, orgs rejected
- BUILD: Upload document under 50K, reality seed ~2,500 chars, config with cost controls
- PREFLIGHT: All checks pass, cost estimate $30-50

- [ ] **Step 3: Verify output directory**

```bash
ls -la sim-prep/oro-verde/
```

Expected files:
- upload_document.md (< 50,000 chars)
- reality_seed.md (2,000-3,000 chars)
- character_cast.json (14 agents with behavioral params)
- simulation_config.json (with message_window_size=50, token_limit=150000)
- event_seeds.json
- preflight_report.md
- upload_checklist.md
- test_config.json (10-round mini test)

- [ ] **Step 4: Validate the cast catches all Oro Verde S1 failures**

```bash
# Run the validator against the generated cast
python3 scripts/mirofish-prep/validate_cast.py sim-prep/oro-verde/character_cast.json
```

Expected: PASS with all 14 characters present, no junk agents.

```bash
# Verify the config has cost controls
python3 -c "
import json
config = json.load(open('sim-prep/oro-verde/simulation_config.json'))
assert config['cost_controls']['message_window_size'] == 50
assert config['cost_controls']['token_limit'] == 150000
assert 'language' in config
print('Config validation: PASS')
print(f'Agents: {len(config[\"agent_configs\"])}')
print(f'Duration: {config[\"time_config\"][\"total_simulation_hours\"]}h')
print(f'Language: {config[\"language\"]}')
"
```

- [ ] **Step 5: Commit the test output**

```bash
git add sim-prep/oro-verde/
git commit -m "test: oro verde prep output — validates mirofish-prep skill end-to-end"
```

---

## Execution Notes

- **Tasks 1-4** build the infrastructure (Python scripts + reference files + templates)
- **Task 5** builds the actual skill file — this is the core deliverable
- **Task 6** is the integration test using the real Oro Verde materials
- Tasks 1-4 can be done in parallel since they're independent scripts
- Task 5 depends on Tasks 1-4 (the skill references the scripts)
- Task 6 depends on Task 5 (tests the skill end-to-end)

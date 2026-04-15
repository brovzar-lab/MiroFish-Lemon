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

        first_name = name.split()[0] if name else ''
        for j, other in enumerate(names):
            if i != j and first_name and other.startswith(first_name) and name != other:
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
    source_characters = cast_data.get('_source_character_names', [])
    if source_characters:
        source_lower = {n.lower() for n in source_characters}
        for agent in agents:
            agent_name = agent.get('name', '').lower()
            for source_name in source_lower:
                if agent_name != source_name:
                    a_parts = set(agent_name.split())
                    s_parts = set(source_name.split())
                    overlap = a_parts & s_parts
                    diff = a_parts.symmetric_difference(s_parts)
                    if overlap and diff:
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

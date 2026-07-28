"""
Cast Policy — makes the simulation engine respect the prep studio's approved cast.

Until this module existed, the cast a producer approved in MIROFISH PREP was
written to disk and never read again: agents were re-derived from Zep entity
extraction over the upload document, which is how a $450 run ended up with
agents like `walmart_999` and a dead grandmother while the three protagonists
never posted once.

Applied between entity filtering and profile generation:
1. Entities matching `excluded_entities` (e.g. dead characters) are dropped.
2. Entities matching the generic-noun / organization blocklist are dropped
   (patterns loaded from scripts/mirofish-prep/reference/blocked_entity_patterns.json,
   the post-mortem's block list).
3. Every `mandatory_agents` entry is guaranteed a profile: matched to a Zep
   entity when one exists, synthesized from the cast entry when not.
4. Non-cast survivors are capped at `max_additional_agents`.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger('mirofish.cast_policy')

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BLOCKED_PATTERNS_PATH = (
    _REPO_ROOT / "scripts" / "mirofish-prep" / "reference" / "blocked_entity_patterns.json"
)

# Minimal builtin fallback if the reference file is missing
_FALLBACK_BLOCKED_NOUNS = [
    "family", "siblings", "grandmother", "grandfather", "senators", "governors",
    "cartels", "journalists", "activists", "officials", "ceos", "executives",
    "investors", "employees", "workers", "citizens", "people", "public",
    "community", "media", "press", "government", "police", "authorities",
]
_FALLBACK_BLOCKED_PATTERNS = [
    r"^(the\s+)?\w+\s+(family|siblings|name)$",
    r"^(criminal|narco|rival)\s+\w+$",
    r"^\w+\s+(empire|operation|organization|corporation)$",
]


def _load_blocklist() -> Dict[str, List[str]]:
    if _BLOCKED_PATTERNS_PATH.exists():
        try:
            data = json.loads(_BLOCKED_PATTERNS_PATH.read_text(encoding="utf-8"))
            nouns = list(data.get("generic_nouns", [])) + list(data.get("abstract_concepts", []))
            patterns = list(data.get("organization_patterns", [])) + list(data.get("descriptor_patterns", []))
            if nouns or patterns:
                return {"nouns": [n.lower() for n in nouns], "patterns": patterns}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load blocked_entity_patterns.json: {e}")
    return {"nouns": _FALLBACK_BLOCKED_NOUNS, "patterns": _FALLBACK_BLOCKED_PATTERNS}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _names_match(a: str, b: str) -> bool:
    """Match 'Benjamín' to 'Benjamín Serrano' and vice versa (whole-word containment)."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    return bool(re.search(rf"(^|\s){re.escape(shorter)}($|\s)", longer))


def is_blocked_entity(name: str, blocklist: Optional[Dict[str, List[str]]] = None) -> bool:
    bl = blocklist or _load_blocklist()
    n = _norm(name)
    if not n:
        return True
    if n in bl["nouns"]:
        return True
    stripped = re.sub(r"^the\s+", "", n)
    if stripped in bl["nouns"]:
        return True
    for pattern in bl["patterns"]:
        try:
            if re.match(pattern, n, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


@dataclass
class CastPolicyResult:
    entities: List[Any]                 # final entity list for profile generation
    matched_cast: List[str] = field(default_factory=list)
    injected_cast: List[str] = field(default_factory=list)
    dropped_excluded: List[str] = field(default_factory=list)
    dropped_blocked: List[str] = field(default_factory=list)
    dropped_over_cap: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"cast policy: {len(self.matched_cast)} cast matched, "
            f"{len(self.injected_cast)} cast injected, "
            f"{len(self.dropped_excluded)} excluded, "
            f"{len(self.dropped_blocked)} generic blocked, "
            f"{len(self.dropped_over_cap)} over cap"
        )


def _make_cast_entity(agent: Dict[str, Any], index: int):
    """Synthesize an EntityNode for a mandatory cast member the graph missed."""
    from .zep_entity_reader import EntityNode
    role = agent.get("role", "")
    stance = agent.get("stance", "")
    desc_bits = [b for b in [
        role,
        f"Narrative stance: {stance}." if stance else "",
        f"Enneagram {agent['enneagram']}." if agent.get("enneagram") else "",
        f"MBTI {agent['mbti']}." if agent.get("mbti") else "",
    ] if b]
    return EntityNode(
        uuid=f"cast_{index}_{re.sub(r'[^a-z0-9]+', '_', _norm(agent.get('name', '')))}",
        name=agent.get("name", f"Cast member {index}"),
        labels=["Entity", "Person"],
        summary=" ".join(desc_bits) or f"Approved cast member: {agent.get('name')}",
        attributes={"_from_cast": True, **{
            k: agent[k] for k in ("archetype", "stance", "activity_level")
            if k in agent
        }},
    )


def apply_cast_policy(entities: List[Any], cast: Optional[Dict[str, Any]]) -> CastPolicyResult:
    """
    Filter/augment the entity list so it honors the approved cast.

    `entities` are zep_entity_reader.EntityNode objects (anything with
    .name works for filtering). `cast` is the character_cast.json dict;
    when None or empty, entities pass through unchanged.
    """
    if not cast or not cast.get("mandatory_agents"):
        return CastPolicyResult(entities=list(entities))

    mandatory = cast.get("mandatory_agents", [])
    excluded_names = [e.get("name", "") for e in cast.get("excluded_entities", [])]
    max_additional = cast.get("max_additional_agents")
    blocklist = _load_blocklist()

    result = CastPolicyResult(entities=[])
    cast_hits: Dict[int, Any] = {}
    additional: List[Any] = []

    for ent in entities:
        name = getattr(ent, "name", "")
        if any(_names_match(name, ex) for ex in excluded_names):
            result.dropped_excluded.append(name)
            continue
        if is_blocked_entity(name, blocklist):
            result.dropped_blocked.append(name)
            continue
        matched_idx = next(
            (i for i, agent in enumerate(mandatory)
             if _names_match(name, agent.get("name", ""))),
            None,
        )
        if matched_idx is not None and matched_idx not in cast_hits:
            cast_hits[matched_idx] = ent
        else:
            additional.append(ent)

    # Guaranteed cast, in cast order: matched entity or synthesized stand-in
    for i, agent in enumerate(mandatory):
        if i in cast_hits:
            result.entities.append(cast_hits[i])
            result.matched_cast.append(agent.get("name", ""))
        else:
            result.entities.append(_make_cast_entity(agent, i))
            result.injected_cast.append(agent.get("name", ""))

    # Cap the extras (keep the most connected ones)
    if isinstance(max_additional, int) and max_additional >= 0:
        additional.sort(key=lambda e: len(getattr(e, "related_edges", []) or []), reverse=True)
        kept, over = additional[:max_additional], additional[max_additional:]
        result.entities.extend(kept)
        result.dropped_over_cap = [getattr(e, "name", "") for e in over]
    else:
        result.entities.extend(additional)

    logger.info(result.summary())
    return result

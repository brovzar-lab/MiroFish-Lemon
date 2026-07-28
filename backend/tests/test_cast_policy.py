"""Tests for cast policy — the engine must respect the approved cast."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cast_policy import apply_cast_policy, is_blocked_entity
from app.services.zep_entity_reader import EntityNode


def ent(name, edges=0):
    return EntityNode(
        uuid=f"u_{name}", name=name, labels=["Entity", "Person"],
        summary=f"{name} summary", attributes={},
        related_edges=[{"e": i} for i in range(edges)],
    )


CAST = {
    "mandatory_agents": [
        {"name": "Benjamín Serrano", "role": "CEO", "stance": "protagonist", "enneagram": "3w2"},
        {"name": "Karla Serrano", "role": "COO", "stance": "protagonist"},
        {"name": "Don Ezequiel", "role": "Cartel patriarch", "stance": "antagonist"},
    ],
    "excluded_entities": [
        {"name": "Carmen Serrano", "reason": "deceased"},
    ],
    "max_additional_agents": 2,
}


def test_no_cast_passes_through():
    entities = [ent("Anyone"), ent("walmart")]
    result = apply_cast_policy(entities, None)
    assert len(result.entities) == 2


def test_excluded_dead_character_dropped():
    result = apply_cast_policy([ent("Carmen Serrano"), ent("Benjamín Serrano")], CAST)
    assert "Carmen Serrano" in result.dropped_excluded
    assert all(e.name != "Carmen Serrano" for e in result.entities)


def test_generic_junk_agents_dropped():
    junk = [ent("Walmart"), ent("senators"), ent("criminal empire"),
            ent("the Serrano family"), ent("grandmother")]
    result = apply_cast_policy(junk + [ent("Benjamín Serrano")], CAST)
    dropped = set(result.dropped_blocked)
    assert {"Walmart", "senators", "criminal empire", "grandmother"} & dropped == \
        {"Walmart", "senators", "criminal empire", "grandmother"}
    assert all(e.name not in dropped for e in result.entities)


def test_every_mandatory_agent_guaranteed():
    # Graph only found Benjamín. Karla and Ezequiel must be injected.
    result = apply_cast_policy([ent("Benjamín Serrano")], CAST)
    names = [e.name for e in result.entities]
    assert "Benjamín Serrano" in result.matched_cast
    assert "Karla Serrano" in result.injected_cast
    assert "Don Ezequiel" in result.injected_cast
    assert set(names) >= {"Benjamín Serrano", "Karla Serrano", "Don Ezequiel"}


def test_injected_entity_carries_cast_context():
    result = apply_cast_policy([], CAST)
    benja = next(e for e in result.entities if e.name == "Benjamín Serrano")
    assert "CEO" in benja.summary
    assert "protagonist" in benja.summary
    assert benja.attributes.get("_from_cast") is True


def test_partial_name_matches_cast():
    # Zep often extracts short forms
    result = apply_cast_policy([ent("Benjamín"), ent("Karla Serrano")], CAST)
    assert "Benjamín Serrano" in result.matched_cast
    assert "Karla Serrano" in result.matched_cast
    assert len(result.injected_cast) == 1  # only Ezequiel synthesized


def test_additional_agents_capped_by_connectivity():
    extras = [ent("Lucía Suárez", edges=9), ent("Javier Cordero", edges=5),
              ent("Random Guy", edges=1)]
    result = apply_cast_policy(extras + [ent("Benjamín Serrano")], CAST)
    names = [e.name for e in result.entities]
    assert "Lucía Suárez" in names and "Javier Cordero" in names
    assert "Random Guy" in result.dropped_over_cap


def test_blocklist_uses_postmortem_reference():
    # These come from the reference JSON (real S1 failure modes)
    assert is_blocked_entity("cartels")
    assert is_blocked_entity("Serrano siblings")
    assert not is_blocked_entity("Ingrid Cervantes")

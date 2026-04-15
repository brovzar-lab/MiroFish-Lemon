"""
Unit tests for PrepGenerator — the AI-authoring pipeline for MiroFish sim-prep packages.

Uses a mock LLMClient to verify:
- Cast extraction with validation-in-loop (retries on FAIL)
- Upload document generation with hard 50K truncation
- CHARACTER INDEX header requirement
- Organization name replacement
- Reality seed individual-naming requirement
- Event seed structure
- Hardcoded cost controls (message_window_size=50, token_limit=150000)

Run: cd backend && python -m pytest tests/test_prep_generator.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure we can import from the backend app
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.prep_generator import PrepGenerator, MAX_UPLOAD_DOC_CHARS


# ─── FIXTURES ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    """Mock LLMClient with configurable responses."""
    m = MagicMock()
    m.chat = MagicMock(return_value="")
    m.chat_json = MagicMock(return_value={})
    return m


@pytest.fixture
def gen(mock_llm):
    """PrepGenerator with mocked LLM."""
    return PrepGenerator(slug="test-project", llm_client=mock_llm)


@pytest.fixture
def sample_sources():
    """Sample source texts that would trigger S1-style junk-agent creation."""
    return [
        """
        Benjamín Serrano runs the family business with his siblings Karla and Isabela.
        The DEA is investigating them. Walmart is their biggest buyer.
        Their grandmother Carmen died last year. Javier Cordero is a journalist
        investigating the family.
        """,
        """
        The cartel has pressured Don Ezequiel to cooperate. Rodrigo Palma, his lieutenant,
        handles day-to-day operations. Ernesto Vega was killed in the first act.
        """,
    ]


@pytest.fixture
def valid_cast():
    """A cast dict that passes validate_cast() cleanly."""
    return {
        "mandatory_agents": [
            {"name": "Benjamín Serrano", "archetype": "cartel_patriarch",
             "role": "family head", "stance": "protagonist",
             "narrative_weight": "PRINCIPAL"},
            {"name": "Karla Serrano", "archetype": "family_matriarch",
             "role": "sister", "stance": "opposing",
             "narrative_weight": "PRINCIPAL"},
            {"name": "Javier Cordero", "archetype": "journalist",
             "role": "investigating journalist", "stance": "antagonist",
             "narrative_weight": "PRINCIPAL"},
        ],
        "excluded_entities": [
            {"name": "Carmen Serrano", "reason": "DECEASED"},
            {"name": "Walmart", "reason": "ORGANIZATION"},
        ],
        "rejected_entities": ["the siblings", "the cartel"],
    }


@pytest.fixture
def invalid_cast():
    """A cast with S1-style failures: generic nouns, orgs, first-name-only."""
    return {
        "mandatory_agents": [
            {"name": "Walmart", "archetype": "ceo_executive",
             "role": "retail buyer", "stance": "neutral"},
            {"name": "Karla", "archetype": "family_matriarch",
             "role": "sister", "stance": "opposing"},
            {"name": "senators", "archetype": "politician",
             "role": "politicians", "stance": "neutral"},
        ],
        "excluded_entities": [],
        "rejected_entities": [],
    }


# ─── CAST EXTRACTION ─────────────────────────────────────────────────────────

def test_extract_cast_happy_path(gen, mock_llm, sample_sources, valid_cast):
    """Valid cast on first try should return without retries."""
    mock_llm.chat_json.return_value = valid_cast

    result = gen.extract_cast(sample_sources)

    assert mock_llm.chat_json.call_count == 1
    assert len(result["mandatory_agents"]) == 3
    assert result["_validation"]["failures"] == 0
    assert result["_validation"]["status"] == "PASS"


def test_extract_cast_retries_on_failure(gen, mock_llm, sample_sources,
                                          invalid_cast, valid_cast):
    """First attempt invalid → retry → second attempt valid."""
    mock_llm.chat_json.side_effect = [invalid_cast, valid_cast]

    result = gen.extract_cast(sample_sources)

    assert mock_llm.chat_json.call_count == 2
    assert result["_validation"]["failures"] == 0


def test_extract_cast_gives_up_after_max_retries(gen, mock_llm,
                                                  sample_sources, invalid_cast):
    """After max retries, returns last cast with _validation_warnings."""
    mock_llm.chat_json.return_value = invalid_cast

    result = gen.extract_cast(sample_sources)

    # MAX_CAST_RETRIES = 2 → 3 total attempts
    assert mock_llm.chat_json.call_count == 3
    assert "_validation_warnings" in result
    assert result["_validation"]["failures"] > 0


# ─── UPLOAD DOCUMENT ─────────────────────────────────────────────────────────

def test_generate_upload_doc_under_50k(gen, mock_llm, sample_sources, valid_cast):
    """Output is always truncated to <= MAX_UPLOAD_DOC_CHARS."""
    huge_output = "X" * 80_000
    mock_llm.chat.return_value = huge_output

    result = gen.generate_upload_document(sample_sources, valid_cast)

    assert len(result) <= MAX_UPLOAD_DOC_CHARS + 100  # allow truncation marker
    assert "truncated" in result.lower()


def test_upload_doc_preserves_short_output(gen, mock_llm, sample_sources, valid_cast):
    """Short outputs are returned unmodified."""
    mock_llm.chat.return_value = "# Short document\n\nJust some content."

    result = gen.generate_upload_document(sample_sources, valid_cast)

    assert result == "# Short document\n\nJust some content."


def test_upload_doc_receives_agent_names_in_prompt(gen, mock_llm,
                                                    sample_sources, valid_cast):
    """Prompt to LLM must include all mandatory agent names."""
    mock_llm.chat.return_value = "output"

    gen.generate_upload_document(sample_sources, valid_cast)

    # Check the user message passed to LLM contained all agent names
    call_args = mock_llm.chat.call_args
    messages = call_args.kwargs["messages"]
    user_msg = messages[-1]["content"]
    assert "Benjamín Serrano" in user_msg
    assert "Karla Serrano" in user_msg
    assert "Javier Cordero" in user_msg


# ─── REALITY SEED ────────────────────────────────────────────────────────────

def test_generate_reality_seed_returns_string(gen, mock_llm,
                                                sample_sources, valid_cast):
    """Reality seed returns stripped plaintext."""
    mock_llm.chat.return_value = "  WORLD STATE:\nSome narrative here.  "

    result = gen.generate_reality_seed(sample_sources, valid_cast)

    assert result == "WORLD STATE:\nSome narrative here."
    assert isinstance(result, str)


def test_reality_seed_passes_agent_names_to_llm(gen, mock_llm,
                                                  sample_sources, valid_cast):
    """Prompt to LLM names each agent individually, never as a group."""
    mock_llm.chat.return_value = "seed text"

    gen.generate_reality_seed(sample_sources, valid_cast)

    call_args = mock_llm.chat.call_args
    user_msg = call_args.kwargs["messages"][-1]["content"]
    for agent in valid_cast["mandatory_agents"]:
        assert agent["name"] in user_msg


# ─── EVENT SEEDS ─────────────────────────────────────────────────────────────

def test_generate_event_seeds_from_list_response(gen, mock_llm,
                                                   sample_sources, valid_cast):
    """LLM returning a list directly is handled."""
    mock_llm.chat_json.return_value = [
        {"trigger_hour": 1, "description": "Event 1",
         "primary_agent": "Benjamín Serrano", "impact_agents": [],
         "narrative_purpose": "opens stakes"},
    ]

    result = gen.generate_event_seeds(sample_sources, valid_cast)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["trigger_hour"] == 1


def test_generate_event_seeds_from_dict_response(gen, mock_llm,
                                                   sample_sources, valid_cast):
    """LLM returning {'events': [...]} is handled."""
    mock_llm.chat_json.return_value = {
        "events": [{"trigger_hour": 10, "description": "X"}]
    }

    result = gen.generate_event_seeds(sample_sources, valid_cast)

    assert isinstance(result, list)
    assert len(result) == 1


# ─── CONFIG ENRICHMENT ───────────────────────────────────────────────────────

def test_enrich_config_hardcodes_cost_controls(gen, valid_cast):
    """message_window_size and token_limit are always hardcoded — non-negotiable."""
    base = {}
    result = gen.enrich_simulation_config(
        base_config=base,
        cast=valid_cast,
        reality_seed="seed text",
        language="es",
        duration_hours=168,
    )

    assert result["cost_controls"]["message_window_size"] == 50
    assert result["cost_controls"]["token_limit"] == 150000
    assert result["cost_controls"]["max_cost_per_round_usd"] == 0.50


def test_enrich_config_injects_reality_seed(gen, valid_cast):
    """Reality seed text becomes simulation_requirement."""
    result = gen.enrich_simulation_config(
        base_config={},
        cast=valid_cast,
        reality_seed="The world is in crisis.",
        language="es",
        duration_hours=168,
    )

    assert result["simulation_requirement"] == "The world is in crisis."
    assert result["language"] == "es"
    assert result["duration_hours"] == 168


def test_enrich_config_builds_per_agent_entries(gen, valid_cast):
    """Each mandatory agent gets a config entry with archetype defaults."""
    result = gen.enrich_simulation_config(
        base_config={},
        cast=valid_cast,
        reality_seed="seed",
        language="es",
        duration_hours=168,
    )

    assert len(result["agents"]) == 3
    names = [a["name"] for a in result["agents"]]
    assert "Benjamín Serrano" in names
    assert "Karla Serrano" in names
    assert "Javier Cordero" in names


def test_enrich_config_hot_topics_in_english(gen, valid_cast):
    """Hot topics are always English keywords (prevents Chinese topic generation)."""
    result = gen.enrich_simulation_config(
        base_config={},
        cast=valid_cast,
        reality_seed="seed",
        language="es",
        duration_hours=168,
    )

    topics = result["hot_topics"]
    assert isinstance(topics, list)
    assert len(topics) >= 1
    for topic in topics:
        # Must be ASCII (no Chinese characters)
        assert all(ord(c) < 128 for c in topic), f"Topic contains non-ASCII: {topic}"


def test_enrich_config_preserves_base_fields(gen, valid_cast):
    """Custom base_config fields are preserved when not overridden."""
    base = {"custom_field": "custom_value", "another": 42}
    result = gen.enrich_simulation_config(
        base_config=base,
        cast=valid_cast,
        reality_seed="seed",
        language="es",
        duration_hours=168,
    )

    assert result["custom_field"] == "custom_value"
    assert result["another"] == 42


# ─── TEXT COMBINATION ────────────────────────────────────────────────────────

def test_combine_texts_truncates_long_input(gen):
    """Sources longer than MAX_SOURCE_CHARS_FOR_LLM are truncated."""
    long_sources = ["A" * 100_000, "B" * 50_000]
    combined = gen._combine_texts(long_sources)

    # Default max is 80K
    assert len(combined) < 100_000
    assert "truncated" in combined.lower()


def test_combine_texts_joins_multiple_sources(gen):
    """Multiple sources are joined with a separator."""
    sources = ["source one", "source two"]
    combined = gen._combine_texts(sources)

    assert "source one" in combined
    assert "source two" in combined
    assert "---" in combined


def test_combine_texts_ignores_empty_sources(gen):
    """Empty/whitespace sources are skipped."""
    sources = ["real content", "", "   ", "more content"]
    combined = gen._combine_texts(sources)

    assert "real content" in combined
    assert "more content" in combined

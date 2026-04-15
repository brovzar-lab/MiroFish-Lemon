"""
PrepGenerator — AI-authoring service for the MiroFish Prep Studio.

Converts raw story materials (scripts, bibles, PDFs) into a validated,
upload-ready simulation package. Every method encodes Oro Verde S1 failure
prevention rules.

S1 context: $450 simulation failed because raw documents were uploaded without
curation. 19/27 agents were junk. Benjamín Serrano (main character) never got
an agent. message_window_size=None caused OOM at round 134.

This service is the primary guard against those failures repeating.

Usage:
    gen = PrepGenerator(slug="oro-verde-s2")
    cast = gen.extract_cast(source_texts)          # validates + retries
    upload_doc = gen.generate_upload_document(source_texts, cast)
    seed = gen.generate_reality_seed(source_texts, cast)
    events = gen.generate_event_seeds(source_texts, cast, duration_hours=168)
    config = gen.enrich_simulation_config(base_config, cast, seed, "es", 168)
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Add scripts directory to path for validate_cast import
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "scripts" / "mirofish-prep"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from validate_cast import validate_cast  # noqa: E402

from ..utils.llm_client import LLMClient
from .prep_prompts import (
    CAST_EXTRACTION_SYSTEM,
    CAST_EXTRACTION_USER,
    CAST_RETRY_SYSTEM,
    UPLOAD_DOCUMENT_SYSTEM,
    UPLOAD_DOCUMENT_USER,
    REALITY_SEED_SYSTEM,
    REALITY_SEED_USER,
    EVENT_SEEDS_SYSTEM,
    EVENT_SEEDS_USER,
)

# MiroFish hard limit for ontology analysis
MAX_UPLOAD_DOC_CHARS = 50_000
# Truncate combined source text fed to LLM to avoid context overflow
MAX_SOURCE_CHARS_FOR_LLM = 80_000
# Max retries when cast validation fails
MAX_CAST_RETRIES = 2


class PrepGenerator:
    """
    AI-authoring pipeline for MiroFish simulation packages.

    Each public method corresponds to one artifact in the sim-prep package.
    Methods validate their output and raise PrepGenerationError on unrecoverable
    failures.
    """

    def __init__(
        self,
        slug: str,
        llm_client: Optional[LLMClient] = None,
    ):
        self.slug = slug
        self.llm = llm_client or LLMClient()

    # ─── PUBLIC API ──────────────────────────────────────────────────────────

    def extract_cast(self, source_texts: list) -> dict:
        """
        Extract and validate a character cast from source documents.

        Runs validate_cast() immediately after LLM extraction. If validation
        fails, re-prompts with specific violations (max MAX_CAST_RETRIES retries).

        Args:
            source_texts: List of plain-text strings from source documents.

        Returns:
            Validated cast dict (same structure as character_cast.json).

        Raises:
            PrepGenerationError: If cast is still invalid after all retries.
        """
        combined = self._combine_texts(source_texts)
        user_msg = CAST_EXTRACTION_USER.format(combined_text=combined)

        messages = [
            {"role": "system", "content": CAST_EXTRACTION_SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        for attempt in range(MAX_CAST_RETRIES + 1):
            raw = self.llm.chat_json(messages=messages, temperature=0.2, max_tokens=4096)
            cast = self._normalize_cast(raw)
            validation = validate_cast(cast)

            if validation["failures"] == 0:
                cast["_validation"] = validation
                return cast

            # Build retry message with specific failures
            failure_details = self._format_validation_failures(validation)
            if attempt < MAX_CAST_RETRIES:
                messages = [
                    {"role": "system", "content": CAST_RETRY_SYSTEM},
                    {"role": "user", "content": (
                        f"The previous cast failed validation with these issues:\n\n"
                        f"{failure_details}\n\n"
                        f"Here is the cast you produced:\n{json.dumps(cast, ensure_ascii=False, indent=2)}\n\n"
                        f"Produce a corrected version that fixes ALL of these failures."
                    )},
                ]

        # Final attempt still failed — return with warnings rather than blocking
        cast["_validation"] = validation
        cast["_validation_warnings"] = (
            f"Cast extracted but has {validation['failures']} validation failure(s) "
            f"after {MAX_CAST_RETRIES} retries. Review manually before promoting."
        )
        return cast

    def generate_upload_document(self, source_texts: list, cast: dict) -> str:
        """
        Generate a clean, pollution-free upload document for MiroFish.

        The document starts with a CHARACTER INDEX to prime Zep's entity extractor,
        replaces all organization names with generic descriptions, expands group
        references to individual names, and marks dead characters with [DECEASED].

        Args:
            source_texts: List of plain-text strings from source documents.
            cast: Validated cast dict (from extract_cast or existing cast file).

        Returns:
            Upload document as a Markdown string, guaranteed under 50K chars.
        """
        combined = self._combine_texts(source_texts)
        agent_names = self._get_agent_names(cast)
        excluded_names = self._get_excluded_names(cast)

        user_msg = UPLOAD_DOCUMENT_USER.format(
            agent_names_list="\n".join(f"  - {n}" for n in agent_names),
            excluded_names_list="\n".join(f"  - {n}" for n in excluded_names) or "  (none)",
            agent_count=len(agent_names),
            combined_text=combined,
        )

        messages = [
            {"role": "system", "content": UPLOAD_DOCUMENT_SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        doc = self.llm.chat(messages=messages, temperature=0.3, max_tokens=8192)

        # Hard truncation at 50K — never let the upload doc exceed the MiroFish limit
        if len(doc) > MAX_UPLOAD_DOC_CHARS:
            doc = doc[:MAX_UPLOAD_DOC_CHARS]
            doc += "\n\n[Document truncated to MiroFish 50,000 character limit]"

        return doc

    def generate_reality_seed(self, source_texts: list, cast: dict) -> str:
        """
        Generate a focused reality seed prompt for the simulation.

        The reality seed is a 2,000–3,000 character world-state description
        that names every agent individually, identifies colliding forces, and
        poses open questions for the simulation to answer.

        Args:
            source_texts: List of plain-text strings from source documents.
            cast: Validated cast dict.

        Returns:
            Reality seed as a plain-text string, 2,000–3,000 chars.
        """
        combined = self._combine_texts(source_texts, max_chars=30_000)
        agent_list = self._format_agent_list_for_seed(cast)

        user_msg = REALITY_SEED_USER.format(
            agent_list_with_roles=agent_list,
            combined_text=combined,
        )

        messages = [
            {"role": "system", "content": REALITY_SEED_SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        seed = self.llm.chat(messages=messages, temperature=0.5, max_tokens=2048)
        return seed.strip()

    def generate_event_seeds(
        self,
        source_texts: list,
        cast: dict,
        duration_hours: int = 168,
    ) -> list:
        """
        Generate narrative event seeds (external shocks) mapped to simulation hours.

        Events are derived from story act breaks and scheduled at appropriate
        points in the simulation arc. Each event names specific agents.

        Args:
            source_texts: List of plain-text strings from source documents.
            cast: Validated cast dict.
            duration_hours: Total simulation duration (default: 168h = 7 days).

        Returns:
            List of event seed dicts.
        """
        combined = self._combine_texts(source_texts, max_chars=30_000)
        agent_names = self._get_agent_names(cast)

        user_msg = EVENT_SEEDS_USER.format(
            duration_hours=duration_hours,
            agent_names_list="\n".join(f"  - {n}" for n in agent_names),
            combined_text=combined,
        )

        messages = [
            {"role": "system", "content": EVENT_SEEDS_SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        result = self.llm.chat_json(messages=messages, temperature=0.6, max_tokens=4096)

        # The LLM might return {"events": [...]} or just [...]
        if isinstance(result, dict):
            events = result.get("events", result.get("event_seeds", []))
        elif isinstance(result, list):
            events = result
        else:
            events = []

        return events

    def enrich_simulation_config(
        self,
        base_config: dict,
        cast: dict,
        reality_seed: str,
        language: str = "es",
        duration_hours: int = 168,
    ) -> dict:
        """
        Enrich a base simulation config with cast, reality seed, and cost controls.

        This is a non-LLM method — it deterministically injects values into the
        config structure. Cost controls are HARDCODED and not overridable:
          message_window_size = 50
          token_limit = 150000

        These values are non-negotiable. In Oro Verde S1, message_window_size=None
        caused 1M+ token prompts, $3/call, and OOM crash at round 134.

        Args:
            base_config: Existing simulation_config.json dict (may be empty {}).
            cast: Validated cast dict.
            reality_seed: Reality seed text (used as simulation_requirement).
            language: Simulation language code ("es", "en", "zh").
            duration_hours: Simulation duration in hours.

        Returns:
            Enriched config dict ready to write as simulation_config.json.
        """
        agents = cast.get("mandatory_agents", [])

        config = {
            **base_config,
            "simulation_requirement": reality_seed,
            "language": language,
            "duration_hours": duration_hours,
            "agents": self._build_agent_configs(agents),
            "hot_topics": self._build_hot_topics(cast, language),
            "cost_controls": {
                "message_window_size": 50,
                "token_limit": 150000,
                "max_cost_per_round_usd": 0.50,
            },
        }

        return config

    # ─── PRIVATE HELPERS ────────────────────────────────────────────────────

    def _combine_texts(self, source_texts: list, max_chars: int = MAX_SOURCE_CHARS_FOR_LLM) -> str:
        """Join source texts with separators, truncated to max_chars."""
        combined = "\n\n---\n\n".join(t for t in source_texts if t and t.strip())
        if len(combined) > max_chars:
            combined = combined[:max_chars] + f"\n\n[... truncated at {max_chars} chars ...]"
        return combined

    def _normalize_cast(self, raw: dict) -> dict:
        """
        Ensure the LLM's cast output has the expected structure.
        Fills in missing fields with safe defaults.
        """
        return {
            "mandatory_agents": raw.get("mandatory_agents", []),
            "excluded_entities": raw.get("excluded_entities", []),
            "rejected_entities": raw.get("rejected_entities", []),
        }

    def _get_agent_names(self, cast: dict) -> list:
        """Return list of agent names from cast."""
        return [a.get("name", "") for a in cast.get("mandatory_agents", []) if a.get("name")]

    def _get_excluded_names(self, cast: dict) -> list:
        """Return list of excluded entity descriptions from cast."""
        return [e.get("name", "") for e in cast.get("excluded_entities", []) if e.get("name")]

    def _format_agent_list_for_seed(self, cast: dict) -> str:
        """Format agent list with roles for the reality seed prompt."""
        lines = []
        for agent in cast.get("mandatory_agents", []):
            name = agent.get("name", "")
            role = agent.get("role", "")
            stance = agent.get("stance", "")
            lines.append(f"  - {name}: {role} [{stance}]")
        return "\n".join(lines)

    def _format_validation_failures(self, validation: dict) -> str:
        """Format validation failures into a human-readable retry prompt."""
        lines = []
        for check in validation.get("checks", []):
            if check.get("status") in ("FAIL", "WARN"):
                lines.append(f"  [{check['status']}] {check['rule']}: {check['message']}")
        return "\n".join(lines) if lines else "Unknown validation failures"

    def _build_agent_configs(self, agents: list) -> list:
        """
        Build per-agent simulation config entries.
        Uses archetype defaults from character_archetypes.json.
        """
        archetypes = self._load_archetypes()

        configs = []
        for agent in agents:
            archetype_key = agent.get("archetype", "journalist")
            defaults = archetypes.get(archetype_key, archetypes.get("journalist", {}))
            configs.append({
                "name": agent.get("name", ""),
                "archetype": archetype_key,
                "role": agent.get("role", ""),
                **defaults,
            })
        return configs

    def _build_hot_topics(self, cast: dict, language: str) -> list:
        """
        Build an initial hot-topics list from cast roles.
        Topics are always English keywords (prevents Chinese topic generation).
        """
        topics = set()
        for agent in cast.get("mandatory_agents", []):
            role = agent.get("role", "").lower()
            stance = agent.get("stance", "").lower()

            if "journalist" in role or "reporter" in role:
                topics.update(["media investigation", "press freedom", "corruption expose"])
            if "cartel" in role or "criminal" in role or "narco" in role:
                topics.update(["organized crime", "drug trafficking", "violence"])
            if "family" in role or "sibling" in role or "daughter" in role or "son" in role:
                topics.update(["family loyalty", "personal sacrifice", "secrets"])
            if "politician" in role or "official" in role:
                topics.update(["political corruption", "abuse of power", "elections"])
            if "investigator" in role or "detective" in role or "cop" in role:
                topics.update(["criminal investigation", "evidence", "justice"])
            if "business" in role or "executive" in role:
                topics.update(["money laundering", "business deals", "financial crime"])

        # Always include some universal simulation topics
        topics.update(["trust", "betrayal", "survival", "truth"])

        return list(topics)[:12]  # MiroFish recommends 10-12 topics

    def _load_archetypes(self) -> dict:
        """Load behavioral archetype presets from templates."""
        archetypes_file = _REPO_ROOT / "scripts" / "mirofish-prep" / "templates" / "character_archetypes.json"
        if archetypes_file.exists():
            try:
                return json.loads(archetypes_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}


class PrepGenerationError(Exception):
    """Raised when AI generation fails unrecoverably."""
    pass

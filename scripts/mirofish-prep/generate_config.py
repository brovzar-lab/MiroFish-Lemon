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

    agent_configs = []
    for i, agent in enumerate(agents):
        archetype = match_archetype(agent.get('role', ''), archetypes)

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

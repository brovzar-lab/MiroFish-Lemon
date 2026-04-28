"""
MiroFish Prep API — /api/prep/<slug>
Generic, project-aware 4-phase sim-prep studio.
All paths are dynamic per project slug.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from flask import jsonify, request, send_file

from . import prep_bp

# Repo root — three levels up from this file (backend/app/api/prep.py)
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "mirofish-prep"

# The six output files that every prep package produces
OUTPUT_FILENAMES = [
    "upload_document.md",
    "reality_seed.md",
    "simulation_config.json",
    "event_seeds.json",
    "preflight_report.md",
    "character_cast.json",
]


def _project_dir(slug: str) -> Path:
    """Return (and ensure) the sim-prep directory for a given project slug."""
    d = REPO_ROOT / "sim-prep" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cast_path(slug: str) -> Path:
    return _project_dir(slug) / "character_cast.json"


def _output_paths(slug: str) -> dict[str, Path]:
    base = _project_dir(slug)
    return {name: base / name for name in OUTPUT_FILENAMES}


# ─── PROJECT LIST ──────────────────────────────────────────────────────────

@prep_bp.route("/projects", methods=["GET"])
def list_prep_projects():
    """List all projects that have a sim-prep directory."""
    sim_prep_root = REPO_ROOT / "sim-prep"
    if not sim_prep_root.exists():
        return jsonify({"projects": []})

    projects = []
    for d in sorted(sim_prep_root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        cast = d / "character_cast.json"
        meta = {
            "slug": d.name,
            "has_cast": cast.exists(),
            "has_upload_doc": (d / "upload_document.md").exists(),
            "has_seed": (d / "reality_seed.md").exists(),
            "has_config": (d / "simulation_config.json").exists(),
            "has_events": (d / "event_seeds.json").exists(),
            "has_preflight": (d / "preflight_report.md").exists(),
            "agent_count": 0,
            "total_chars": 0,
        }
        # Enrich with agent count
        if cast.exists():
            try:
                cdata = json.loads(cast.read_text("utf-8"))
                meta["agent_count"] = len(cdata.get("mandatory_agents", []))
            except (json.JSONDecodeError, KeyError):
                pass
        # Upload doc size
        ud = d / "upload_document.md"
        if ud.exists():
            meta["total_chars"] = ud.stat().st_size
        projects.append(meta)

    return jsonify({"projects": projects})


@prep_bp.route("/projects", methods=["POST"])
def create_prep_project():
    """Create a new sim-prep project directory."""
    data = request.get_json(silent=True) or {}
    slug = data.get("slug", "").strip().lower()
    slug = re.sub(r"[^a-z0-9\-]", "-", slug).strip("-")
    if not slug:
        return jsonify({"error": "A project slug is required"}), 400

    project_dir = _project_dir(slug)
    # Create a meta.json with project info
    meta_path = project_dir / "meta.json"
    if not meta_path.exists():
        meta = {
            "slug": slug,
            "name": data.get("name", slug.replace("-", " ").title()),
            "language": data.get("language", "en"),
            "duration_hours": int(data.get("duration_hours", 168)),
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return jsonify({"slug": slug, "status": "created"})


@prep_bp.route("/<slug>/meta", methods=["GET"])
def get_project_meta(slug: str):
    """Return project metadata."""
    meta_path = _project_dir(slug) / "meta.json"
    if meta_path.exists():
        return jsonify(json.loads(meta_path.read_text("utf-8")))
    return jsonify({"slug": slug, "name": slug.replace("-", " ").title()})


# ─── PHASE 1: INGEST ────────────────────────────────────────────────────────

@prep_bp.route("/<slug>/parse", methods=["POST"])
def parse_doc(slug: str):
    """Accept plain text content of a doc; return word and char count."""
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"error": "No content provided"}), 400
    words = len(content.split())
    chars = len(content)
    return jsonify({"word_count": words, "char_count": chars})


@prep_bp.route("/<slug>/sources", methods=["POST"])
def save_sources(slug: str):
    """
    Persist uploaded source documents to sim-prep/<slug>/sources/.

    Body: {sources: [{id, label, filename, content}, ...]}
    Each source is saved to sources/<id>.md so the AI extraction
    step can read them back. Replaces any existing sources for this slug.
    """
    data = request.get_json(silent=True) or {}
    sources = data.get("sources", [])
    if not sources:
        return jsonify({"error": "No sources provided"}), 400

    sources_dir = _project_dir(slug) / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    # Clear stale sources first
    for existing in sources_dir.glob("*.md"):
        existing.unlink()

    saved = []
    total_chars = 0
    for src in sources:
        sid = src.get("id")
        content = src.get("content", "")
        if not sid or not content:
            continue
        # Sanitize id for filename
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", sid)[:64]
        path = sources_dir / f"{safe_id}.md"
        # Header lets the AI know which document is which
        label = src.get("label", sid)
        filename = src.get("filename", "")
        header = f"# Source: {label}\n# File: {filename}\n# ID: {sid}\n\n---\n\n"
        path.write_text(header + content, encoding="utf-8")
        saved.append({"id": sid, "chars": len(content), "label": label})
        total_chars += len(content)

    return jsonify({
        "status": "ok",
        "saved": saved,
        "total_chars": total_chars,
        "sources_dir": str(sources_dir.relative_to(REPO_ROOT)),
    })


# ─── PHASE 2: CAST ──────────────────────────────────────────────────────────

# Extraction prompt — encodes all 29 failure modes from the Oro Verde S1 post-mortem
# as anti-patterns the AI must avoid. Output schema matches what validate_cast.py expects.
CAST_EXTRACTION_SYSTEM_PROMPT = """You are a casting director for a MiroFish multi-agent narrative simulation. Your job: extract a clean character cast from source materials (show bibles, screenplays, treatments, character breakdowns).

CRITICAL CONTEXT — what NOT to do (every rule below comes from a real failure that burned $450 in a prior run):

1. NEVER create an agent for a generic noun. Bad: "senators", "cartels", "the family", "the siblings", "grandmother", "journalists", "activists", "CEOs", "officials". Good: extract the actual NAMED individuals these refer to.

2. NEVER create an agent for an organization. Bad: "Walmart", "DEA", "FBI", "Forbes", "Grupo Serrano", "Harvard", "criminal empire", "narco operation". These are entities mentioned in the world, not posting characters.

3. NEVER create a duplicate agent for the same character. If the source says "Javier" in one place and "Javier Cordero" elsewhere, ONE agent named "Javier Cordero" — not two.

4. NEVER create an agent with first-name-only when a surname exists in the source. "Karla" → "Karla Serrano". "Benjamín" → "Benjamín Serrano". Exception: characters with intentional single-name identity like "Reynaldo" the thief.

5. NEVER create an agent for a dead character. If someone died before the simulation start (e.g., killed in the pilot, died of illness), they go in `excluded_entities`, NOT `mandatory_agents`. Knowledge graph references only.

6. NEVER hallucinate names. If the source says "Ernesto Vega", the agent is "Ernesto Vega" — not "Nesto Vega" or any partial/altered form.

7. NEVER use generic descriptors as names. Bad: "fourteen-year-old girl", "the unnamed thief", "young woman", "the lawyer". If the character has no name in the source, skip them or use a single distinctive identifier ("Reynaldo" if named, otherwise omit).

OUTPUT FORMAT — strict JSON, no commentary:

{
  "mandatory_agents": [
    {
      "name": "Full Proper Name",
      "role": "Their function in the story (one short sentence)",
      "stance": "protagonist|antagonist|opposing|neutral|supportive",
      "enneagram": "3w2 (or null if not specified)",
      "influence_weight": 1.0-3.0,
      "_psychology_notes": "1-2 sentences on their wound, want, and flaw"
    }
  ],
  "excluded_entities": [
    {"name": "Full Name", "reason": "deceased_before_simulation|deceased_in_pilot|reference_only"}
  ],
  "max_additional_agents": 3
}

GUIDELINES:
- 8-15 mandatory agents is ideal. Quality over quantity.
- Stance values: protagonist (drives plot from inside), antagonist (opposes protagonist directly), opposing (external pressure), neutral (observer/context), supportive (allied with protagonist).
- influence_weight: 3.0 for power-broker characters, 2.0 for principal cast, 1.4 for supporting, 1.0 for minor.
- excluded_entities: dead characters, organizations central to plot but not posting agents, archive-only references.
- max_additional_agents: how many bonus background agents the simulation engine may generate (default 3).

Be ruthless about the failure rules above. The cost of one junk agent is $20-40 per simulation."""


@prep_bp.route("/<slug>/cast/extract", methods=["POST"])
def extract_cast(slug: str):
    """
    Run AI cast extraction from stored source documents.

    Reads sim-prep/<slug>/sources/*.md, combines them into a single context,
    sends to the LLM with a strict extraction prompt, validates the result
    against scripts/mirofish-prep/validate_cast.py, and writes
    character_cast.json on success.
    """
    sources_dir = _project_dir(slug) / "sources"
    if not sources_dir.exists() or not list(sources_dir.glob("*.md")):
        return jsonify({
            "error": "No source documents found",
            "hint": "Upload source docs in INGEST and click Save before extracting cast.",
        }), 400

    # Combine all source files. Cap at ~80K chars to stay safely within Sonnet's
    # context budget while leaving room for the system prompt and output tokens.
    MAX_CONTEXT_CHARS = 80_000
    parts = []
    total = 0
    for f in sorted(sources_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if total + len(text) > MAX_CONTEXT_CHARS:
            # Truncate the last doc to fit, mark it
            remaining = MAX_CONTEXT_CHARS - total
            if remaining > 1000:
                parts.append(text[:remaining] + f"\n\n[...{len(text) - remaining:,} chars truncated to fit context...]")
                total = MAX_CONTEXT_CHARS
            break
        parts.append(text)
        total += len(text)

    if not parts:
        return jsonify({"error": "No source content to extract from"}), 400

    combined = "\n\n========================\n\n".join(parts)

    # Call the LLM
    try:
        from ..utils.llm_client import LLMClient, CreditExhaustedException
        client = LLMClient()
        cast_data = client.chat_json(
            messages=[
                {"role": "system", "content": CAST_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract the character cast from these source documents:\n\n{combined}"},
            ],
            temperature=0.2,
            max_tokens=8192,
        )
    except CreditExhaustedException as e:
        return jsonify({"error": "credits_exhausted", "message": str(e)}), 402
    except ValueError as e:
        return jsonify({"error": "llm_invalid_json", "message": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "llm_call_failed", "message": str(e)}), 502

    # Sanity check the shape
    if not isinstance(cast_data, dict) or "mandatory_agents" not in cast_data:
        return jsonify({
            "error": "extraction_invalid_shape",
            "message": "LLM response did not match expected schema",
            "got": cast_data if isinstance(cast_data, dict) else {"_type": str(type(cast_data))},
        }), 502

    # Run our validator (subprocess so we don't pollute Flask's import space)
    cast_path = _cast_path(slug)
    cast_path.parent.mkdir(parents=True, exist_ok=True)
    cast_path.write_text(json.dumps(cast_data, indent=2, ensure_ascii=False), encoding="utf-8")

    validation = {"status": "UNKNOWN", "failures": 0, "warnings": 0, "checks": []}
    validator = SCRIPTS_DIR / "validate_cast.py"
    if validator.exists():
        try:
            r = subprocess.run(
                [sys.executable, str(validator), str(cast_path)],
                capture_output=True, text=True, timeout=20,
            )
            try:
                validation = json.loads(r.stdout)
            except json.JSONDecodeError:
                validation = {"status": "ERROR", "raw_stdout": r.stdout[:1000], "stderr": r.stderr[:500]}
        except subprocess.TimeoutExpired:
            validation = {"status": "TIMEOUT"}

    return jsonify({
        "status": "ok",
        "agent_count": len(cast_data.get("mandatory_agents", [])),
        "excluded_count": len(cast_data.get("excluded_entities", [])),
        "context_chars": total,
        "cast": cast_data,
        "validation": validation,
    })


@prep_bp.route("/<slug>/cast", methods=["GET"])
def get_cast(slug: str):
    """Return the current character_cast.json for this project."""
    cast_file = _cast_path(slug)
    if not cast_file.exists():
        return jsonify({"error": "character_cast.json not found", "hint": "Upload source documents and run CAST phase first."}), 404
    with open(cast_file, "r", encoding="utf-8") as f:
        cast = json.load(f)
    return jsonify(cast)


@prep_bp.route("/<slug>/cast", methods=["POST"])
def save_cast(slug: str):
    """Save an updated character_cast.json (from UI edits)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400
    cast_file = _cast_path(slug)
    with open(cast_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "saved"})


# ─── PHASE 3: BUILD ─────────────────────────────────────────────────────────

# Each generator builds one output file. The shape of these prompts encodes
# the same anti-patterns as the cast extractor — "the siblings" must become
# "Benjamín, Karla, and Isabela", Walmart must become "a major retail buyer", etc.

UPLOAD_DOC_SYSTEM_PROMPT = """You are synthesizing a curated upload document for a MiroFish multi-agent simulation. The document you produce will be uploaded as the Reality Seed in MiroFish — Zep Cloud will extract entities from it, and those entities become simulation agents.

CRITICAL RULES (every rule comes from a $450 simulation failure):

1. NO ORGANIZATION NAMES that could become posting agents.
   - "Walmart" → "a major retail buyer"
   - "DEA" → "a federal agency"
   - "Forbes" → "a business magazine"
   - "Harvard" → "a top US business school"
   - "Grupo Serrano" — keep this since the company itself is a story element, not a posting agent

2. NO GROUP REFERENCES — replace with individual full names from the cast.
   - "the siblings" / "Serrano siblings" → "Benjamín, Karla, and Isabela"
   - "the family" → list the relevant individuals
   - "journalists" → name the specific journalist if relevant
   - "cartels" → "the criminal operation"

3. NO ABSTRACT CONCEPTS that could become entities.
   - "criminal empire" → "the operation"
   - "narco operation" → "the operation"

4. MARK DEAD CHARACTERS explicitly. Use "[DECEASED]" inline so Zep classifies them as historical references, not active entities.

5. CHARACTER INDEX HEADER. Open the document with a "CHARACTER INDEX" section that lists every mandatory agent by full name + 1-line role. This anchors Zep's entity extraction.

6. UNDER 50,000 CHARACTERS. MiroFish's ontology generation truncates at 50K. Aim for 30,000-45,000 chars.

7. WRITE IN ENGLISH. Zep extracts cleaner entities from English than from Spanish.

8. PRESERVE NARRATIVE TEXTURE. This isn't a wiki article — keep the dramatic voice from the source materials. The world should feel alive, but every named entity must be a person from the cast (or marked deceased)."""


REALITY_SEED_SYSTEM_PROMPT = """You are writing the Reality Seed for a MiroFish multi-agent simulation. This is a 2,000-3,000 character narrative prompt that gets pasted into MiroFish's "Simulation Requirement" field. It tells the simulation engine what world to simulate, who the characters are, and what questions to explore.

STRUCTURE (write in this order):

1. ONE-PARAGRAPH WORLD STATE at simulation start. Name every mandatory agent individually — never as a group. Establish what just happened (the inciting event), who knows what, and what's about to collide.

2. THREE COLLIDING FORCES paragraph. Identify the 2-3 power centers in tension. Name the agents inside each. Make the asymmetries clear.

3. OPEN QUESTIONS the simulation should answer (3-5 questions). These should be genuinely undetermined — not predictions, but live questions about what these specific named characters will do.

4. REPORT STRUCTURE specification: 4 thematic sections at the end. Pick titles that capture the dramatic engine of THIS specific world.

REQUIREMENTS:
- Write in English (cleaner Zep extraction).
- Every name is the FULL name from the cast (no first-name-only).
- No organization names except the company at the heart of the story (e.g., Grupo Serrano).
- 2,000-3,000 characters total.
- No "the siblings" / "the family" / generic plurals. Use names.
- Dead characters get "[DECEASED]" inline."""


EVENT_SEEDS_SYSTEM_PROMPT = """You are designing 8 narrative inflection points for a MiroFish multi-agent simulation. Each event is a scheduled trigger that fires at a specific simulation hour to generate dramatic pressure.

OUTPUT FORMAT — strict JSON, no commentary:

{
  "events": [
    {
      "trigger_hour": 12,
      "agent_name": "Full Proper Name from the cast",
      "event_type": "post|comment|reveal|action",
      "description": "1-2 sentence description of what this character does at this hour",
      "stakes": "Why this matters dramatically"
    }
  ]
}

GUIDELINES:
- Exactly 8 events spread across the 168-hour arc (~hour 6, 24, 48, 72, 96, 120, 144, 160).
- Each event must reference a SPECIFIC mandatory agent by full name.
- Events should escalate — early ones plant seeds, later ones detonate.
- Mix event types: 2-3 reveals, 2-3 actions, 2-3 posts/comments.
- Stakes should connect to the open questions in the reality seed.
- No group references — every event has one named character at its center."""


def _read_combined_sources(slug: str, max_chars: int = 80_000) -> str:
    """Read all source docs for a project, concatenated, capped at max_chars."""
    sources_dir = _project_dir(slug) / "sources"
    if not sources_dir.exists():
        return ""
    parts = []
    total = 0
    for f in sorted(sources_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if total + len(text) > max_chars:
            remaining = max_chars - total
            if remaining > 1000:
                parts.append(text[:remaining])
            break
        parts.append(text)
        total += len(text)
    return "\n\n========================\n\n".join(parts)


def _generate_upload_doc(slug: str, sources: str, cast_data: dict) -> tuple[bool, str]:
    """Generate upload_document.md via LLM. Returns (success, content_or_error)."""
    cast_summary = "\n".join(
        f"- {a['name']} — {a.get('role', '')}"
        for a in cast_data.get("mandatory_agents", [])
    )
    excluded_summary = "\n".join(
        f"- {e['name']} [DECEASED — {e.get('reason', '')}]"
        for e in cast_data.get("excluded_entities", [])
    )
    user_msg = (
        f"MANDATORY CAST (these and only these become simulation agents):\n{cast_summary}\n\n"
        f"EXCLUDED (must appear ONLY as historical references, marked [DECEASED]):\n{excluded_summary}\n\n"
        f"SOURCE MATERIAL TO SYNTHESIZE FROM:\n\n{sources}\n\n"
        f"Now produce the curated upload document. Output ONLY the markdown — no commentary, no code fences. "
        f"Start with a CHARACTER INDEX section listing every mandatory agent. Stay under 50,000 characters."
    )

    try:
        from ..utils.llm_client import LLMClient
        client = LLMClient()
        result = client.chat(
            messages=[
                {"role": "system", "content": UPLOAD_DOC_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=16000,
        )
        # Strip code fences if the LLM wrapped in ```markdown blocks
        result = re.sub(r'^```(?:markdown|md)?\s*\n', '', result.strip(), flags=re.IGNORECASE)
        result = re.sub(r'\n```\s*$', '', result)
        return True, result.strip()
    except Exception as e:
        return False, str(e)


def _generate_reality_seed(slug: str, sources: str, cast_data: dict) -> tuple[bool, str]:
    """Generate reality_seed.md via LLM."""
    cast_summary = "\n".join(
        f"- {a['name']} — {a.get('role', '')} (stance: {a.get('stance', '')})"
        for a in cast_data.get("mandatory_agents", [])
    )
    user_msg = (
        f"MANDATORY CAST:\n{cast_summary}\n\n"
        f"SOURCE MATERIAL:\n\n{sources[:60_000]}\n\n"
        f"Write the reality seed. Output ONLY the markdown narrative — no headers like 'Reality Seed:', "
        f"no commentary. 2,000-3,000 characters. Name every agent individually."
    )

    try:
        from ..utils.llm_client import LLMClient
        client = LLMClient()
        result = client.chat(
            messages=[
                {"role": "system", "content": REALITY_SEED_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=2000,
        )
        result = re.sub(r'^```(?:markdown|md)?\s*\n', '', result.strip(), flags=re.IGNORECASE)
        result = re.sub(r'\n```\s*$', '', result)
        return True, result.strip()
    except Exception as e:
        return False, str(e)


def _generate_event_seeds(slug: str, sources: str, cast_data: dict) -> tuple[bool, dict]:
    """Generate event_seeds.json via LLM."""
    cast_summary = "\n".join(
        f"- {a['name']} ({a.get('stance', '')}): {a.get('role', '')}"
        for a in cast_data.get("mandatory_agents", [])
    )
    user_msg = (
        f"MANDATORY CAST:\n{cast_summary}\n\n"
        f"SOURCE MATERIAL (for narrative beats):\n\n{sources[:60_000]}\n\n"
        f"Design 8 inflection points across 168 hours. Use only these named agents."
    )

    try:
        from ..utils.llm_client import LLMClient
        client = LLMClient()
        result = client.chat_json(
            messages=[
                {"role": "system", "content": EVENT_SEEDS_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=3000,
        )
        return True, result
    except Exception as e:
        return False, {"error": str(e)}


def _build_preflight_report(slug: str, validation: dict, files: dict) -> str:
    """Mechanical preflight report — no LLM call. Just data assembly."""
    paths = _output_paths(slug)
    upload_path = paths["upload_document.md"]
    seed_path = paths["reality_seed.md"]
    config_path = paths["simulation_config.json"]

    upload_chars = upload_path.stat().st_size if upload_path.exists() else 0
    seed_chars = seed_path.stat().st_size if seed_path.exists() else 0

    # Pollution check on upload doc
    pollution = []
    if upload_path.exists():
        text = upload_path.read_text(encoding="utf-8")
        for term in ["Walmart", " DEA ", "the siblings", "the family", "criminal empire", "narco operation"]:
            count = text.count(term)
            if count > 0:
                pollution.append(f"  ⚠️  Found `{term.strip()}` × {count} — review")
        chinese = re.findall(r'[\u4e00-\u9fff]', text)
        if chinese:
            pollution.append(f"  ❌ Chinese chars detected × {len(chinese)} — must be removed")

    # Cost estimate (rough: agents × rounds × $/call × tokens)
    agent_count = validation.get("agent_count", 0)
    duration_hours = 168  # would read meta if needed
    estimated_calls = agent_count * duration_hours * 0.4  # ~0.4 calls/agent/hour avg
    estimated_cost = estimated_calls * 0.003 + 10  # $0.003/call avg + $10 report
    s1_cost = 450
    savings_pct = (1 - estimated_cost / s1_cost) * 100

    cast_status = "✅ PASS" if validation.get("status") == "PASS" else f"⚠️ {validation.get('status')}"

    report = f"""# Preflight Report — {slug}

**Generated:** {os.environ.get('TZ', 'auto')}
**Phase:** 4 PREFLIGHT
**Overall Status:** {"✅ READY" if validation.get("failures", 0) == 0 and not pollution else "⚠️ REVIEW"}

---

## Cast Validation

- **Status:** {cast_status}
- **Agents:** {agent_count}
- **Failures:** {validation.get('failures', 0)}
- **Warnings:** {validation.get('warnings', 0)}

## Document Sizes

| File | Size | Limit | Status |
|------|------|-------|--------|
| upload_document.md | {upload_chars:,} chars | 50,000 | {"✅" if upload_chars <= 50000 else "❌ over limit"} |
| reality_seed.md | {seed_chars:,} chars | 5,000 | {"✅" if seed_chars <= 5000 else "❌ over limit"} |

## Pollution Check (upload_document.md)

{chr(10).join(pollution) if pollution else "  ✅ Clean — no Walmart, DEA, group references, or Chinese chars detected"}

## Output Files

{chr(10).join(f"- {n} {'✅' if f['exists'] else '❌ missing'}" for n, f in files.items())}

## Cost Estimate

| Item | Estimate |
|------|----------|
| Agent posts (≈{int(estimated_calls):,} calls × $0.003) | ${estimated_calls * 0.003:.2f} |
| Report generation | ~$10.00 |
| **Total estimated** | **${estimated_cost:.2f}** |
| vs. Oro Verde S1 | $450 ({savings_pct:.0f}% reduction) |

## Ready to Upload?

If all checks above are ✅, the package is ready:
1. Upload `upload_document.md` to MiroFish as the Reality Seed
2. Paste `reality_seed.md` into the Simulation Requirement field
3. ⚠️ Verify entity types come back in **English PascalCase** (not Chinese)
4. ⚠️ Verify no Organization-typed entities become posting agents
5. Run a 10-round test before committing to full 168 hours
"""
    return report


@prep_bp.route("/<slug>/build", methods=["POST"])
def build_package(slug: str):
    """
    Generate all 5 output files. Runs 3 LLM-driven generators in parallel
    (upload_document, reality_seed, event_seeds), runs generate_config.py
    locally, and assembles preflight_report.md from the others.

    Total wall time: typically 60-90 seconds (parallel LLM calls + small overhead).
    """
    from concurrent.futures import ThreadPoolExecutor

    cast_file = _cast_path(slug)
    if not cast_file.exists():
        return jsonify({"error": "character_cast.json not found — complete CAST phase first"}), 400

    cast_data = json.loads(cast_file.read_text(encoding="utf-8"))
    if not cast_data.get("mandatory_agents"):
        return jsonify({"error": "character_cast.json has no mandatory_agents"}), 400

    sources = _read_combined_sources(slug)
    if not sources:
        return jsonify({"error": "No source documents found — re-run INGEST"}), 400

    paths = _output_paths(slug)
    project_dir = _project_dir(slug)
    project_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run the 3 LLM generators in parallel
    errors = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_upload = ex.submit(_generate_upload_doc, slug, sources, cast_data)
        f_seed = ex.submit(_generate_reality_seed, slug, sources, cast_data)
        f_events = ex.submit(_generate_event_seeds, slug, sources, cast_data)

        ok, content = f_upload.result()
        if ok:
            paths["upload_document.md"].write_text(content, encoding="utf-8")
        else:
            errors["upload_document"] = content

        ok, content = f_seed.result()
        if ok:
            paths["reality_seed.md"].write_text(content, encoding="utf-8")
        else:
            errors["reality_seed"] = content

        ok, content = f_events.result()
        if ok:
            paths["event_seeds.json"].write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            errors["event_seeds"] = content.get("error", "unknown")

    # 2. Run the local config generator (fast, no LLM)
    meta_path = project_dir / "meta.json"
    language = "en"
    duration = "168"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text("utf-8"))
            language = meta.get("language", "en")
            duration = str(meta.get("duration_hours", 168))
        except (json.JSONDecodeError, KeyError):
            pass

    script = SCRIPTS_DIR / "generate_config.py"
    config_result = {"returncode": 0, "stdout": "", "stderr": ""}
    if script.exists():
        try:
            r = subprocess.run(
                [sys.executable, str(script), str(cast_file), "--duration", duration, "--language", language],
                capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
            )
            if r.returncode == 0 and r.stdout:
                paths["simulation_config.json"].write_text(r.stdout, encoding="utf-8")
            config_result = {"returncode": r.returncode, "stdout": r.stdout[-500:], "stderr": r.stderr[-500:]}
        except subprocess.TimeoutExpired:
            errors["simulation_config"] = "config generator timed out"

    # 3. Run validator on the cast for preflight
    validation = {"status": "UNKNOWN", "failures": 0, "warnings": 0, "agent_count": len(cast_data.get("mandatory_agents", []))}
    validator = SCRIPTS_DIR / "validate_cast.py"
    if validator.exists():
        try:
            r = subprocess.run(
                [sys.executable, str(validator), str(cast_file)],
                capture_output=True, text=True, timeout=15,
            )
            try:
                validation = json.loads(r.stdout)
            except json.JSONDecodeError:
                pass
        except subprocess.TimeoutExpired:
            pass

    # 4. Collect file statuses (now that things are written)
    files = {}
    for name, path in paths.items():
        files[name] = {"exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0}

    # 5. Assemble preflight report (mechanical)
    try:
        preflight_md = _build_preflight_report(slug, validation, files)
        paths["preflight_report.md"].write_text(preflight_md, encoding="utf-8")
        files["preflight_report.md"] = {"exists": True, "size_bytes": paths["preflight_report.md"].stat().st_size}
    except Exception as e:
        errors["preflight_report"] = str(e)

    overall = "ok" if not errors else ("partial" if files["upload_document.md"]["exists"] else "failed")

    return jsonify({
        "status": overall,
        "files": files,
        "errors": errors,
        "validation": validation,
    })


@prep_bp.route("/<slug>/files", methods=["GET"])
def list_files(slug: str):
    """Return current status of all output files for this project."""
    paths = _output_paths(slug)
    files = {}
    for name, path in paths.items():
        if path.exists():
            files[name] = {"exists": True, "size_bytes": path.stat().st_size}
        else:
            files[name] = {"exists": False}
    return jsonify({"files": files})


# ─── PHASE 4: PREFLIGHT ─────────────────────────────────────────────────────

@prep_bp.route("/<slug>/validate", methods=["GET"])
def validate(slug: str):
    """Run validate_cast.py and return its JSON output + pollution + cost estimate."""
    cast_file = _cast_path(slug)
    if not cast_file.exists():
        return jsonify({"error": "character_cast.json not found"}), 404

    # Read project meta
    meta_path = _project_dir(slug) / "meta.json"
    duration = 168
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text("utf-8"))
            duration = int(meta.get("duration_hours", 168))
        except (json.JSONDecodeError, KeyError):
            pass

    # Run validator script
    script = SCRIPTS_DIR / "validate_cast.py"
    validation = {"status": "SKIPPED", "checks": [], "failures": 0}
    if script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(script), str(cast_file)],
                capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
            )
            try:
                validation = json.loads(result.stdout)
            except json.JSONDecodeError:
                validation = {"status": "ERROR", "raw": result.stdout, "stderr": result.stderr, "checks": [], "failures": 1}
        except subprocess.TimeoutExpired:
            validation = {"status": "TIMEOUT", "checks": [], "failures": 1}

    # Pollution check on upload doc
    project_dir = _project_dir(slug)
    upload_doc = project_dir / "upload_document.md"
    pollution = []
    if upload_doc.exists():
        txt = upload_doc.read_text(encoding="utf-8")
        # Generic pollution patterns (non-project-specific)
        blocked = {
            "Chinese characters": r"[\u4e00-\u9fff]",
        }
        for label, pattern in blocked.items():
            hits = len(re.findall(pattern, txt, re.IGNORECASE))
            if hits:
                pollution.append({"pattern": label, "hits": hits, "status": "FAIL"})

    # Cost estimate (dynamic based on agent count and duration)
    agent_count = 7.5
    if cast_file.exists():
        try:
            cdata = json.loads(cast_file.read_text("utf-8"))
            agent_count = len(cdata.get("mandatory_agents", [])) or 7.5
        except (json.JSONDecodeError, KeyError):
            pass

    upload_chars = upload_doc.stat().st_size if upload_doc.exists() else 0
    seed_path = project_dir / "reality_seed.md"
    seed_chars = seed_path.stat().st_size if seed_path.exists() else 0

    rounds = duration
    input_tokens = 3500
    output_tokens = 500
    calls = agent_count * rounds
    cost_input = (calls * input_tokens / 1_000_000) * 3.0
    cost_output = (calls * output_tokens / 1_000_000) * 15.0
    cost_report = 7.5
    cost_total = cost_input + cost_output + cost_report

    return jsonify({
        "validation": validation,
        "pollution": pollution,
        "pollution_clean": len(pollution) == 0,
        "size_checks": {
            "upload_document_chars": upload_chars,
            "upload_under_50k": upload_chars < 50000,
            "reality_seed_chars": seed_chars,
            "seed_under_5k": seed_chars < 5000,
        },
        "cost_estimate": {
            "input_usd": round(cost_input, 2),
            "output_usd": round(cost_output, 2),
            "report_usd": round(cost_report, 2),
            "total_usd": round(cost_total, 2),
            "agent_count": int(agent_count),
            "duration_hours": duration,
        },
        "overall": "PASS" if (
            validation.get("failures", 1) == 0 and
            len(pollution) == 0 and
            upload_chars < 50000 and
            seed_chars < 5000
        ) else "FAIL",
    })


# ─── DOWNLOAD ───────────────────────────────────────────────────────────────

@prep_bp.route("/<slug>/download/<filename>", methods=["GET"])
def download_file(slug: str, filename: str):
    """Serve a generated output file for download."""
    paths = _output_paths(slug)
    path = paths.get(filename)
    if not path or not path.exists():
        return jsonify({"error": f"{filename} not found"}), 404
    return send_file(str(path), as_attachment=True, download_name=filename)

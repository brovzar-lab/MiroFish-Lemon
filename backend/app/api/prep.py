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


# ─── PHASE 2: CAST ──────────────────────────────────────────────────────────

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

@prep_bp.route("/<slug>/build", methods=["POST"])
def build_package(slug: str):
    """
    Run generate_config.py against the cast file, report output file statuses.
    Language and duration are read from project meta.json.
    """
    cast_file = _cast_path(slug)
    if not cast_file.exists():
        return jsonify({"error": "character_cast.json not found — complete CAST phase first"}), 400

    # Read project meta for language/duration
    meta_path = _project_dir(slug) / "meta.json"
    language = "en"
    duration = "168"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text("utf-8"))
            language = meta.get("language", "en")
            duration = str(meta.get("duration_hours", 168))
        except (json.JSONDecodeError, KeyError):
            pass

    # Run the config generator script
    script = SCRIPTS_DIR / "generate_config.py"
    if script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(script), str(cast_file), "--duration", duration, "--language", language],
                capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
            )
        except subprocess.TimeoutExpired:
            result = type("R", (), {"returncode": 1, "stdout": "", "stderr": "timeout"})()
    else:
        result = type("R", (), {"returncode": 0, "stdout": "generate_config.py not found — skipped", "stderr": ""})()

    # Collect file statuses
    paths = _output_paths(slug)
    files = {}
    for name, path in paths.items():
        if path.exists():
            files[name] = {"exists": True, "size_bytes": path.stat().st_size}
        else:
            files[name] = {"exists": False}

    return jsonify({
        "status": "ok" if result.returncode == 0 else "warning",
        "generator_stdout": (result.stdout or "")[-2000:],
        "generator_stderr": (result.stderr or "")[-500:],
        "files": files,
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

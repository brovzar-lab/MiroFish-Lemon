"""
MiroFish Prep API — /api/prep
Supports the 4-phase sim-prep studio UI.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from flask import jsonify, request, send_file

from . import prep_bp

# Repo root — two levels up from this file
REPO_ROOT = Path(__file__).resolve().parents[3]
SIM_PREP_DIR = REPO_ROOT / "sim-prep" / "oro-verde"
SCRIPTS_DIR = REPO_ROOT / "scripts" / "mirofish-prep"
CAST_FILE = SIM_PREP_DIR / "character_cast.json"

DOWNLOADABLE_FILES = {
    "upload_document.md": SIM_PREP_DIR / "upload_document.md",
    "reality_seed.md": SIM_PREP_DIR / "reality_seed.md",
    "simulation_config.json": SIM_PREP_DIR / "simulation_config.json",
    "event_seeds.json": SIM_PREP_DIR / "event_seeds.json",
    "preflight_report.md": SIM_PREP_DIR / "preflight_report.md",
    "character_cast.json": CAST_FILE,
}


# ─── PHASE 1: INGEST ────────────────────────────────────────────────────────

@prep_bp.route("/parse", methods=["POST"])
def parse_doc():
    """Accept plain text content of a doc; return word and char count."""
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"error": "No content provided"}), 400
    words = len(content.split())
    chars = len(content)
    return jsonify({"word_count": words, "char_count": chars})


# ─── PHASE 2: CAST ──────────────────────────────────────────────────────────

@prep_bp.route("/cast", methods=["GET"])
def get_cast():
    """Return the current character_cast.json."""
    if not CAST_FILE.exists():
        return jsonify({"error": "character_cast.json not found"}), 404
    with open(CAST_FILE, "r", encoding="utf-8") as f:
        cast = json.load(f)
    return jsonify(cast)


@prep_bp.route("/cast", methods=["POST"])
def save_cast():
    """Save an updated character_cast.json (from UI edits)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400
    SIM_PREP_DIR.mkdir(parents=True, exist_ok=True)
    with open(CAST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"status": "saved"})


# ─── PHASE 3: BUILD ─────────────────────────────────────────────────────────

@prep_bp.route("/build", methods=["POST"])
def build_package():
    """
    Run generate_config.py against the cast file, then report the
    sizes of all output files. The actual file-writing was done in
    Phase 3 BUILD; this endpoint is called from the UI to (re)generate
    simulation_config.json and return file statuses.
    """
    if not CAST_FILE.exists():
        return jsonify({"error": "character_cast.json not found — complete CAST phase first"}), 400

    # Run the config generator script
    script = SCRIPTS_DIR / "generate_config.py"
    if not script.exists():
        return jsonify({"error": "generate_config.py not found"}), 500

    try:
        result = subprocess.run(
            [sys.executable, str(script), str(CAST_FILE), "--duration", "168", "--language", "es"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Config generation timed out"}), 500

    # Collect file statuses
    files = {}
    for name, path in DOWNLOADABLE_FILES.items():
        if path.exists():
            stat = path.stat()
            files[name] = {
                "exists": True,
                "size_bytes": stat.st_size,
                "size_chars": stat.st_size,  # approximation for text files
            }
        else:
            files[name] = {"exists": False}

    return jsonify({
        "status": "ok" if result.returncode == 0 else "warning",
        "generator_stdout": result.stdout[-2000:] if result.stdout else "",
        "generator_stderr": result.stderr[-500:] if result.stderr else "",
        "files": files,
    })


@prep_bp.route("/files", methods=["GET"])
def list_files():
    """Return current status of all output files."""
    files = {}
    for name, path in DOWNLOADABLE_FILES.items():
        if path.exists():
            files[name] = {
                "exists": True,
                "size_bytes": path.stat().st_size,
            }
        else:
            files[name] = {"exists": False}
    return jsonify({"files": files})


# ─── PHASE 4: PREFLIGHT ─────────────────────────────────────────────────────

@prep_bp.route("/validate", methods=["GET"])
def validate():
    """Run validate_cast.py and return its JSON output."""
    if not CAST_FILE.exists():
        return jsonify({"error": "character_cast.json not found"}), 404

    script = SCRIPTS_DIR / "validate_cast.py"
    if not script.exists():
        return jsonify({"error": "validate_cast.py not found"}), 500

    try:
        result = subprocess.run(
            [sys.executable, str(script), str(CAST_FILE)],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Validation timed out"}), 500

    # validate_cast.py writes JSON to stdout
    try:
        validation = json.loads(result.stdout)
    except json.JSONDecodeError:
        validation = {"status": "ERROR", "raw": result.stdout, "stderr": result.stderr}

    # Add pollution check
    upload_doc = SIM_PREP_DIR / "upload_document.md"
    pollution = []
    if upload_doc.exists():
        import re
        txt = upload_doc.read_text(encoding="utf-8")
        blocked = {
            "Walmart": r"\bWalmart\b",
            "DEA (org)": r"\bDEA\b",
            "Harvard": r"\bHarvard\b",
            "criminal empire": r"\bcriminal empire\b",
            "the siblings": r"the siblings\b",
        }
        for label, pattern in blocked.items():
            hits = len(re.findall(pattern, txt, re.IGNORECASE))
            if hits:
                pollution.append({"pattern": label, "hits": hits, "status": "FAIL"})
        chinese = len(re.findall(r"[\u4e00-\u9fff]", txt))
        if chinese:
            pollution.append({"pattern": "Chinese characters", "hits": chinese, "status": "FAIL"})

    # Cost estimate
    upload_chars = upload_doc.stat().st_size if upload_doc.exists() else 0
    seed_chars = (SIM_PREP_DIR / "reality_seed.md").stat().st_size if (SIM_PREP_DIR / "reality_seed.md").exists() else 0
    avg_agents = 7.5
    rounds = 168
    input_tokens = 3500
    output_tokens = 500
    calls = avg_agents * rounds
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
            "vs_s1_pct": round((cost_total / 450) * 100, 1),
        },
        "overall": "PASS" if (
            validation.get("failures", 1) == 0 and
            len(pollution) == 0 and
            upload_chars < 50000 and
            seed_chars < 5000
        ) else "FAIL",
    })


# ─── DOWNLOAD ───────────────────────────────────────────────────────────────

@prep_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    """Serve a generated output file for download."""
    path = DOWNLOADABLE_FILES.get(filename)
    if not path or not path.exists():
        return jsonify({"error": f"{filename} not found"}), 404
    return send_file(str(path), as_attachment=True, download_name=filename)

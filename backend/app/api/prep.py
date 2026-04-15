"""
MiroFish Prep API — /api/prep

Supports the 4-phase sim-prep studio UI (wizard mode).

New endpoints (slug-based, AI-authoring):
  GET/POST  /api/prep/projects                      project registry
  POST      /api/prep/<slug>/upload                 upload source file (FormData)
  POST      /api/prep/<slug>/analyze                analyze source files
  POST      /api/prep/<slug>/extract-cast           AI cast extraction
  POST      /api/prep/<slug>/generate/<kind>        AI artifact generation
  GET       /api/prep/<slug>/draft/<kind>           read draft file
  POST      /api/prep/<slug>/promote/<kind>         promote draft to canonical
  GET       /api/prep/<slug>/files                  file status for this project

Legacy endpoints (still slug-based, moved from hardcoded oro-verde path):
  POST      /api/prep/<slug>/parse                  word/char count
  GET/POST  /api/prep/<slug>/cast                   read/save cast
  POST      /api/prep/<slug>/build                  run generate_config.py
  GET       /api/prep/<slug>/validate               run validate_cast.py
  GET       /api/prep/<slug>/download/<filename>    serve output file

Backward-compat aliases (no slug, original routes):
  POST /api/prep/parse       → uses oro-verde slug
  GET/POST /api/prep/cast    → uses oro-verde slug
  POST /api/prep/build       → uses oro-verde slug
  GET /api/prep/validate     → uses oro-verde slug
  GET /api/prep/files        → uses oro-verde slug
  GET /api/prep/download/<f> → uses oro-verde slug
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from flask import jsonify, request, send_file

from . import prep_bp
from ..services.project_registry import (
    list_projects,
    get_project,
    create_project,
    project_dir,
    draft_dir,
    sources_dir,
    ensure_project_dirs,
)
from ..utils.pdf_extractor import extract_text_from_bytes

# Repo root — two levels up from this file
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "mirofish-prep"

# Backward-compat default slug for legacy routes
_LEGACY_SLUG = "oro-verde"

_ARTIFACT_FILENAMES = {
    "cast": "character_cast.json",
    "upload-document": "upload_document.md",
    "reality-seed": "reality_seed.md",
    "event-seeds": "event_seeds.json",
    "config": "simulation_config.json",
    "preflight": "preflight_report.md",
    "checklist": "upload_checklist.md",
}

_DOWNLOADABLE = {
    "upload_document.md",
    "reality_seed.md",
    "simulation_config.json",
    "event_seeds.json",
    "preflight_report.md",
    "character_cast.json",
}


def _proj_dir(slug: str) -> Path:
    return project_dir(slug)


def _cast_file(slug: str) -> Path:
    return _proj_dir(slug) / "character_cast.json"


def _draft_artifact_path(slug: str, kind: str) -> Path:
    filename = _ARTIFACT_FILENAMES.get(kind, kind)
    return draft_dir(slug) / filename


def _canonical_artifact_path(slug: str, kind: str) -> Path:
    filename = _ARTIFACT_FILENAMES.get(kind, kind)
    return _proj_dir(slug) / filename


# ─── PROJECT REGISTRY ───────────────────────────────────────────────────────

@prep_bp.route("/projects", methods=["GET"])
def get_projects():
    """Return all registered projects."""
    return jsonify({"projects": list_projects()})


@prep_bp.route("/projects", methods=["POST"])
def post_projects():
    """Create a new project. Returns {slug}."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Project name is required"}), 400
    slug = create_project(name)
    ensure_project_dirs(slug)
    project = get_project(slug)
    return jsonify({"slug": slug, "project": project}), 201


# ─── SOURCE FILE UPLOAD ──────────────────────────────────────────────────────

@prep_bp.route("/<slug>/upload", methods=["POST"])
def upload_source(slug: str):
    """
    Upload a source file (script, bible, PDF) for this project.
    Accepts multipart/form-data with a 'file' field.
    Performs server-side text extraction (fixes PrepView.vue binary-PDF bug).
    """
    ensure_project_dirs(slug)
    src_dir = sources_dir(slug)

    if "file" not in request.files:
        return jsonify({"error": "No file field in request"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = f.filename
    ext = Path(filename).suffix.lower()
    allowed = {".pdf", ".md", ".markdown", ".txt"}
    if ext not in allowed:
        return jsonify({
            "error": f"Unsupported format '{ext}'. MiroFish accepts: PDF, MD, TXT."
        }), 400

    raw_bytes = f.read()
    raw_path = src_dir / filename
    raw_path.write_bytes(raw_bytes)

    try:
        text = extract_text_from_bytes(raw_bytes, filename)
    except Exception as e:
        return jsonify({"error": f"Text extraction failed: {e}"}), 500

    txt_path = src_dir / (Path(filename).stem + ".extracted.txt")
    txt_path.write_text(text, encoding="utf-8")

    return jsonify({
        "filename": filename,
        "char_count": len(text),
        "word_count": len(text.split()),
        "txt_path": str(txt_path.relative_to(REPO_ROOT)),
    })


@prep_bp.route("/<slug>/sources", methods=["GET"])
def list_sources(slug: str):
    """List uploaded source files for a project."""
    src_dir = sources_dir(slug)
    if not src_dir.exists():
        return jsonify({"sources": []})

    sources = []
    for p in sorted(src_dir.iterdir()):
        if p.suffix == ".txt" and ".extracted" in p.name:
            original_stem = p.name.replace(".extracted.txt", "")
            sources.append({
                "filename": original_stem,
                "txt_file": p.name,
                "char_count": len(p.read_text(encoding="utf-8")),
            })
    return jsonify({"sources": sources})


# ─── ANALYZE SOURCES ─────────────────────────────────────────────────────────

@prep_bp.route("/<slug>/analyze", methods=["POST"])
def analyze_sources(slug: str):
    """
    Run analyze_documents.py against all extracted source texts.
    Returns entity counts, pollution risks, and document metadata.
    """
    src_dir = sources_dir(slug)
    if not src_dir.exists():
        return jsonify({"error": "No sources uploaded yet"}), 400

    txt_files = sorted(src_dir.glob("*.extracted.txt"))
    if not txt_files:
        return jsonify({"error": "No extracted text files found — upload sources first"}), 400

    script = SCRIPTS_DIR / "analyze_documents.py"
    if not script.exists():
        return jsonify({"error": "analyze_documents.py not found"}), 500

    try:
        result = subprocess.run(
            [sys.executable, str(script)] + [str(f) for f in txt_files],
            capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Analysis timed out"}), 500

    try:
        analysis = json.loads(result.stdout)
    except json.JSONDecodeError:
        analysis = {"raw": result.stdout, "stderr": result.stderr}

    return jsonify({"analysis": analysis})


# ─── AI CAST EXTRACTION ──────────────────────────────────────────────────────

@prep_bp.route("/<slug>/extract-cast", methods=["POST"])
def extract_cast_ai(slug: str):
    """
    Run AI cast extraction against all source texts for this project.
    Validates the result and retries on failure (max 2 retries).
    Writes output to _draft/character_cast.json.
    """
    src_dir = sources_dir(slug)
    txt_files = sorted(src_dir.glob("*.extracted.txt")) if src_dir.exists() else []
    if not txt_files:
        return jsonify({"error": "No source texts found — upload sources first"}), 400

    source_texts = [f.read_text(encoding="utf-8") for f in txt_files]

    try:
        from ..services.prep_generator import PrepGenerator
        gen = PrepGenerator(slug=slug)
        cast = gen.extract_cast(source_texts)
    except Exception as e:
        return jsonify({"error": f"Cast extraction failed: {e}"}), 500

    draft_path = _draft_artifact_path(slug, "cast")
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(
        json.dumps(cast, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    validation = cast.get("_validation", {})
    return jsonify({
        "cast": cast,
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "agent_count": len(cast.get("mandatory_agents", [])),
        "validation": validation,
        "ready_to_promote": validation.get("failures", 1) == 0,
    })


# ─── AI ARTIFACT GENERATION ──────────────────────────────────────────────────

@prep_bp.route("/<slug>/generate/<kind>", methods=["POST"])
def generate_artifact(slug: str, kind: str):
    """
    Generate a simulation artifact via AI.

    kind: upload-document | reality-seed | event-seeds

    Requires:
      - Source texts uploaded and extracted
      - character_cast.json promoted to canonical (not just draft)

    Writes output to _draft/<kind-filename>.
    """
    valid_kinds = {"upload-document", "reality-seed", "event-seeds"}
    if kind not in valid_kinds:
        return jsonify({"error": f"Unknown kind '{kind}'. Valid: {sorted(valid_kinds)}"}), 400

    # Load source texts
    src_dir = sources_dir(slug)
    txt_files = sorted(src_dir.glob("*.extracted.txt")) if src_dir.exists() else []
    if not txt_files:
        return jsonify({"error": "No source texts found — upload sources first"}), 400
    source_texts = [f.read_text(encoding="utf-8") for f in txt_files]

    # Load canonical cast (must be promoted before generating other artifacts)
    cast_path = _cast_file(slug)
    if not cast_path.exists():
        return jsonify({
            "error": "character_cast.json not found. Extract and promote cast first."
        }), 400
    cast = json.loads(cast_path.read_text(encoding="utf-8"))

    try:
        from ..services.prep_generator import PrepGenerator
        gen = PrepGenerator(slug=slug)

        if kind == "upload-document":
            result = gen.generate_upload_document(source_texts, cast)
            preview = result[:500]
            char_count = len(result)
            over_limit = char_count > 50_000
        elif kind == "reality-seed":
            result = gen.generate_reality_seed(source_texts, cast)
            preview = result[:500]
            char_count = len(result)
            over_limit = char_count > 5_000
        elif kind == "event-seeds":
            result_list = gen.generate_event_seeds(source_texts, cast)
            result = json.dumps(result_list, ensure_ascii=False, indent=2)
            preview = result[:500]
            char_count = len(result_list)
            over_limit = False

    except Exception as e:
        return jsonify({"error": f"Generation failed: {e}"}), 500

    draft_path = _draft_artifact_path(slug, kind)
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(
        result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return jsonify({
        "kind": kind,
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "preview": preview,
        "char_count": char_count,
        "over_limit": over_limit,
        "ready_to_promote": not over_limit,
    })


# ─── READ DRAFT ──────────────────────────────────────────────────────────────

@prep_bp.route("/<slug>/draft/<kind>", methods=["GET"])
def get_draft(slug: str, kind: str):
    """Read a draft file for preview."""
    draft_path = _draft_artifact_path(slug, kind)
    if not draft_path.exists():
        return jsonify({"error": f"No draft for '{kind}' yet"}), 404

    content = draft_path.read_text(encoding="utf-8")
    is_json = draft_path.suffix == ".json"

    if is_json:
        try:
            parsed = json.loads(content)
            return jsonify({"kind": kind, "content": parsed, "char_count": len(content)})
        except json.JSONDecodeError:
            pass

    return jsonify({"kind": kind, "content": content, "char_count": len(content)})


# ─── PROMOTE DRAFT TO CANONICAL ──────────────────────────────────────────────

@prep_bp.route("/<slug>/promote/<kind>", methods=["POST"])
def promote_draft(slug: str, kind: str):
    """
    Promote a draft artifact to canonical (copy _draft/<file> → <file>).
    The canonical file is what gets validated, downloaded, and uploaded to MiroFish.
    """
    draft_path = _draft_artifact_path(slug, kind)
    if not draft_path.exists():
        return jsonify({"error": f"No draft for '{kind}' to promote"}), 404

    canonical_path = _canonical_artifact_path(slug, kind)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)

    content = draft_path.read_text(encoding="utf-8")
    canonical_path.write_text(content, encoding="utf-8")

    from ..services.project_registry import _iso_now
    return jsonify({
        "promoted": True,
        "kind": kind,
        "path": str(canonical_path.relative_to(REPO_ROOT)),
        "char_count": len(content),
        "promoted_at": _iso_now(),
    })


# ─── FILE STATUS ─────────────────────────────────────────────────────────────

@prep_bp.route("/<slug>/files", methods=["GET"])
def list_project_files(slug: str):
    """Return status of all canonical output files for this project."""
    d = _proj_dir(slug)
    draft = draft_dir(slug)

    def file_status(path: Path, draft_path: Optional[Path] = None) -> dict:
        entry = {"exists": path.exists()}
        if path.exists():
            entry["size_bytes"] = path.stat().st_size
        if draft_path and draft_path.exists():
            entry["has_draft"] = True
            entry["draft_size_bytes"] = draft_path.stat().st_size
        else:
            entry["has_draft"] = False
        return entry

    return jsonify({
        "slug": slug,
        "files": {
            "character_cast.json": file_status(
                d / "character_cast.json", draft / "character_cast.json"
            ),
            "upload_document.md": file_status(
                d / "upload_document.md", draft / "upload_document.md"
            ),
            "reality_seed.md": file_status(
                d / "reality_seed.md", draft / "reality_seed.md"
            ),
            "simulation_config.json": file_status(
                d / "simulation_config.json", draft / "simulation_config.json"
            ),
            "event_seeds.json": file_status(
                d / "event_seeds.json", draft / "event_seeds.json"
            ),
            "preflight_report.md": file_status(d / "preflight_report.md"),
            "upload_checklist.md": file_status(d / "upload_checklist.md"),
        },
    })


# Helper for Optional type hint inside function
from typing import Optional


# ─── LEGACY ENDPOINTS (slug-based) ───────────────────────────────────────────

@prep_bp.route("/<slug>/parse", methods=["POST"])
def parse_doc_slug(slug: str):
    """Accept plain text content; return word and char count."""
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"error": "No content provided"}), 400
    return jsonify({"word_count": len(content.split()), "char_count": len(content)})


@prep_bp.route("/<slug>/cast", methods=["GET"])
def get_cast_slug(slug: str):
    """Return the current character_cast.json for this project."""
    cast_path = _cast_file(slug)
    if not cast_path.exists():
        return jsonify({"error": "character_cast.json not found"}), 404
    return jsonify(json.loads(cast_path.read_text(encoding="utf-8")))


@prep_bp.route("/<slug>/cast", methods=["POST"])
def save_cast_slug(slug: str):
    """Save an updated character_cast.json (from UI manual edits)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400
    cast_path = _cast_file(slug)
    cast_path.parent.mkdir(parents=True, exist_ok=True)
    cast_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return jsonify({"status": "saved"})


@prep_bp.route("/<slug>/build", methods=["POST"])
def build_package_slug(slug: str):
    """
    Run generate_config.py against the cast file, return file statuses.
    Reads duration/language from request body or defaults to 168h/es.
    """
    cast_path = _cast_file(slug)
    if not cast_path.exists():
        return jsonify({"error": "character_cast.json not found — complete CAST phase first"}), 400

    data = request.get_json(silent=True) or {}
    duration = str(data.get("duration", 168))
    language = data.get("language", "es")

    script = SCRIPTS_DIR / "generate_config.py"
    if not script.exists():
        return jsonify({"error": "generate_config.py not found"}), 500

    try:
        result = subprocess.run(
            [sys.executable, str(script), str(cast_path),
             "--duration", duration, "--language", language],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Config generation timed out"}), 500

    proj = _proj_dir(slug)
    files = {}
    for name in _DOWNLOADABLE:
        path = proj / name
        files[name] = {
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }

    return jsonify({
        "status": "ok" if result.returncode == 0 else "warning",
        "generator_stdout": result.stdout[-2000:] if result.stdout else "",
        "generator_stderr": result.stderr[-500:] if result.stderr else "",
        "files": files,
    })


@prep_bp.route("/<slug>/validate", methods=["GET"])
def validate_slug(slug: str):
    """Run validate_cast.py and return full preflight report for this project."""
    cast_path = _cast_file(slug)
    if not cast_path.exists():
        return jsonify({"error": "character_cast.json not found"}), 404

    script = SCRIPTS_DIR / "validate_cast.py"
    if not script.exists():
        return jsonify({"error": "validate_cast.py not found"}), 500

    try:
        result = subprocess.run(
            [sys.executable, str(script), str(cast_path)],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Validation timed out"}), 500

    try:
        validation = json.loads(result.stdout)
    except json.JSONDecodeError:
        validation = {"status": "ERROR", "raw": result.stdout, "stderr": result.stderr}

    proj = _proj_dir(slug)
    upload_doc = proj / "upload_document.md"
    pollution = []
    if upload_doc.exists():
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

    upload_chars = upload_doc.stat().st_size if upload_doc.exists() else 0
    seed_path = proj / "reality_seed.md"
    seed_chars = seed_path.stat().st_size if seed_path.exists() else 0

    avg_agents = 7.5
    rounds = 168
    calls = avg_agents * rounds
    cost_input = (calls * 3500 / 1_000_000) * 3.0
    cost_output = (calls * 500 / 1_000_000) * 15.0
    cost_total = cost_input + cost_output + 7.5

    return jsonify({
        "validation": validation,
        "pollution": pollution,
        "pollution_clean": len(pollution) == 0,
        "size_checks": {
            "upload_document_chars": upload_chars,
            "upload_under_50k": upload_chars < 50_000,
            "reality_seed_chars": seed_chars,
            "seed_under_5k": seed_chars < 5_000,
        },
        "cost_estimate": {
            "input_usd": round(cost_input, 2),
            "output_usd": round(cost_output, 2),
            "report_usd": 7.5,
            "total_usd": round(cost_total, 2),
            "vs_s1_pct": round((cost_total / 450) * 100, 1),
        },
        "overall": "PASS" if (
            validation.get("failures", 1) == 0 and
            len(pollution) == 0 and
            upload_chars < 50_000 and
            seed_chars < 5_000
        ) else "FAIL",
    })


@prep_bp.route("/<slug>/download/<filename>", methods=["GET"])
def download_file_slug(slug: str, filename: str):
    """Serve a generated output file for download."""
    if filename not in _DOWNLOADABLE:
        return jsonify({"error": f"'{filename}' is not a downloadable file"}), 404
    path = _proj_dir(slug) / filename
    if not path.exists():
        return jsonify({"error": f"{filename} not found"}), 404
    return send_file(str(path), as_attachment=True, download_name=filename)


# ─── BACKWARD-COMPAT ALIASES (no slug — use oro-verde) ───────────────────────

@prep_bp.route("/parse", methods=["POST"])
def parse_doc():
    return parse_doc_slug(_LEGACY_SLUG)


@prep_bp.route("/cast", methods=["GET"])
def get_cast():
    return get_cast_slug(_LEGACY_SLUG)


@prep_bp.route("/cast", methods=["POST"])
def save_cast():
    return save_cast_slug(_LEGACY_SLUG)


@prep_bp.route("/build", methods=["POST"])
def build_package():
    return build_package_slug(_LEGACY_SLUG)


@prep_bp.route("/files", methods=["GET"])
def list_files():
    return list_project_files(_LEGACY_SLUG)


@prep_bp.route("/validate", methods=["GET"])
def validate():
    return validate_slug(_LEGACY_SLUG)


@prep_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename: str):
    return download_file_slug(_LEGACY_SLUG, filename)

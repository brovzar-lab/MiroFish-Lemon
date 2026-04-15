"""
MiroFish Launch API — /api/launch/<slug>
Bridges the sim-prep package into the MiroFish simulation engine.
Auto-creates a project, uploads source material, and starts the simulation.
"""

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

from ..models.project import ProjectManager, ProjectStatus

logger = logging.getLogger(__name__)

launch_bp = Blueprint("launch", __name__, url_prefix="/api/launch")

# Repo root — three levels up from this file
REPO_ROOT = Path(__file__).resolve().parents[3]


def _prep_dir(slug: str) -> Path:
    return REPO_ROOT / "sim-prep" / slug


@launch_bp.route("/<slug>", methods=["POST"])
def launch_simulation(slug: str):
    """
    Auto-ingest a sim-prep package into MiroFish.

    1. Read upload_document.md → save as project source material
    2. Read reality_seed.md → set as simulation_requirement
    3. Read simulation_config.json → configure simulation params
    4. Create a MiroFish project via ProjectManager
    5. Return project_id for frontend redirect
    """
    prep = _prep_dir(slug)

    # Validate all required files exist
    upload_doc = prep / "upload_document.md"
    reality_seed = prep / "reality_seed.md"
    sim_config = prep / "simulation_config.json"
    cast_file = prep / "character_cast.json"

    missing = []
    for name, path in [
        ("upload_document.md", upload_doc),
        ("reality_seed.md", reality_seed),
        ("simulation_config.json", sim_config),
        ("character_cast.json", cast_file),
    ]:
        if not path.exists():
            missing.append(name)

    if missing:
        return jsonify({
            "error": f"Missing required files: {', '.join(missing)}",
            "hint": "Complete the PREP phase before launching."
        }), 400

    # Read the source material
    source_text = upload_doc.read_text(encoding="utf-8")
    seed_text = reality_seed.read_text(encoding="utf-8")

    # Read project meta for friendly name
    meta_path = prep / "meta.json"
    project_name = slug.replace("-", " ").title()
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text("utf-8"))
            project_name = meta.get("name", project_name)
        except (json.JSONDecodeError, KeyError):
            pass

    try:
        # Create the MiroFish project
        project = ProjectManager.create_project(name=project_name)
        logger.info(f"Created project: {project.project_id} for slug: {slug}")

        # Save source material as extracted text
        ProjectManager.save_extracted_text(project.project_id, source_text)
        project.total_text_length = len(source_text)

        # Set the simulation requirement (reality seed)
        project.simulation_requirement = seed_text

        # Update status
        project.status = ProjectStatus.CREATED

        # Save project state
        ProjectManager.save_project(project)

        logger.info(f"Auto-ingest complete for {slug} → project {project.project_id}")

        return jsonify({
            "status": "ok",
            "project_id": project.project_id,
            "project_name": project_name,
            "source_length": len(source_text),
            "seed_length": len(seed_text),
            "message": f"Project '{project_name}' created. Navigate to the simulation view to build the knowledge graph and start the simulation.",
        })

    except Exception as e:
        logger.error(f"Launch failed for {slug}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@launch_bp.route("/<slug>/status", methods=["GET"])
def launch_status(slug: str):
    """Check if a project has been launched for this slug."""
    prep = _prep_dir(slug)
    has_files = all(
        (prep / f).exists()
        for f in ["upload_document.md", "reality_seed.md", "simulation_config.json", "character_cast.json"]
    )

    # Check if a MiroFish project exists with this name
    slug_name = slug.replace("-", " ").title()
    projects = ProjectManager.list_projects()
    matching = [p for p in projects if p.name == slug_name]

    return jsonify({
        "slug": slug,
        "prep_ready": has_files,
        "project_exists": len(matching) > 0,
        "project_id": matching[0].project_id if matching else None,
        "project_status": matching[0].status.value if matching else None,
    })

"""
Project Registry — manages Prep Studio projects.

Each project maps to a directory under sim-prep/<slug>/ and an entry in
sim-prep/projects.json.  The slug is derived from the project name and is
stable across sessions.

Directory layout created per project:
  sim-prep/<slug>/
    _sources/         raw uploaded source files
    _draft/           AI-generated candidates (not yet promoted)
    character_cast.json         canonical (promoted from _draft/)
    upload_document.md
    reality_seed.md
    simulation_config.json
    event_seeds.json
    preflight_report.md
    upload_checklist.md
"""

import json
import re
import time
from pathlib import Path
from typing import Optional


# Repo root is 4 levels above this file:
# backend/app/services/project_registry.py → backend/app/services/ → backend/app/ → backend/ → repo
REPO_ROOT = Path(__file__).resolve().parents[3]
SIM_PREP_ROOT = REPO_ROOT / "sim-prep"
REGISTRY_FILE = SIM_PREP_ROOT / "projects.json"


def _slugify(name: str) -> str:
    """Convert a project name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "project"


def _load_registry() -> list:
    """Load projects.json, returning empty list if it doesn't exist."""
    if not REGISTRY_FILE.exists():
        return []
    try:
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_registry(projects: list) -> None:
    """Persist projects list to projects.json."""
    SIM_PREP_ROOT.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(
        json.dumps(projects, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_projects() -> list:
    """
    Return all projects, sorted by creation date descending.

    Merges registered projects (projects.json) with any directories under
    sim-prep/ that contain canonical artifacts but were created before the
    registry existed (e.g. the original oro-verde package).

    Each entry: {slug, name, created_at, has_cast, has_upload_doc, has_config, ...}
    """
    projects = _load_registry()
    registered_slugs = {p.get("slug", "") for p in projects}

    # Auto-discover legacy directories that aren't in the registry
    if SIM_PREP_ROOT.exists():
        for child in SIM_PREP_ROOT.iterdir():
            if not child.is_dir() or child.name in registered_slugs:
                continue
            if child.name.startswith(".") or child.name.startswith("_"):
                continue
            # Heuristic: real project directories have at least one canonical file
            if any((child / fname).exists() for fname in (
                "character_cast.json", "upload_document.md", "simulation_config.json"
            )):
                projects.append({
                    "slug": child.name,
                    "name": child.name.replace("-", " ").title(),
                    "created_at": _iso_from_mtime(child),
                    "_legacy": True,
                })

    enriched = [_enrich(p) for p in projects]
    return sorted(enriched, key=lambda p: p.get("created_at", ""), reverse=True)


def get_project(slug: str) -> Optional[dict]:
    """Return a single project by slug, or None if not found.

    Enriches only the requested project (avoids scanning every other project's
    directory for file-status flags).
    """
    for p in _load_registry():
        if p.get("slug") == slug:
            return _enrich(p)

    # Fallback: legacy directory not in registry
    d = project_dir(slug)
    if d.exists() and any((d / f).exists() for f in (
        "character_cast.json", "upload_document.md", "simulation_config.json"
    )):
        return _enrich({
            "slug": slug,
            "name": slug.replace("-", " ").title(),
            "created_at": _iso_from_mtime(d),
            "_legacy": True,
        })

    return None


def _enrich(p: dict) -> dict:
    """Annotate a project entry with file-existence flags and source count."""
    d = project_dir(p.get("slug", ""))
    return {
        **p,
        "has_cast": (d / "character_cast.json").exists(),
        "has_upload_doc": (d / "upload_document.md").exists(),
        "has_reality_seed": (d / "reality_seed.md").exists(),
        "has_config": (d / "simulation_config.json").exists(),
        "has_event_seeds": (d / "event_seeds.json").exists(),
        "has_preflight": (d / "preflight_report.md").exists(),
        "source_count": len(list((d / "_sources").glob("*"))) if (d / "_sources").exists() else 0,
    }


def create_project(name: str) -> str:
    """
    Register a new project. Creates the directory structure and adds to
    projects.json. Returns the slug.

    If a project with the same name already exists, returns its existing slug
    without creating a duplicate.
    """
    slug = _slugify(name)

    projects = _load_registry()

    # Check for existing slug and de-duplicate
    existing_slugs = {p["slug"] for p in projects}
    base_slug = slug
    counter = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Check for same name (case-insensitive)
    for p in projects:
        if p.get("name", "").lower() == name.lower():
            return p["slug"]

    # Create directory structure
    proj_dir = SIM_PREP_ROOT / slug
    (proj_dir / "_sources").mkdir(parents=True, exist_ok=True)
    (proj_dir / "_draft").mkdir(parents=True, exist_ok=True)

    # Register
    projects.append({
        "slug": slug,
        "name": name,
        "created_at": iso_now(),
    })
    _save_registry(projects)

    return slug


def delete_project(slug: str) -> bool:
    """
    Remove a project from the registry (does NOT delete files).
    Returns True if the project was found and removed.
    """
    projects = _load_registry()
    new_projects = [p for p in projects if p["slug"] != slug]
    if len(new_projects) == len(projects):
        return False
    _save_registry(new_projects)
    return True


def project_dir(slug: str) -> Path:
    """Return the canonical directory for a project."""
    return SIM_PREP_ROOT / slug


def draft_dir(slug: str) -> Path:
    """Return the _draft/ subdirectory for a project."""
    return SIM_PREP_ROOT / slug / "_draft"


def sources_dir(slug: str) -> Path:
    """Return the _sources/ subdirectory for a project."""
    return SIM_PREP_ROOT / slug / "_sources"


def ensure_project_dirs(slug: str) -> None:
    """Create _sources/ and _draft/ if they don't exist."""
    (project_dir(slug) / "_sources").mkdir(parents=True, exist_ok=True)
    (project_dir(slug) / "_draft").mkdir(parents=True, exist_ok=True)


def iso_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    import datetime
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_from_mtime(path: Path) -> str:
    """Return a directory's modification time as ISO 8601 string."""
    import datetime
    try:
        ts = path.stat().st_mtime
        return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return iso_now()

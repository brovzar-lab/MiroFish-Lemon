"""Tests for the film-native report changes (structure + wired config)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Config
from app.services.report_agent import (
    ReportAgent, ReportManager, ReportOutline, ReportSection,
    PLAN_SYSTEM_PROMPT,
)


def outline():
    return ReportOutline(
        title="Informe de Prueba",
        summary="resumen",
        sections=[ReportSection(title="Arcos de Personaje", content="")],
    )


def test_clean_section_preserves_h3_subsections():
    content = "Intro paragraph.\n\n### Benjamín: el heredero\n\nSu arco se rompe.\n\n#### demasiado profundo\n\ntexto"
    cleaned = ReportManager._clean_section_content(content, "Arcos de Personaje")
    assert "### Benjamín: el heredero" in cleaned
    # H4 still demoted to bold
    assert "#### demasiado profundo" not in cleaned
    assert "**demasiado profundo**" in cleaned


def test_clean_section_still_strips_duplicate_title():
    content = "## Arcos de Personaje\n\nBody text."
    cleaned = ReportManager._clean_section_content(content, "Arcos de Personaje")
    assert "## Arcos de Personaje" not in cleaned
    assert "Body text." in cleaned


def test_post_process_preserves_h3():
    md = (
        "# Informe de Prueba\n\n## Arcos de Personaje\n\n"
        "### La caída de Karla\n\ntexto\n\n#### micro\n\nmas texto"
    )
    out = ReportManager._post_process_report(md, outline())
    assert "### La caída de Karla" in out
    assert "#### micro" not in out


def test_plan_prompt_is_film_aware():
    assert "CHARACTER-BY-CHARACTER" in PLAN_SYSTEM_PROMPT
    assert "STORY DEPARTMENT" in PLAN_SYSTEM_PROMPT
    # Section range raised
    assert "最多7个" in PLAN_SYSTEM_PROMPT


def test_report_agent_knobs_wired_to_config():
    assert ReportAgent.MAX_TOOL_CALLS_PER_SECTION == Config.REPORT_AGENT_MAX_TOOL_CALLS
    assert Config.REPORT_AGENT_MAX_TOKENS >= 8192
    import inspect
    src = inspect.getsource(ReportAgent._generate_section_react)
    assert "Config.REPORT_AGENT_MAX_TOKENS" in src
    assert "max_tokens=4096" not in src

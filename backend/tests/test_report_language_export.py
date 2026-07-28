"""Tests for the report language fix and export improvements.

Covers:
1. Locale defaults to English (not Chinese) outside a request context.
2. set_locale() on a background thread is honored.
3. Languages advertised in languages.json (es, fr, pt...) are reachable even
   without a full UI translation file.
4. The report agent's prompt assembly injects the language instruction.
5. Project model round-trips the new `language` field.
6. Download filename is derived from the report title, not the report id.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.locale import get_locale, set_locale, get_language_instruction
from app.models.project import Project, ProjectStatus


def test_get_locale_defaults_to_english_off_request():
    set_locale(None)  # clear any thread-local from other tests
    import app.utils.locale as loc
    if hasattr(loc._thread_local, 'locale'):
        del loc._thread_local.locale
    assert get_locale() == 'en'


def test_set_locale_thread_local_spanish():
    set_locale('es')
    assert get_locale() == 'es'
    assert 'español' in get_language_instruction().lower()
    del sys.modules['app.utils.locale']._thread_local.locale


def test_registry_language_without_translation_file_is_reachable():
    # es has no es.json translation file, only a languages.json entry.
    set_locale('es')
    instruction = get_language_instruction()
    assert '中文' not in instruction
    del sys.modules['app.utils.locale']._thread_local.locale


def test_language_instruction_fallback_is_english():
    set_locale('xx-unknown')
    instruction = get_language_instruction()
    assert 'English' in instruction
    del sys.modules['app.utils.locale']._thread_local.locale


def test_plan_prompt_includes_language_instruction():
    import inspect
    from app.services import report_agent
    src = inspect.getsource(report_agent.ReportAgent.plan_outline)
    assert 'get_language_instruction' in src


def test_section_prompt_includes_language_instruction():
    import inspect
    from app.services import report_agent
    src = inspect.getsource(report_agent.ReportAgent._generate_section_react)
    assert 'get_language_instruction' in src


def test_chat_prompt_includes_language_instruction():
    import inspect
    from app.services import report_agent
    src = inspect.getsource(report_agent.ReportAgent.chat)
    assert 'get_language_instruction' in src


def test_project_language_field_round_trip():
    p = Project(
        project_id='proj_test123',
        name='Test',
        status=ProjectStatus.CREATED,
        created_at='2026-07-28',
        updated_at='2026-07-28',
        language='es',
    )
    d = p.to_dict()
    assert d['language'] == 'es'
    p2 = Project.from_dict(d)
    assert p2.language == 'es'
    # Older saved projects have no language key at all
    d.pop('language')
    p3 = Project.from_dict(d)
    assert p3.language is None


def test_download_filename_from_title():
    from app.api.report import _report_download_name
    assert _report_download_name('El Futuro de los Serrano: Análisis', 'report_abc123') \
        == 'El Futuro de los Serrano - Análisis.md'
    # Falls back to the id when there is no title
    assert _report_download_name('', 'report_abc123') == 'report_abc123.md'
    # Strips path-hostile characters
    assert '/' not in _report_download_name('a/b\\c:d', 'report_x')

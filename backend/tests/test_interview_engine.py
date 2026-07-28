"""Tests for the document wizard's interview engine."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.services.interview_engine import InterviewEngine, QUESTION_BANK


@pytest.fixture
def engine(tmp_path):
    return InterviewEngine(tmp_path / "test-project")


def test_start_skips_uploaded_docs(engine):
    state = engine.start(uploaded_doc_ids=["synopsis"])
    docs = {q["doc"] for q in state["questions"]}
    assert "synopsis" not in docs
    assert "bible" in docs and "protocol" in docs


def test_state_persists_across_instances(engine, tmp_path):
    state = engine.start([])
    engine.answer(state, "b1", "Mexico City, present day.")
    engine2 = InterviewEngine(tmp_path / "test-project")
    reloaded = engine2.load()
    b1 = next(q for q in reloaded["questions"] if q["id"] == "b1")
    assert b1["answer"] == "Mexico City, present day."


def test_next_question_walks_in_order(engine):
    state = engine.start([])
    first = engine.next_question(state)
    assert first["id"] == "b1"
    engine.answer(state, "b1", "somewhere")
    assert engine.next_question(state)["id"] == "b2"


def test_skip_moves_on(engine):
    state = engine.start([])
    engine.answer(state, "b1", skip=True)
    assert engine.next_question(state)["id"] == "b2"


def test_empty_answer_rejected(engine):
    state = engine.start([])
    with pytest.raises(ValueError):
        engine.answer(state, "b1", "   ")


def test_cast_list_expands_per_character_questions(engine):
    state = engine.start([])
    engine.answer(state, "c0", "Chuy, ambitious office worker\nLupe, the auditor of heaven")
    ids = [q["id"] for q in state["questions"]]
    assert "c1_want" in ids and "c1_wound" in ids and "c1_flaw" in ids
    assert "c2_want" in ids
    # Expansion questions come right after c0, before synopsis questions
    assert ids.index("c1_want") < ids.index("s1")
    # Character names parsed correctly
    assert state["characters"][0]["name"] == "Chuy"
    assert state["characters"][1]["name"] == "Lupe"
    # Question text is personalized
    q = next(q for q in state["questions"] if q["id"] == "c1_want")
    assert "Chuy" in q["text"]


def test_cast_list_caps_at_six(engine):
    state = engine.start([])
    engine.answer(state, "c0", "\n".join(f"Char{i}, tag" for i in range(10)))
    assert len(state["characters"]) == 6


def test_progress_reports_percentages(engine):
    state = engine.start(uploaded_doc_ids=["synopsis"])
    engine.answer(state, "b1", "a")
    engine.answer(state, "b2", "b")
    docs = engine.progress(state)
    assert docs["synopsis"]["uploaded"] is True
    assert docs["synopsis"]["percent"] == 100
    assert docs["bible"]["answered"] == 2
    assert 0 < docs["bible"]["percent"] < 100


def test_ready_to_synthesize_threshold(engine):
    state = engine.start([])
    assert engine.ready_to_synthesize(state, "bible") is False
    for qid in ["b1", "b2", "b3"]:
        engine.answer(state, qid, "answer")
    assert engine.ready_to_synthesize(state, "bible") is True  # 3/5 = 60%
    # Uploaded docs are never synthesized
    state2 = engine.start(uploaded_doc_ids=["bible"])
    assert engine.ready_to_synthesize(state2, "bible") is False


def test_synthesis_prompt_contains_answers_and_sources(engine):
    state = engine.start([])
    engine.answer(state, "b1", "A floating bureaucracy above CDMX")
    messages = engine.build_synthesis_prompt(state, "bible", sources_text="EXISTING SYNOPSIS TEXT")
    user = messages[1]["content"]
    assert "A floating bureaucracy above CDMX" in user
    assert "EXISTING SYNOPSIS TEXT" in user
    assert "SHOW BIBLE" in user


def test_approve_writes_source_file_with_authored_header(engine, tmp_path):
    state = engine.start([])
    engine.store_draft(state, "seed", "Simulate the 72 hours after the audit.")
    path = engine.approve(state, "seed")
    content = Path(path).read_text(encoding="utf-8")
    assert content.startswith("# Source: Seed Prompt")
    assert "# Mode: authored" in content
    assert "Simulate the 72 hours" in content
    assert (tmp_path / "test-project" / "sources" / "seed.md").exists()


def test_approve_without_draft_raises(engine):
    state = engine.start([])
    with pytest.raises(ValueError):
        engine.approve(state, "bible")


def test_question_bank_covers_all_docs():
    docs = {q["doc"] for q in QUESTION_BANK}
    assert docs == {"bible", "synopsis", "protocol", "seed", "handoff"}

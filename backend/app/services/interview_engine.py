"""
Interview Engine — the document wizard's core.

Builds the sim-prep source documents through a deterministic Q&A interview
instead of requiring finished uploads. Question banks are film-development
questions (want/wound/flaw interrogation in the style of the repo's
Jen Grisanti agent); the LLM is used only at synthesis time, to turn the
producer's answers into the five source documents the existing pipeline
already consumes (sources/<id>.md).

State lives in sim-prep/<slug>/interview.json so an interview can be
resumed across sessions.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DOC_IDS = ["bible", "synopsis", "protocol", "seed", "handoff"]

# Static question bank. Each question: id, doc, text, example (ghost answer
# shape shown by the UI), optional flag.
QUESTION_BANK: List[Dict[str, Any]] = [
    # Show Bible
    {"id": "b1", "doc": "bible", "text": "Where and when does your story live? Describe the world: place, era, and the corner of it we spend the most time in.",
     "example": "Mexico City, present day. The story lives inside a family-run avocado export empire..."},
    {"id": "b2", "doc": "bible", "text": "What is the premise in one or two sentences? The 'what if' at the center of the story.",
     "example": "What if three siblings discovered the business they inherited was built on..."},
    {"id": "b3", "doc": "bible", "text": "What is the tone and genre? Name two or three reference shows or films and how yours differs.",
     "example": "Grounded crime drama with dark humor. Succession meets Narcos, but from the heirs' point of view..."},
    {"id": "b4", "doc": "bible", "text": "What is the engine of conflict, the thing that keeps generating new stories week after week?",
     "example": "Every episode someone must protect the family's public face while privately..."},
    {"id": "b5", "doc": "bible", "text": "What groups or factions are in tension? Name each side and what it wants.",
     "example": "The family (wants legitimacy), the cartel partner (wants control), the journalists (want the story)..."},
    # Characters — c0 expands dynamically into want/wound/flaw per character
    {"id": "c0", "doc": "protocol", "dynamic": "cast_list",
     "text": "Name your central characters, three to six, one per line, each with a short tag.",
     "example": "Benjamín, the performing heir\nKarla, the strongest person in every room\nIsabela, the one who found the photographs"},
    # Pilot Synopsis
    {"id": "s1", "doc": "synopsis", "text": "Where does the story open, and what is the disruption that kicks everything off?",
     "example": "It opens at the grandmother's funeral. The disruption: a stranger hands Benjamín a ledger..."},
    {"id": "s2", "doc": "synopsis", "text": "What are the two or three major turns or escalations after that?",
     "example": "First turn: the audit is announced. Second: Karla finds out her brother lied..."},
    {"id": "s3", "doc": "synopsis", "text": "What happens if the protagonist fails? What is unrecoverable?",
     "example": "If Benjamín fails, the family name becomes a criminal brand and his sisters..."},
    # Seed Prompt
    {"id": "q1", "doc": "seed", "text": "What do you want the simulation to reveal? Ask it as a question.",
     "example": "What happens in the 72 hours after the audit becomes public? Who breaks first?"},
    {"id": "q2", "doc": "seed", "text": "How much story time should the simulation cover, and what moment ends it?",
     "example": "Three days of story time, ending the moment the family must appear together in public..."},
    # Handoff (optional)
    {"id": "h1", "doc": "handoff", "optional": True,
     "text": "Any producer constraints the simulation must respect? (Optional — skip if none.)",
     "example": "Don't kill any of the siblings. Keep the grandmother dead and off-screen..."},
]

PER_CHARACTER_QUESTIONS = [
    ("want", "What does {name} want that they cannot have?"),
    ("wound", "What wound or piece of backstory drives that want for {name}?"),
    ("flaw", "What flaw gets {name} in their own way under pressure?"),
]

DOC_LABELS = {
    "bible": "Show Bible",
    "synopsis": "Pilot Synopsis",
    "protocol": "Interrogation Protocol",
    "seed": "Seed Prompt",
    "handoff": "Handoff Doc",
}

SYNTH_SYSTEM = (
    "You are a senior development executive writing internal source documents "
    "for a multi-agent story simulation. Write ONLY from the producer's "
    "interview answers and any uploaded material provided. Do not invent "
    "named characters, companies, or institutions that the producer did not "
    "mention. Where you must infer connective tissue, stay generic. Write in "
    "clean Markdown prose. Never use real-world organization names."
)

SYNTH_PROMPTS = {
    "bible": (
        "Write a SHOW BIBLE (800-1400 words) with sections: World, Premise, "
        "Tone & References, Engine of Conflict, Factions & Tensions. Base it "
        "on these interview answers:\n\n{answers}\n\n{sources_block}"
    ),
    "synopsis": (
        "Write a PILOT SYNOPSIS (500-900 words) narrating the opening, the "
        "major escalations, and the stakes of failure, in present tense. "
        "Interview answers:\n\n{answers}\n\n{sources_block}"
    ),
    "protocol": (
        "Write an INTERROGATION PROTOCOL: one section per character with "
        "subsections Want, Wound, Flaw, and a 2-3 sentence 'Under Pressure' "
        "synthesis of how the flaw will surface. Characters and answers:\n\n"
        "{answers}\n\n{sources_block}"
    ),
    "seed": (
        "Write a SEED PROMPT (200-450 words): a single tight simulation "
        "requirement describing what the simulation should explore, the "
        "colliding forces, the time horizon, and the question it must answer. "
        "Interview answers:\n\n{answers}\n\n{sources_block}"
    ),
    "handoff": (
        "Write a short HANDOFF DOC of producer constraints and notes for the "
        "simulation operator, as a bulleted list. Interview answers:\n\n"
        "{answers}\n\n{sources_block}"
    ),
}

MAX_SOURCE_CONTEXT = 20_000


class InterviewEngine:
    """Deterministic interview state machine over sim-prep/<slug>/interview.json."""

    def __init__(self, prep_dir: Path):
        self.prep_dir = Path(prep_dir)
        self.state_path = self.prep_dir / "interview.json"

    # ---------- state ----------

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.state_path.exists():
            return None
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save(self, state: Dict[str, Any]) -> None:
        self.prep_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---------- lifecycle ----------

    def start(self, uploaded_doc_ids: List[str]) -> Dict[str, Any]:
        """Create (or reset) the interview, skipping docs already uploaded."""
        uploaded = set(uploaded_doc_ids or [])
        questions = [
            {**q, "answer": None, "skipped": False}
            for q in QUESTION_BANK
            if q["doc"] not in uploaded
        ]
        state = {
            "status": "active",
            "uploaded_docs": sorted(uploaded),
            "questions": questions,
            "characters": [],
            "drafts": {},
            "approved": {},
        }
        self.save(state)
        return state

    def next_question(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for q in state["questions"]:
            if q["answer"] is None and not q["skipped"]:
                return q
        return None

    def answer(self, state: Dict[str, Any], question_id: str,
               answer: Optional[str] = None, skip: bool = False) -> Dict[str, Any]:
        q = next((x for x in state["questions"] if x["id"] == question_id), None)
        if q is None:
            raise KeyError(f"unknown question: {question_id}")
        if skip:
            q["skipped"] = True
        else:
            if not (answer or "").strip():
                raise ValueError("answer must not be empty")
            q["answer"] = answer.strip()
            if q.get("dynamic") == "cast_list":
                self._expand_characters(state, q)
        self.save(state)
        return state

    def _expand_characters(self, state: Dict[str, Any], cast_q: Dict[str, Any]) -> None:
        """Parse the cast-list answer and append want/wound/flaw questions."""
        names = []
        for line in cast_q["answer"].splitlines():
            line = line.strip().lstrip("-•*0123456789. ")
            if not line:
                continue
            name = re.split(r"[,:—–(]| - ", line, maxsplit=1)[0].strip()
            if name:
                names.append({"name": name, "tag": line[len(name):].strip(" ,:-")})
        names = names[:6]
        state["characters"] = names
        insert_at = state["questions"].index(cast_q) + 1
        new_qs = []
        for i, ch in enumerate(names):
            for key, template in PER_CHARACTER_QUESTIONS:
                new_qs.append({
                    "id": f"c{i + 1}_{key}",
                    "doc": "protocol",
                    "text": template.format(name=ch["name"]),
                    "example": "",
                    "answer": None,
                    "skipped": False,
                })
        state["questions"][insert_at:insert_at] = new_qs

    # ---------- progress ----------

    def progress(self, state: Dict[str, Any]) -> Dict[str, Any]:
        docs: Dict[str, Any] = {}
        for doc_id in DOC_IDS:
            qs = [q for q in state["questions"] if q["doc"] == doc_id]
            uploaded = doc_id in state.get("uploaded_docs", [])
            answered = [q for q in qs if q["answer"] is not None]
            pct = 100 if uploaded else (
                int(100 * len(answered) / len(qs)) if qs else 0
            )
            docs[doc_id] = {
                "label": DOC_LABELS[doc_id],
                "uploaded": uploaded,
                "questions": len(qs),
                "answered": len(answered),
                "percent": pct,
                "draft": doc_id in state.get("drafts", {}),
                "approved": bool(state.get("approved", {}).get(doc_id)),
            }
        return docs

    def ready_to_synthesize(self, state: Dict[str, Any], doc_id: str) -> bool:
        if doc_id in state.get("uploaded_docs", []):
            return False
        qs = [q for q in state["questions"] if q["doc"] == doc_id]
        answered = [q for q in qs if q["answer"] is not None]
        if not qs:
            return False
        required = [q for q in qs if not q.get("optional")]
        required_answered = [q for q in required if q["answer"] is not None]
        # At least 60% of required questions answered
        return bool(required) and len(required_answered) * 10 >= len(required) * 6 or (
            not required and bool(answered)
        )

    # ---------- synthesis ----------

    def build_synthesis_prompt(self, state: Dict[str, Any], doc_id: str,
                               sources_text: str = "") -> List[Dict[str, str]]:
        qs = [q for q in state["questions"]
              if q["doc"] == doc_id and q["answer"] is not None]
        answers = "\n\n".join(f"Q: {q['text']}\nA: {q['answer']}" for q in qs)
        sources_block = ""
        if sources_text:
            sources_block = (
                "Uploaded material to stay consistent with (excerpt):\n\n"
                + sources_text[:MAX_SOURCE_CONTEXT]
            )
        user = SYNTH_PROMPTS[doc_id].format(answers=answers, sources_block=sources_block)
        return [
            {"role": "system", "content": SYNTH_SYSTEM},
            {"role": "user", "content": user},
        ]

    def store_draft(self, state: Dict[str, Any], doc_id: str, text: str) -> None:
        state.setdefault("drafts", {})[doc_id] = text
        state.setdefault("approved", {})[doc_id] = False
        self.save(state)

    def approve(self, state: Dict[str, Any], doc_id: str) -> str:
        """Write the approved draft into sources/<doc_id>.md and return the path."""
        draft = state.get("drafts", {}).get(doc_id)
        if not draft:
            raise ValueError(f"no draft to approve for {doc_id}")
        sources_dir = self.prep_dir / "sources"
        sources_dir.mkdir(parents=True, exist_ok=True)
        header = (
            f"# Source: {DOC_LABELS[doc_id]}\n"
            f"# File: authored-{doc_id}.md\n"
            f"# ID: {doc_id}\n"
            f"# Mode: authored\n\n"
        )
        path = sources_dir / f"{doc_id}.md"
        path.write_text(header + draft, encoding="utf-8")
        state["approved"][doc_id] = True
        self.save(state)
        return str(path)

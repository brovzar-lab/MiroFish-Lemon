# Oro Verde S2 Re-Run — Handoff

**Date:** 2026-04-14
**Previous session:** Built `/mirofish-prep` skill, completed Phase 1 INGEST, awaiting Phase 2 decisions.

---

## THE SITUATION IN ONE PARAGRAPH

Lemon Studios is running a MiroFish multi-agent narrative simulation for "Oro Verde" (premium narco-family drama, 3 Serrano siblings, Benjamín/Karla/Isabela, after grandmother Carmen dies). The first simulation (S1, ~1 week ago) burned $450 and crashed at round 134/168 because MiroFish generated 27 agents and only 3 were actual named characters — the other 19 were junk like `walmart_999`, `senators_884`, `serrano_siblings_655`, `criminal_empire_588`, `grandmother_791` (a dead person), plus duplicates (`javier_339` + `javier_cordero_320`) and hallucinated names (`nesto_vega_698` should have been Ernesto or Emilio Vega). Key characters like Benjamín, Isabela, Don Ezequiel, Emilio Vega never got agents. We built a reusable Claude Code skill called `/mirofish-prep` to prevent this from happening again, and we're now re-running Oro Verde with it. We just finished Phase 1 (INGEST) and I was waiting for the user to approve choices before moving to Phase 2 (CAST).

---

## WHAT EXISTS NOW (all committed to main)

### The /mirofish-prep skill — 8 files, 5 commits

```
17aa492 feat: add /mirofish-prep Claude Code skill — 4-phase simulation packager
09da106 feat: add validation rules, blocked patterns, and checklist template
ed1c875 feat: add config generator with role archetypes and cost controls
69ebafc feat: add cast validator with Oro Verde post-mortem rules
8d250b3 feat: add document analyzer for mirofish-prep skill
```

**Files:**
- `.claude/commands/mirofish-prep.md` — the skill (4-phase pipeline: INGEST → CAST → BUILD → PREFLIGHT)
- `scripts/mirofish-prep/analyze_documents.py` — char count, entity scan, pollution risk detection
- `scripts/mirofish-prep/validate_cast.py` — blocks all 29 S1 failure modes (generic nouns, orgs, dead chars, duplicates, hallucinations, first-name-only)
- `scripts/mirofish-prep/generate_config.py` — produces simulation_config.json with hardcoded cost controls (`message_window_size=50`, `token_limit=150000`)
- `scripts/mirofish-prep/templates/character_archetypes.json` — 15 role archetypes (journalist, cartel_patriarch, activist, etc.)
- `scripts/mirofish-prep/templates/upload_checklist.md` — operator checklist template
- `scripts/mirofish-prep/reference/blocked_entity_patterns.json` — block list
- `scripts/mirofish-prep/reference/validation_rules.json` — 12 preflight rules

### Supporting docs
- `mirofishlemon.md` — full S1 post-mortem (all 29 failure modes documented)
- `docs/superpowers/specs/2026-04-13-mirofish-prep-skill-design.md` — spec
- `docs/superpowers/plans/2026-04-13-mirofish-prep-skill.md` — implementation plan

---

## WHERE WE ARE IN THE PIPELINE

**Status: Phase 1 INGEST just completed. Awaiting user decisions to proceed to Phase 2 CAST.**

### Phase 1 INGEST results

Ran `python3 scripts/mirofish-prep/analyze_documents.py` on 5 files in `Billy Agents/Billy Docs for Mirofish/`:

| File | Chars | Type |
|------|-------|------|
| OV MIROFISH REALITY SEED V8.md | 55,354 | SHOW_BIBLE (over 50K limit) |
| PILOT SINOPSIS OV V8.txt | 10,326 | SYNOPSIS |
| JEN_GRISANTI_ORO_VERDE_V8_INTERROGATION.md | 29,319 | CHARACTER_BREAKDOWN |
| V8 MF Seed Prompt.md | 2,640 | SIMULATION_PROMPT |
| ORO VERDE 101 V8.1 09_01_26 CLEAN TXT.txt | 50,871 | SCRIPT (over 50K limit) |

**Total: 148,510 chars — 3x over the 50K MiroFish ontology limit.**

**7 HIGH-risk pollution patterns detected:**
- "the siblings" × 43
- "the family" × 24
- "cartel(s)" × 11
- "grandmother" × 9
- "the thief" × 8
- "criminal empire" × 7
- "rival family/cartel" × 7

Plus 12 MEDIUM risks (Walmart ×7, Harvard ×7, Forbes, DEA, senators, governors, etc.)

### Questions I asked the user (awaiting response)

1. **Which files to use?** Recommended: Bible + Synopsis + Interrogation + Seed Prompt (skip full pilot script — too heavy, voice can come from Interrogation)
2. **Strategy for 50K limit?** Recommended: Synthesize a curated upload doc, stripping all pollution
3. **Language?** Recommended: Spanish
4. **Duration?** Recommended: 168 hours (matches S1 for comparison)

---

## THE CAST WE ALREADY KNOW (from the show bible)

Use this to pre-populate the Phase 2 CAST table. All names must be FULL names (first + last), never generics.

### PRINCIPAL (drives plot — must all be agents)
| # | Name | Role | Stance | Archetype |
|---|------|------|--------|-----------|
| 1 | Benjamín Serrano | Middle sibling, CEO-performer, 3w2/ENFJ | protagonist | ceo_executive |
| 2 | Karla Serrano | Oldest sibling, armored protector, 8w7/ENTJ | protagonist | cartel_patriarch |
| 3 | Isabela Serrano | Youngest sibling, investigator from inside, 7w6/ENFP | protagonist | investigator |
| 4 | Don Ezequiel Antona | Criminal structure behind Grupo Serrano, 8w9/INTJ | antagonist | cartel_patriarch |
| 5 | Javier Cordero | Embedded CFO, Don Ezequiel's operative, 5w6/INTP | antagonist | cfo_analyst |
| 6 | Ingrid Cervantes | Investigative journalist, Karla's ex, 1w9/INTJ | opposing | journalist |
| 7 | Emilio Vega | Son of murdered Ernesto, lawyer-investigator, 9w8/INFP | opposing | investigator |
| 8 | Lucía Suárez | Environmental activist, Benjamín's conscience, 1w2/ENFJ. SECRET: Don Ezequiel's estranged niece | opposing | activist |

### SUPPORTING (drives subplots — candidates for agents)
| # | Name | Role | Stance |
|---|------|------|--------|
| 9 | Valeria Luna | Benjamín's wife, architect, ISFJ, arrives at hacienda | neutral |
| 10 | Gabriela Ruiz | Hacienda housekeeper, served Carmen 40 years, holds secrets | supportive |
| 11 | Reynaldo | The thief hired by the siblings, has the blue folder, 6w5 | neutral |
| 12 | Padre Mendoza | Priest/mediator figure | neutral |
| 13 | Comandante Ruiz | State police commander | neutral |

### EXCLUDED (dead before simulation start — MUST be in excluded_entities, never as active agents)
| # | Name | Reason |
|---|------|--------|
| — | Carmen Serrano | Died of COPD before pilot. She is the ghost. |
| — | Ernesto Vega | Murdered during pilot theft. |

### REJECTED (found in text, blocked from becoming agents)
- "the siblings" / "Serrano siblings" → use Benjamín, Karla, Isabela individually
- "the family" / "Serrano family" → use individual names
- Walmart, Amazon, Netflix, Forbes, DEA, ESG → replace with generic descriptions
- "criminal empire" / "narco operation" → replace with "the operation"
- "grandmother" → use "Carmen Serrano [DECEASED]"
- "the thief" → use Reynaldo (his actual name)
- Harvard → "top US business school"

---

## PHASE 2, 3, 4 — WHAT STILL NEEDS TO HAPPEN

### PHASE 2: CAST
1. Present the cast table (above) to the user for approval
2. Ask: promote minor to agents? (default: no, keep Reynaldo as agent for plot relevance)
3. Ask: allow MiroFish to generate additional background agents? (default: up to 3 extras)
4. Write `sim-prep/oro-verde/character_cast.json` with approved cast, including `excluded_entities` for Carmen + Ernesto

### PHASE 3: BUILD
1. **upload_document.md** — Synthesize from Bible + Synopsis + Interrogation, under 50K chars, in English. Apply these transformations:
   - Start with CHARACTER INDEX header listing all mandatory agents
   - Replace "Walmart" → "a major retail buyer"; "DEA" → "a federal agency"; "Harvard" → "a top business school"
   - Replace "the siblings" → "Benjamín, Karla, and Isabela"
   - Replace "the family" → specific names
   - Mark "Carmen Serrano [DECEASED]" everywhere
   - Strip "criminal empire", "narco operation" → "the operation"
2. **reality_seed.md** — ~2-3K char narrative prompt (can adapt V8 Seed Prompt but rewrite to name individuals, not groups)
3. **simulation_config.json** — `python3 scripts/mirofish-prep/generate_config.py sim-prep/oro-verde/character_cast.json --duration 168 --language es`, then fill in simulation_requirement, initial_posts (6-8 assigned to specific agents), hot_topics (10-12 English keywords), narrative_direction
4. **event_seeds.json** — Key beats: Valeria's arrival, Emilio arriving in Michoacán, Ingrid's next article, Isabela finding the 1982 photo

### PHASE 4: PREFLIGHT
1. `python3 scripts/mirofish-prep/validate_cast.py sim-prep/oro-verde/character_cast.json`
2. Verify: upload doc <50K, no Chinese anywhere, message_window_size=50, token_limit=150000, all mandatory agents present, Carmen/Ernesto ONLY in excluded
3. Cost estimate (compare to S1 $450)
4. Generate `preflight_report.md` and filled `upload_checklist.md`
5. Generate optional `test_config.json` (10-round mini test)

---

## CRITICAL CONTEXT YOU MUST REMEMBER

1. **The V8 materials are the SAME docs that failed the first time.** The docs are excellent. The problem was never the writing — it was the prep. Zep Cloud (MiroFish's entity extractor) sees "Walmart" in the upload doc → creates a Walmart entity → profile generator turns it into a posting agent. The BUILD phase's document curation is the single most important step.

2. **MiroFish's ontology prompt is 100% Chinese.** The entity type generation can return Chinese labels. The upload checklist warns the user to verify entity types come back in English PascalCase. If they don't, re-run ontology generation.

3. **MiroFish has NO checkpoint/resume.** If the sim crashes mid-run, data is in action logs but cannot be resumed — must restart from round 0. Monitor VPS memory (`free -h` on root@187.124.251.98) and cost actively during first 30 rounds.

4. **Cost controls are non-negotiable.** `message_window_size=50`, `token_limit=150000`. Already applied in `backend/scripts/run_parallel_simulation.py` but the config generator hardcodes them too.

5. **VPS:** root@187.124.251.98 — MiroFish backend, LiteLLM proxy → OpenRouter → claude-sonnet-4-6

6. **Oro Verde Pilot Revision rule (from user's memory):** The "algorithm" is GONE. The Serranos themselves are the asset (their face, their name, their 40-year public history). Never reference an algorithm.

---

## PROMPT TO PASTE INTO NEW CLAUDE CODE SESSION

```
I'm continuing work on the Oro Verde S2 re-run for MiroFish. Read these files first in order:

1. /Users/quantumcode/CODE/MIROFISH LEMON/HANDOFF_ORO_VERDE_RERUN.md — the handoff doc (start here)
2. /Users/quantumcode/CODE/MIROFISH LEMON/mirofishlemon.md — full S1 post-mortem (29 failure modes)
3. /Users/quantumcode/CODE/MIROFISH LEMON/.claude/commands/mirofish-prep.md — the /mirofish-prep skill we built
4. /Users/quantumcode/CODE/MIROFISH LEMON/Billy Agents/Billy Docs for Mirofish/V8 MF Seed Prompt.md — simulation requirement
5. /Users/quantumcode/CODE/MIROFISH LEMON/Billy Agents/Billy Docs for Mirofish/OV MIROFISH REALITY SEED V8.md — show bible

We finished Phase 1 INGEST. I need you to:

1. Confirm you understand the handoff doc
2. Pick up at Phase 2 CAST: present the cast table (pre-populated from the show bible, see handoff doc) and get my approval
3. Then proceed through Phase 3 BUILD (generate sim-prep/oro-verde/ files) and Phase 4 PREFLIGHT (run validate_cast.py, produce preflight report)

My preferences for Phase 1 (assume these unless I say otherwise):
- Use Bible + Synopsis + Interrogation + Seed Prompt (skip the pilot script — voice comes from Interrogation)
- Synthesize a curated upload doc under 50K chars
- Language: Spanish
- Duration: 168 hours (match S1 for comparison)

Do NOT re-upload or re-run anything on the MiroFish VPS yet. Just build the sim-prep/oro-verde/ package. I'll upload manually when it's validated.
```

---

## WHAT'S IN THE WORKING DIRECTORY (git status context)

- **Clean commits** on `main`: all 6 commits from the skill build
- **Unstaged modifications** (pre-existing, not from this session): `backend/app/utils/credit_check.py`, `backend/scripts/run_parallel_simulation.py`, `backend/scripts/run_reddit_simulation.py`, `backend/scripts/run_twitter_simulation.py`, `frontend/src/components/Step3Simulation.vue`, `frontend/src/views/SimulationRunView.vue` — these already had the cost controls applied from an earlier session
- **Deleted but not committed** (user tidied workspace): `LICENSE`, old V3/V4 Reality Seed files, V8.1 pilot script at root, old pilot synopsis files
- **Untracked**: `Billy Agents/` (the source material, intentionally untracked), `oro-verde-sim-export/` (S1 data dump from VPS), `mirofishlemon.md`, `report_715af78f0b5a/`, design screenshots from an unrelated exercise

Nothing to commit before handoff — everything from the skill build is already committed.

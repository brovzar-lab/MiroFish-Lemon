# MiroFish Prep Skill — Design Spec

**Date:** 2026-04-13
**Project:** MiroFish Lemon (Lemon Studios)
**Skill name:** `mirofish-prep`
**Model:** Claude Sonnet 4.6 (latest — `claude-sonnet-4-6`)

---

## Problem

MiroFish's simulation pipeline (Steps 1-5) has a critical weakness: the profile generator (Step 2) creates agents by extracting entity mentions from uploaded documents via Zep's internal NLP. This is a black box — if your script mentions "Walmart," Zep creates a Walmart entity node, and MiroFish turns it into a posting agent. The Oro Verde S1 run wasted ~$450 because 19 of 27 agents were junk (generic nouns, organizations, dead characters, duplicates) while key characters like Benjamín Serrano never got individual agents.

The root cause: no human checkpoint between document upload and simulation execution. The AI made all agent-casting decisions autonomously and got them catastrophically wrong.

## Solution

A Claude Code skill (`/mirofish-prep`) that helps Lemon Studios producers prepare simulation materials before uploading to MiroFish. It runs as a 4-phase pipeline with human approval checkpoints between each phase. The skill:

1. Reads your existing creative materials (scripts, treatments, bibles, character breakdowns)
2. Extracts and classifies every character for your approval
3. Generates curated upload documents engineered to produce clean Zep entities
4. Runs validation and cost estimation before you commit money

**Scope:** Lemon Studios film and TV projects only — narrative fiction with a defined cast. Not general-purpose opinion simulation.

**Interaction model:** Creative brief — the user dumps materials and a short description, the skill digests and comes back with structured output and decisions at each phase.

**Output:** A directory of ready-to-upload files + a step-by-step checklist for the MiroFish UI. No MiroFish code changes required.

---

## Architecture

```
User invokes /mirofish-prep
        │
        ▼
┌─────────────┐     approval     ┌──────────┐     approval     ┌─────────┐     approval     ┌────────────┐
│  PHASE 1    │ ───────────────► │ PHASE 2  │ ───────────────► │ PHASE 3 │ ───────────────► │  PHASE 4   │
│  INGEST     │                  │  CAST    │                  │  BUILD  │                  │  PREFLIGHT │
│             │                  │          │                  │         │                  │            │
│ Read files  │                  │ Extract  │                  │ Generate│                  │ Validate   │
│ Analyze     │                  │ chars    │                  │ all     │                  │ Estimate   │
│ Detect      │                  │ Classify │                  │ output  │                  │ cost       │
│ entities    │                  │ Approve  │                  │ files   │                  │ Final gate │
│ Flag risks  │                  │ cast     │                  │         │                  │            │
└─────────────┘                  └──────────┘                  └─────────┘                  └────────────┘
                                                                                                  │
                                                                                                  ▼
                                                                                        sim-prep/<project>/
                                                                                        ├── upload_document.md
                                                                                        ├── reality_seed.md
                                                                                        ├── character_cast.json
                                                                                        ├── simulation_config.json
                                                                                        ├── event_seeds.json
                                                                                        ├── preflight_report.md
                                                                                        ├── upload_checklist.md
                                                                                        └── test_config.json
```

Each phase ends with multiple-choice decisions with recommended defaults. The user can accept defaults quickly or override specific choices.

---

## Phase 1: INGEST

### Input
- File paths or directory path provided by user
- Short creative brief describing the project

### Behavior
1. Scan for PDF, MD, and TXT files (MiroFish's accepted formats — no DOCX)
2. Read and parse all files (PyMuPDF for PDF, plain read for MD/TXT)
3. Detect document type by content analysis (script format, prose treatment, character list, pitch bible, synopsis)
4. Count total characters per file
5. Scan for named entities: people, organizations, locations
6. Identify dead characters (referenced in past tense, marked deceased, die in narrative)
7. Flag entity pollution risks: organizations, abstract concepts, group nouns that Zep will extract as entities
8. Flag files exceeding MiroFish's 50K char ontology analysis limit

### Output
Summary report showing:
- File inventory with char counts and detected types
- Named entity preview (characters, organizations, locations, dead characters)
- Warnings (size limits, pollution risks)
- Decisions with recommended defaults:
  1. **Which files to include** — checkboxes, all checked by default
  2. **Document strategy for 50K limit** — how to handle overflow if total exceeds 50K
  3. **Simulation language** — Spanish / English / Mixed (default: Spanish for Latin American projects)
  4. **Simulation length** — 72h / 168h / 336h / Custom (default: 168h)

### Read-only
This phase does not create or modify any files.

---

## Phase 2: CAST

### Input
- Parsed materials from INGEST
- User's file selection and configuration choices

### Behavior
1. Extract every named character from the approved materials
2. Classify each by narrative weight:
   - **Principal** — appears in 10+ scenes or drives main plot
   - **Supporting** — appears in 3-9 scenes, drives subplots
   - **Minor** — mentioned but not a scene driver
3. Auto-assign stance per character based on narrative context:
   - `protagonist` — drives or supports the central family/mission
   - `antagonist` — actively works against protagonists
   - `opposing` — external pressure (investigators, activists, rivals)
   - `neutral` — observers, mediators, wildcards
   - `supportive` — allies, enablers, loyalists
4. Auto-exclude dead characters from active agent pool (keep as referenced entities)
5. Reject organizations and abstract nouns — show what was blocked and why
6. Check for duplicates (same character referenced by different names)
7. Present cast table with editable fields

### Output
Cast table in three tiers (Principal / Supporting / Minor) plus Excluded and Rejected sections. Each character row shows: name, role, stance, agent checkbox.

Decisions:
1. **Cast correct?** — Yes / Add character / Remove or change someone
2. **Include minor cast as agents?** — No (recommended) / Yes all / Pick specific ones
3. **Allow background agents?** — Up to 6 / Up to 3 (recommended) / None

### Iteration
If the user adds, removes, or edits characters, re-present the table until approved. The approved cast becomes `character_cast.json`.

### character_cast.json Schema
```json
{
  "project": "oro-verde-s2",
  "mandatory_agents": [
    {
      "name": "Benjamín Serrano",
      "role": "CEO of Grupo Serrano",
      "stance": "protagonist",
      "activity_level": 0.7,
      "influence_weight": 2.0,
      "active_hours": [9, 10, 11, 14, 15, 16, 19, 20],
      "sentiment_bias": 0.2,
      "posts_per_hour": 0.5,
      "comments_per_hour": 1.0,
      "response_delay_min": 15,
      "response_delay_max": 60
    }
  ],
  "excluded_entities": [
    { "name": "Carmen Serrano", "reason": "deceased_before_simulation" },
    { "name": "Ernesto Vega", "reason": "deceased_before_simulation" }
  ],
  "rejected_entities": [
    { "name": "Grupo Serrano", "reason": "organization" },
    { "name": "Walmart de México", "reason": "organization" },
    { "name": "DEA", "reason": "organization" }
  ],
  "allow_additional_agents": true,
  "max_additional_agents": 3
}
```

Behavioral parameters (activity_level, influence_weight, active_hours, etc.) are pre-calibrated by the skill based on the character's role:
- **Journalists** — high activity, early + late hours, fast response, negative sentiment bias
- **CEOs/executives** — moderate activity, business hours, medium response delay
- **Cartel operators** — moderate activity, late night hours, slow response, negative bias, high influence
- **Activists** — high activity, spread across day, fast response, positive sentiment
- **Artists/creatives** — low-moderate activity, evening hours, variable sentiment

---

## Phase 3: BUILD

### Input
- Approved cast from CAST phase
- File selection and config choices from INGEST phase
- Full parsed text from all approved materials

### Behavior
Generates 5 output files:

#### 1. upload_document.md
A curated document synthesized from the user's approved materials, specifically engineered for clean Zep entity extraction.

Modifications applied:
- **Strip organization names** that would create junk agents. Replace with generic descriptions ("Walmart de México" → "a major retail buyer", "DEA" → "a federal law enforcement agency")
- **Replace group references** with individual names ("the siblings" → "Benjamín, Karla, and Isabela")
- **Mark dead characters** explicitly ("[DECEASED]") so Zep classifies them correctly
- **Add character index header** listing all mandatory agents by name at the top of the document — this primes Zep to create individual entity nodes for each
- **Ensure total length stays under 50K chars** (MiroFish ontology analysis limit)
- **Language: English** — the upload document is always in English regardless of the simulation language setting. This is because Zep's entity extraction produces cleaner individual entity nodes from English text (fewer ambiguities with Spanish noun phrases like "los hermanos Serrano"). The simulation language setting (e.g., Spanish) only affects how agents post during the simulation, configured in simulation_config.json

#### 2. reality_seed.md
The `simulation_requirement` narrative prompt. Written fresh from the user's materials following the structure that worked in Oro Verde S1:
- 2,000-3,000 characters
- Names all key characters individually (never as groups)
- Describes the world state at simulation start
- Identifies 2-3 colliding forces
- Poses open questions for the simulation to answer
- Specifies the report structure (4 thematic sections)

#### 3. character_cast.json
The approved cast from Phase 2 with full behavioral parameters.

#### 4. simulation_config.json
Complete simulation configuration:
- `simulation_id`: auto-generated
- `simulation_requirement`: contents of reality_seed.md
- `time_config`: based on user's duration choice, with sensible defaults for peak/off-peak hours calibrated to the story's timezone
- `agent_configs`: one entry per mandatory agent, behavioral parameters from character_cast.json
- `event_config`: initial_posts (assigned to specific agents), hot_topics (derived from materials), narrative_direction (English, for production team)
- `twitter_config` / `reddit_config`: platform weights (sensible defaults)
- `llm_model`: `claude-sonnet-4-6`
- `llm_base_url`: user's LiteLLM proxy URL (from env or prompted)
- Cost controls enforced:
  - `message_window_size`: 50
  - `token_limit`: 150000

#### 5. event_seeds.json
Optional scheduled narrative events derived from the script's act breaks:
```json
{
  "scheduled_events": [
    {
      "hour": 24,
      "description": "Ingrid publishes Part 1 of investigation",
      "trigger_agent": "Ingrid Cervantes",
      "event_type": "publication",
      "impact": "high"
    }
  ]
}
```

### Output
Shows a summary of each generated file with preview snippets. Decisions:
1. **Upload document correct?** — Yes / Review full text / Change what's included
2. **Reality seed captures right focus?** — Yes / Edit it / Rewrite with different emphasis
3. **Event seeds?** — Use these / Adjust timing / No scheduled events

---

## Phase 4: PREFLIGHT

### Input
All generated files from BUILD phase.

### Behavior
Runs validation checks across four categories. Each check is PASS / WARN / FAIL.

#### Cast Validation
- All mandatory agents have unique individual names → PASS/FAIL
- No generic nouns (senators, cartels, family, woman) → PASS/FAIL
- No organizations as posting agents → PASS/FAIL
- No dead characters in active agent pool → PASS/FAIL
- No duplicate agents (name similarity check — fuzzy match) → PASS/FAIL
- All stances assigned → PASS/FAIL
- Agent count within reasonable limits (≤30) → PASS/WARN/FAIL

#### Document Validation
- Upload document under 50K chars → PASS/FAIL
- File format is PDF/MD/TXT → PASS/FAIL
- Encoding is UTF-8 → PASS/FAIL
- Reality seed under 5K chars → PASS/WARN
- Residual organization mentions in upload doc (entity pollution risk) → PASS/WARN

#### Config Validation
- `message_window_size` is set and ≤ 50 → PASS/FAIL
- `token_limit` is set and ≤ 150000 → PASS/FAIL
- Simulation hours within expected range → PASS/WARN
- LLM model is `claude-sonnet-4-6` → PASS/WARN
- Language is set (not defaulting to Chinese) → PASS/FAIL
- No Chinese text in config, topics, or narrative direction → PASS/FAIL

#### Cost Estimate
Calculated from:
- Agent count × activity levels × rounds = estimated API calls
- Avg tokens per call (bounded by message_window_size/token_limit) × Sonnet pricing
- Report generation cost (separate estimate)
- Comparison to Oro Verde S1 ($450) for context
- Check against user's budget ($200+) → PASS/WARN

#### Preflight Result
- **ALL CLEAR**: 0 failures, warnings acceptable → proceed
- **WARNINGS**: 0 failures, warnings present → proceed with awareness
- **BLOCKED**: 1+ failures → must fix before proceeding

### Output
Full preflight report. Decisions:
1. **Ready to prep for upload?** — Yes / Go back and adjust
2. **Generate mini test config?** — Yes, 10-round test for $2-3 (recommended) / No, straight to full run

### Final Output
On confirmation, writes all files to `sim-prep/<project-slug>/` and generates `upload_checklist.md`:

```markdown
# Upload Checklist — <Project Name>

## Pre-Upload
- [ ] MiroFish backend running on VPS (root@187.124.251.98)
- [ ] LiteLLM proxy running and connected to OpenRouter
- [ ] OpenRouter balance > estimated cost ($XX)
- [ ] VPS memory > 4GB free

## Step 1: Graph Building
- [ ] Create new project in MiroFish UI
- [ ] Upload `upload_document.md`
- [ ] Paste contents of `reality_seed.md` into simulation requirement field
- [ ] Generate ontology
- [ ] Review entity types — should include Person, not Organization/Company for characters

## Step 2: Profile Generation (CRITICAL CHECKPOINT)
- [ ] Generate agent profiles
- [ ] **VERIFY** every name in `character_cast.json` appears as an individual agent
- [ ] **VERIFY** no junk agents (Walmart, senators, family, etc.)
- [ ] **VERIFY** no dead characters as active agents
- [ ] If any check fails: DO NOT PROCEED. Re-run profile generation or manually fix.

## Step 3: Simulation
- [ ] Optional: Run 10-round test first using `test_config.json`
- [ ] Monitor first 10 rounds — cost should be < $0.50/round
- [ ] Monitor VPS memory — should stay under 80% usage
- [ ] Start full 168-hour simulation

## Step 4: Report
- [ ] Generate report after simulation completes
- [ ] Verify report sections match reality_seed.md structure

## Step 5: Post-Simulation
- [ ] Export simulation data to Character Engine (sync-from-mirofish.sh)
- [ ] Update character profiles if simulation revealed new dynamics
```

---

## Skill Implementation

### File Location
```
~/.claude/commands/mirofish-prep.md
```

### Model
The skill runs on **Claude Sonnet 4 (latest)** — `claude-sonnet-4-6`. This is specified in the skill's frontmatter as the model parameter.

### Tools Used
- **Read** — parse user's PDF/MD/TXT files
- **Glob** — find files in user's directory
- **Grep** — scan for entity mentions, character names, organization names
- **Write** — output all generated files to sim-prep/ directory
- **Bash** — PDF text extraction via Python (PyMuPDF/pdfplumber if needed), char counting
- **TodoWrite** — track phase progress

### State Management
The skill maintains state between phases through the conversation context. Each phase's approved output feeds into the next phase. If the user wants to go back and change something (e.g., edit the cast after seeing the BUILD output), the skill re-runs from the changed phase forward.

### Error Handling
- File not found → report which file and ask for corrected path
- PDF extraction fails → report error, suggest converting to TXT/MD
- File too large (>50MB) → reject, suggest trimming
- Unsupported format → list supported formats, suggest conversion
- No characters detected → ask user to provide cast manually (skip to CAST with manual input)

---

## Validation Rules Reference

These rules are derived from the Oro Verde S1 post-mortem (`mirofishlemon.md`) and encode every failure mode encountered:

| Rule | Phase | Severity | What It Catches |
|------|-------|----------|-----------------|
| No generic nouns as agents | CAST, PREFLIGHT | FAIL | "senators", "cartels", "family", "woman" |
| No organizations as agents | CAST, PREFLIGHT | FAIL | "Walmart", "criminal empire", "DEA" |
| No dead characters posting | CAST, PREFLIGHT | FAIL | Carmen Serrano posting on Twitter |
| No duplicate agents | CAST, PREFLIGHT | FAIL | "Javier" + "Javier Cordero" |
| No first-name-only agents | CAST, PREFLIGHT | WARN | "Karla" should be "Karla Serrano" (except legit single names like "Reynaldo") |
| No name hallucinations | CAST, PREFLIGHT | WARN | "Nesto Vega" is a corruption of "Ernesto Vega" / "Emilio Vega" |
| All mandatory chars present | PREFLIGHT | FAIL | Benjamín missing, merged into "Serrano siblings" |
| message_window_size bounded | PREFLIGHT | FAIL | Unbounded context → $3/call → OOM crash |
| token_limit bounded | PREFLIGHT | FAIL | Same as above |
| No Chinese in config | PREFLIGHT | FAIL | Hot topics, narrative direction in wrong language |
| Upload doc under 50K chars | PREFLIGHT | FAIL | Ontology analysis truncation |
| Upload doc stripped of orgs | BUILD | automatic | Prevents Zep from creating org entities |
| Group refs → individual names | BUILD | automatic | "the siblings" → "Benjamín, Karla, and Isabela" |
| Dead chars marked [DECEASED] | BUILD | automatic | Guides Zep classification |
| Character index header | BUILD | automatic | Primes Zep to create individual entity nodes |
| Cost estimate vs budget | PREFLIGHT | WARN | $450 burn prevention |
| Residual org mentions | PREFLIGHT | WARN | Entity pollution risk monitoring |
| Ontology type verification | CHECKLIST | manual | MiroFish ontology prompt is Chinese — verify types come back in English PascalCase |
| Organization type exclusion | CHECKLIST | manual | If Zep creates Organization entity type, verify org entities don't become posting agents |
| No checkpoint/resume warning | CHECKLIST | info | MiroFish cannot resume crashed simulations — monitor actively during first 30 rounds |

---

## Success Criteria

The skill is successful when:
1. Every simulation run uses the full mandatory cast — no missing key characters
2. Zero junk agents (organizations, generics, dead characters) reach the simulation
3. Cost per simulation stays in the $30-75 range (vs. $450 for Oro Verde S1)
4. The user can go from "I have a script" to "files ready for MiroFish" in one Claude Code session
5. The upload checklist catches any remaining issues at the MiroFish UI level
6. The mini test config option lets users validate for $2-3 before committing to a full run

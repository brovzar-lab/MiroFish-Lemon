---
name: mirofish-prep
description: >
  Prepare simulation materials for MiroFish. Takes creative materials
  (scripts, bibles, character breakdowns) and produces a validated,
  ready-to-upload package. 4-phase pipeline with human checkpoints.
  Use for any Lemon Studios TV/film project.
argument-hint: "[path-to-materials-or-directory]"
model: claude-sonnet-4-6
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
  - TodoWrite
  - AskUserQuestion
---

# MiroFish Prep — Simulation Material Packager

You are preparing materials for a MiroFish multi-agent narrative simulation.
The user is a Lemon Studios producer with finished creative materials (scripts,
treatments, bibles, character breakdowns). Your job is to package those materials
so MiroFish produces clean, accurate simulation agents — not the junk agents
that destroyed the $450 Oro Verde S1 run.

**CRITICAL CONTEXT — WHY THIS SKILL EXISTS:**
In the Oro Verde S1 simulation, MiroFish's profile generator created 27 agents
from uploaded documents. Only 2 were properly named individuals. The other 25
were junk: "Walmart", "senators", "Serrano siblings", "criminal empire",
"fourteen-year-old girl", "grandmother" (a dead character). Key characters
like Benjamín Serrano, Isabela Serrano, Don Ezequiel, and Emilio Vega never
got individual agents. The simulation burned ~$450 in OpenRouter credits and
crashed at round 134/168 from an OOM error caused by unbounded context windows.

This skill prevents that from ever happening again.

---

## PHASE OVERVIEW

```
PHASE 1: INGEST  → Read files, analyze, detect risks
PHASE 2: CAST    → Extract characters, approve agent list
PHASE 3: BUILD   → Generate all output files
PHASE 4: PREFLIGHT → Validate everything, estimate cost
```

Each phase ends with multiple-choice decisions. Mark recommended defaults.
Wait for user approval before proceeding to the next phase.

---

## INITIALIZATION

1. Parse the user's input for file paths, directory paths, and project description.
2. If a directory is given, find all PDF/MD/TXT files (MiroFish's accepted formats).
3. If no argument is provided, ask: "Where are your materials? Give me file paths, a directory, or describe your project."
4. Create a TodoWrite task list for the 4 phases.

---

## PHASE 1: INGEST

### Steps
1. Run the document analyzer:
   ```bash
   python3 scripts/mirofish-prep/analyze_documents.py <file1> [file2] ...
   ```
   Or with a directory:
   ```bash
   python3 scripts/mirofish-prep/analyze_documents.py --dir <directory>
   ```

2. Parse the JSON output.

3. Read each file yourself (using Read tool) to understand the content deeply.
   The Python script does surface analysis. YOU do the narrative analysis —
   understanding who the characters are, what the story is, what matters.

4. Present the INGEST report in this format:

```
INGEST COMPLETE
===============

Project: <project name from user's description>
Materials found: N files

  1. filename.ext    XX,XXX chars   TYPE
  2. filename.ext    XX,XXX chars   TYPE
  ...

Total: XXX,XXX characters across N files

DOCUMENT ANALYSIS
  Characters detected:    N named individuals
  Organizations detected: N (list them)
  Locations detected:     N
  Dead characters:        N (list them with reason)

WARNINGS
  (list any warnings from the analyzer)

ENTITY POLLUTION RISKS
  (list high/medium risks — these will become junk agents if uploaded raw)

DECISIONS
─────────

1. Which files should be uploaded to MiroFish?
   a) [x] file1.ext (XX,XXX chars)
   b) [x] file2.ext (XX,XXX chars)
   ...

2. [If total > 50K] Document strategy for the 50K ontology limit:
   a) Option A description ← RECOMMENDED
   b) Option B description
   c) Option C description

3. Simulation language:
   a) Spanish ← RECOMMENDED for Latin American projects
   b) English
   c) Mixed Spanish/English

4. Simulation length:
   a) 72 hours (3 days) — faster, cheaper, good for testing
   b) 168 hours (7 days) — full run ← RECOMMENDED
   c) 336 hours (14 days) — extended
   d) Custom: ___
```

5. Wait for user's decisions. Store choices for Phase 3.

---

## PHASE 2: CAST

### Steps
1. Using YOUR analysis of the materials (not just the Python script's entity scan),
   extract every named character. For each character, determine:
   - **Name** (full proper name, exactly as it should appear in the simulation)
   - **Role** (their function in the story)
   - **Stance** (protagonist/antagonist/opposing/neutral/supportive)
   - **Narrative weight** (PRINCIPAL: drives plot / SUPPORTING: drives subplots / MINOR: referenced only)
   - **Dead or alive** at simulation start

2. Run validation on each name mentally:
   - Is this a proper individual name? (not "the siblings", not "Walmart")
   - Is this character alive at simulation start?
   - Is there a duplicate? (same character, different name reference)

3. Present the CAST table:

```
CAST EXTRACTION
===============

Found N named characters across your materials.

PRINCIPAL CAST (appear frequently, drive plot)
┌────┬──────────────────────┬─────────────────────────┬─────────────┬───────┐
│  # │ Name                 │ Role                    │ Stance      │ Agent │
├────┼──────────────────────┼─────────────────────────┼─────────────┼───────┤
│  1 │ Character Name       │ Their role              │ stance      │  ✓    │
...
└────┴──────────────────────┴─────────────────────────┴─────────────┴───────┘

SUPPORTING CAST
(same format)

MINOR / REFERENCED ONLY
(same format, with ○ instead of ✓ for agent column)

EXCLUDED (not suitable as posting agents)
│  – │ Name                 │ Role                    │ Reason               │

REJECTED ENTITIES (found in text, blocked from becoming agents)
  ✗ Entity Name          → reason for rejection

Agent count: N mandatory + 0 minor = N agents

DECISIONS
─────────

1. Cast looks correct?
   a) Yes, proceed with this cast ← RECOMMENDED
   b) I need to add a character
   c) I need to remove/change someone

2. Include minor cast as agents?
   a) No, keep them as referenced-only ← RECOMMENDED
   b) Yes, promote all minor to agents
   c) Let me pick which minor characters get agents

3. Allow MiroFish to generate additional background agents?
   a) Yes, up to 6 extras
   b) Yes, up to 3 extras ← RECOMMENDED
   c) No, only use the mandatory cast
```

4. If user wants to add/change/remove, iterate until approved.

5. Once approved, generate `character_cast.json` and save to `sim-prep/<project-slug>/`:
   ```bash
   # Write the JSON using the Write tool — do NOT use the Python generator
   # for the cast file. YOU build it from the approved table because YOU
   # understand the characters. Use archetype matching for behavioral params:
   python3 -c "
   import json
   archetypes = json.load(open('scripts/mirofish-prep/templates/character_archetypes.json'))
   print(json.dumps(archetypes, indent=2))
   "
   ```
   Match each character's role to an archetype for behavioral parameters
   (activity_level, posts_per_hour, active_hours, etc.)

---

## PHASE 3: BUILD

### Steps
1. Generate the **upload document** (`upload_document.md`):
   - Synthesize from approved materials
   - Apply these transformations:
     a. Add a CHARACTER INDEX header listing all mandatory agents by full name
     b. Replace organization names with generic descriptions
        ("Walmart" → "a major retail buyer", "DEA" → "a federal agency")
     c. Replace group references with individual names
        ("the siblings" → "Benjamín, Karla, and Isabela")
     d. Mark dead characters explicitly: "Carmen Serrano [DECEASED]"
     e. Remove or neutralize any entity that could create a junk agent
     f. Keep total under 50,000 characters
     g. Write in English (for cleaner Zep entity extraction)

2. Generate the **reality seed** (`reality_seed.md`):
   - Write a fresh 2,000-3,000 character narrative prompt
   - Name every mandatory agent individually (never as groups)
   - Describe the world state at simulation start
   - Identify 2-3 colliding forces
   - Pose open questions for the simulation to answer
   - Specify report structure (4 thematic sections)
   - Write in English

3. Generate the **simulation config** (`simulation_config.json`):
   ```bash
   python3 scripts/mirofish-prep/generate_config.py \
     sim-prep/<project-slug>/character_cast.json \
     --duration <hours> \
     --language <lang>
   ```
   Then update it with:
   - The reality seed text as simulation_requirement
   - Initial posts (assign 6-8 to specific agents)
   - Hot topics (10-12 keywords from the materials, in ENGLISH)
   - Narrative direction (in English, for the production team)

4. Generate **event seeds** (`event_seeds.json`) if the user chose to use them:
   - Derive from script act breaks / key narrative beats
   - Assign each event a trigger hour and agent

5. Present BUILD summary with previews of each file:

```
BUILD COMPLETE
==============

OUTPUTS GENERATED
─────────────────

1. UPLOAD DOCUMENT — sim-prep/<slug>/upload_document.md (XX,XXX chars)
   Modifications applied:
     ✓ (list each transformation)

2. REALITY SEED — sim-prep/<slug>/reality_seed.md (X,XXX chars)
   Preview:
   ┌──────────────────────────────────────────────────────────────┐
   │ First 300 chars of the reality seed...                      │
   └──────────────────────────────────────────────────────────────┘

3. CHARACTER CAST — sim-prep/<slug>/character_cast.json
   N mandatory agents with full profiles

4. SIMULATION CONFIG — sim-prep/<slug>/simulation_config.json
   Duration: XXXh | Language: XX | Cost controls: ✓

5. EVENT SEEDS — sim-prep/<slug>/event_seeds.json
   N scheduled events

DECISIONS
─────────

1. Upload document looks correct?
   a) Yes ← RECOMMENDED
   b) Let me review the full text
   c) I want to change what's included

2. Reality seed captures the right focus?
   a) Yes ← RECOMMENDED
   b) I want to edit it
   c) Rewrite with different emphasis: ___

3. Event seeds?
   a) Yes, use these ← RECOMMENDED
   b) Adjust timing/content
   c) No scheduled events
```

---

## PHASE 4: PREFLIGHT

### Steps
1. Run the cast validator:
   ```bash
   python3 scripts/mirofish-prep/validate_cast.py sim-prep/<slug>/character_cast.json
   ```

2. Run additional validation checks yourself:
   - Upload document under 50K chars
   - Reality seed under 5K chars
   - simulation_config.json has message_window_size=50 and token_limit=150000
   - No Chinese text anywhere in config, topics, or narrative direction
   - Language field is set
   - All mandatory agents in config match character_cast.json
   - No first-name-only agents (except characters known by single name like Reynaldo)
   - No agent names that look like corruptions of known character names
     (e.g., "Nesto Vega" instead of "Emilio Vega" — the profile generator hallucinated this)
   - Upload document has been stripped of organization names that Zep would extract
   - Upload document starts with a CHARACTER INDEX listing all mandatory agents by full name
   - No agent has the same first name as another agent (catches the "Javier" + "Javier Cordero" duplication)
   - Dead characters (Carmen, Ernesto) appear ONLY in excluded_entities, never in mandatory_agents

3. Calculate cost estimate:
   - Count agents × average activity × rounds = estimated API calls
   - Estimated tokens per call: ~4,500 (4K prompt + 500 completion, bounded)
   - Cost per call: use Sonnet pricing (~$0.003 per 1K input + $0.015 per 1K output)
   - Add report generation cost (~$5-10)
   - Compare to Oro Verde S1 ($450)

4. Generate `preflight_report.md` and `upload_checklist.md`:
   - Read the checklist template:
     ```bash
     cat scripts/mirofish-prep/templates/upload_checklist.md
     ```
   - Fill in the template variables
   - Write both files to sim-prep/<slug>/

5. Optionally generate `test_config.json` (10-round mini test):
   ```bash
   python3 -c "
   import json, sys
   sys.path.insert(0, 'scripts/mirofish-prep')
   from generate_config import generate_test_config
   config = json.load(open('sim-prep/<slug>/simulation_config.json'))
   test = generate_test_config(config, test_rounds=10)
   print(json.dumps(test, indent=2))
   "
   ```

6. Present the PREFLIGHT report:

```
PREFLIGHT CHECK
===============

CAST VALIDATION
  ✅/❌ Each check result

DOCUMENT VALIDATION
  ✅/❌ Each check result

CONFIG VALIDATION
  ✅/❌ Each check result

COST ESTIMATE
  ┌──────────────────────────────────────────────────┐
  │ (itemized estimate)                              │
  │ vs. Oro Verde S1: ~$450 (XX% reduction)          │
  └──────────────────────────────────────────────────┘

PREFLIGHT RESULT: ✅ ALL CLEAR / ⚠️ WARNINGS / ❌ BLOCKED

DECISIONS
─────────

1. Ready to prep for upload?
   a) Yes, generate final output directory ← RECOMMENDED
   b) Go back and adjust something

2. Generate a mini test config?
   a) Yes, 10-round test for ~$2-3 ← RECOMMENDED
   b) No, straight to full run
```

7. On final confirmation, display the output directory listing and the upload checklist.

---

## RULES

1. **Never skip a phase.** Even if the user says "just generate everything", run all 4 phases with checkpoints.
2. **Never create a group agent.** If a character is "the Serrano siblings", create Benjamín, Karla, and Isabela as three separate agents.
3. **Never create an organization agent.** Walmart is not a character. DEA is not a character.
4. **Never create a dead character as an active agent.** Carmen is dead. She goes in excluded_entities.
5. **Always set message_window_size=50 and token_limit=150000.** These are non-negotiable.
6. **Always write config/topics/narrative in English.** Never in Chinese.
7. **Always wait for user approval between phases.** Never auto-proceed.
8. **The upload document is curated, not raw.** Never upload the user's original files as-is.
9. **The reality seed names individuals, never groups.** Write "Benjamín, Karla, and Isabela" not "the Serrano siblings".
10. **All output goes to sim-prep/<project-slug>/.** Create the directory if it doesn't exist.
11. **Flag the ontology prompt language issue.** MiroFish's ONTOLOGY_SYSTEM_PROMPT is 100% Chinese. The upload checklist must warn the user to verify entity type names come back in English PascalCase, not Chinese. If they don't, the ontology generation must be re-run.
12. **Recommend excluding Organization entity type.** When reviewing ontology in MiroFish Step 1, the user should request that Organization-type entities be excluded from agent generation — Zep will still create org nodes, but they should not become posting agents. Add this to the upload checklist as a manual verification step.
13. **Warn about Zep's black-box entity extraction.** The upload document is the ONLY lever we have to control what Zep creates. Every organization name, group noun, or abstract concept left in the upload doc WILL become a Zep entity. The BUILD phase's document curation is the most important step in the entire pipeline.
14. **Detect name hallucinations.** If the cast validator finds an agent name that looks like a corruption of a known character name (e.g., "Nesto Vega" instead of "Ernesto Vega" or "Emilio Vega"), flag it as a warning. The LLM profile generator can hallucinate partial names.
15. **Require full names where applicable.** Agent names should be full proper names (first + last), not first-name-only. "Karla" should be "Karla Serrano". "Javier" should be "Javier Cordero". Exception: characters known by single name (e.g., "Reynaldo" the thief).
16. **Include checkpoint/resume guidance.** The upload checklist should note that MiroFish currently has no checkpoint/resume capability. If the simulation crashes, data up to the crash point is in the action logs but the simulation cannot be resumed. The user should monitor VPS memory and cost actively during the first 30 rounds.

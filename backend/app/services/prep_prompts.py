"""
LLM prompt constants for the Prep Studio AI-authoring pipeline.

Each prompt encodes hard-won lessons from the Oro Verde S1 $450 simulation
disaster. S1 failure modes are embedded directly as NEGATIVE EXAMPLES so the
LLM cannot repeat them.

S1 root causes (post-mortem, 2026-04):
  - 19/27 agents were junk: Walmart, senators, grandmother (dead), family
  - Benjamín Serrano (main character) never got an agent
  - message_window_size=None → 1M+ token prompts → OOM crash at round 134
  - No character index in upload doc → Zep extracted org names as entities
  - Config generated in Chinese → hot topics/narrative direction in Chinese
"""


# ─── CAST EXTRACTION ────────────────────────────────────────────────────────

CAST_EXTRACTION_SYSTEM = """You are a character analyst for a narrative simulation engine called MiroFish.
Your job is to extract every NAMED INDIVIDUAL CHARACTER from the provided story materials
and classify them as simulation agents.

CRITICAL RULES — violations caused the Oro Verde S1 simulation to fail and waste $450:

1. ONLY real named individuals become agents. Never groups, organizations, or concepts.
   BAD (S1 failures): "senators", "the Serrano siblings", "Walmart", "the DEA",
                      "criminal empire", "activists", "cartel", "family"
   GOOD: "Benjamín Serrano", "Karla Serrano", "Isabela Serrano" (each separately)

2. FULL NAMES REQUIRED. First + last name whenever known.
   BAD: "Karla", "Javier", "the journalist"
   GOOD: "Karla Serrano", "Javier Cordero"
   Exception: single-name characters (e.g., a character known only as "Reynaldo").

3. DEAD CHARACTERS ARE NOT AGENTS. Dead characters go in excluded_entities.
   BAD (S1 failure): "Carmen Serrano" was created as agent #7 with highest influence_weight
                     even though she died before the simulation period.
   GOOD: Carmen Serrano → excluded_entities with reason "DECEASED"

4. NO DUPLICATES. One agent per character, regardless of how many name variants appear.
   BAD (S1 failure): "Javier" (agent 9) AND "Javier Cordero" (agent 12) — same person, two agents.
   GOOD: "Javier Cordero" — pick the most complete name.

5. REQUIRED AGENT MINIMUM. The simulation's protagonist(s) MUST have individual agents.
   BAD (S1 failure): Benjamín Serrano appeared in every scene but never got an individual agent.
   GOOD: Every character who appears 3+ times or drives the plot gets an individual agent.

6. ARCHETYPE MATCHING. Match each character to one of these behavioral archetypes:
   journalist, ceo_executive, operations_director, artist_creative, cartel_patriarch,
   cartel_lieutenant, politician, lawyer, investigator, activist_organizer,
   family_matriarch, corrupt_official, informant, young_idealist

Output JSON in exactly this structure:
{
  "mandatory_agents": [
    {
      "name": "Full Name",
      "archetype": "archetype_key",
      "role": "one-line description of their function in the story",
      "stance": "protagonist|antagonist|neutral|supporting|opposing",
      "narrative_weight": "PRINCIPAL|SUPPORTING|MINOR"
    }
  ],
  "excluded_entities": [
    {
      "name": "Full Name or Description",
      "reason": "DECEASED|ORGANIZATION|GROUP|ABSTRACT|DUPLICATE"
    }
  ],
  "rejected_entities": [
    "entity name that must NEVER become an agent"
  ]
}"""


CAST_EXTRACTION_USER = """Extract the character cast from these story materials.

BLOCKED PATTERNS — these entity types must NEVER appear in mandatory_agents:
  Generic nouns: senators, governors, cartels, journalists (plural), activists (plural),
                 family, siblings, grandmother, grandfather, woman, man, boy, girl,
                 child, teenager, people, citizens, workers, employees, lawyers, doctors,
                 police, military, media, public, audience, investors, politicians, officials
  Organizations: Walmart, Amazon, Netflix, Disney, Fox, HBO, DEA, FBI, CIA, NSA, SEC,
                 Harvard, Yale, Stanford, any "Grupo X" organization
  Abstracts: activism, corruption, justice, power, authority, violence,
             narco operation, criminal empire, the system
  Descriptors: anything starting with "a/the/an", "X-year-old", "young/old/unnamed"

STORY MATERIALS:
{combined_text}

VALIDATION NOTES FROM PRIOR RUNS:
  - If a character's name only appears as part of a group reference ("the Serrano siblings"),
    still create individual agents for each named sibling.
  - If you are uncertain whether a referenced person is named, do NOT invent a name.
    Put them in excluded_entities with reason "UNNAMED".
  - The protagonist must appear in mandatory_agents. If unsure who the protagonist is,
    include all characters who appear 3+ times.

Return ONLY valid JSON. No markdown, no commentary."""


# ─── CAST VALIDATION RETRY ──────────────────────────────────────────────────

CAST_RETRY_SYSTEM = """You previously extracted a character cast that failed automated validation.
Review the validation failures and produce a corrected cast.

Apply these corrections:
- Remove any agent whose name matches a blocked pattern (group nouns, organizations, abstracts)
- Split any group agent into individual named agents or move to excluded_entities
- Add last names to any first-name-only agents where the materials provide them
- Move dead characters from mandatory_agents to excluded_entities
- Merge any duplicate agents (same person, different name variants)

Return the corrected cast JSON in exactly the same structure as before."""


# ─── UPLOAD DOCUMENT ────────────────────────────────────────────────────────

UPLOAD_DOCUMENT_SYSTEM = """You are preparing a document for upload to MiroFish, a multi-agent narrative simulation platform.
MiroFish uses Zep Cloud to extract entities from the uploaded document. Those entities become
simulation agents. The upload document is the ONLY lever we have to control which agents get created.

YOUR JOB: Synthesize the provided story materials into a CLEAN narrative document that will cause
Zep to extract exactly the right entities — the named individuals — and nothing else.

CRITICAL RULES:

1. START WITH A CHARACTER INDEX.
   The very first section MUST be:
   ---
   CHARACTER INDEX
   The following characters are the simulation agents for this story:
   [list every mandatory agent by full name, one per line]
   ---
   This primes Zep's entity extractor to recognize these names as the important nodes.

2. REPLACE ALL ORGANIZATION NAMES.
   Organization names become junk agents. Replace them with generic descriptions.
   BAD: "the DEA raided the warehouse"
   GOOD: "a federal narcotics agency raided the warehouse"
   BAD: "Walmart's regional buyer"
   GOOD: "a major retail buyer"

3. EXPAND ALL GROUP REFERENCES TO INDIVIDUAL NAMES.
   Group references create group agents. Expand them.
   BAD: "the Serrano siblings argued"
   GOOD: "Benjamín, Karla, and Isabela argued"

4. MARK ALL DEAD CHARACTERS WITH [DECEASED].
   BAD: "Carmen managed the finances"
   GOOD: "Carmen Serrano [DECEASED] had managed the finances until her death"

5. WRITE IN ENGLISH. Even for Latin American projects. Zep entity extraction is more reliable in English.

6. KEEP TOTAL LENGTH UNDER 50,000 CHARACTERS. MiroFish truncates its ontology analysis at 50K.
   If the materials exceed this limit, prioritize: character descriptions > plot > setting > backstory.

7. REMOVE OR NEUTRALIZE ANY ENTITY THAT COULD CREATE A JUNK AGENT:
   - Generic nouns used as character references ("the journalist" → use their name)
   - Abstract concepts referenced as actors ("the cartel decided" → name the person)
   - Any organization, company, or institution that should NOT become a posting agent

Output the upload document as plain Markdown text. No JSON wrapper."""


UPLOAD_DOCUMENT_USER = """Create the MiroFish upload document from these materials.

MANDATORY AGENTS (these individuals MUST appear as named individuals throughout the document):
{agent_names_list}

EXCLUDED ENTITIES (NEVER mention these as active agents — dead characters listed as [DECEASED]):
{excluded_names_list}

STORY MATERIALS:
{combined_text}

Remember:
1. Start with CHARACTER INDEX listing all {agent_count} mandatory agents
2. Replace every organization name with a generic description
3. Expand every group reference to individual names
4. Mark dead characters with [DECEASED]
5. Write in English
6. Keep under 50,000 characters

Output the document text only."""


# ─── REALITY SEED ───────────────────────────────────────────────────────────

REALITY_SEED_SYSTEM = """You are writing a simulation requirement prompt for MiroFish — a world-state description
that tells the simulation engine what situation the agents are starting from.

THE REALITY SEED IS NOT A SUMMARY. It is a directive that:
1. Names every agent individually (NEVER as groups)
2. Describes the world state at simulation start
3. Identifies 2-3 colliding forces that will drive conflict
4. Poses open questions for the simulation to answer
5. Specifies a report structure (4 thematic sections)

CRITICAL RULES:

1. NAME INDIVIDUALS, NEVER GROUPS.
   BAD: "the Serrano siblings are under pressure"
   GOOD: "Benjamín, Karla, and Isabela each face different pressures"
   BAD: "the cartel leadership"
   GOOD: "Don Ezequiel and his lieutenant Rodrigo Palma"

2. TARGET LENGTH: 2,000–3,000 characters. Dense and specific.

3. WRITE IN ENGLISH. The narrative direction and topics must be in English.
   This is non-negotiable: MiroFish's config generator produces Chinese output
   if the seed is in Spanish.

4. PRESENT TENSE. Describe what IS happening at simulation start.

5. INCLUDE THESE SECTIONS:
   - WORLD STATE: what has just happened, the current situation
   - AGENTS: who each character is and what they want right now
   - TENSIONS: 2-3 specific conflicts about to collide
   - OPEN QUESTIONS: what the simulation should answer
   - REPORT STRUCTURE: 4 thematic sections for the final report

Output the reality seed as plain text. No JSON."""


REALITY_SEED_USER = """Write the reality seed for this simulation.

MANDATORY AGENTS:
{agent_list_with_roles}

STORY CONTEXT:
{combined_text}

Requirements:
- 2,000 to 3,000 characters
- Name every agent individually, never as a group
- English only
- Present tense
- Include all 5 sections: WORLD STATE, AGENTS, TENSIONS, OPEN QUESTIONS, REPORT STRUCTURE

Output the reality seed text only."""


# ─── EVENT SEEDS ────────────────────────────────────────────────────────────

EVENT_SEEDS_SYSTEM = """You are scheduling narrative event injections for a MiroFish multi-agent simulation.
Events are external shocks injected at specific simulation hours that force agents to react,
creating narrative momentum.

RULES:

1. DERIVE FROM ACT BREAKS. Identify the major turning points in the story and map them to hours.
   For a 168-hour (7-day) simulation:
   - Hour 1: Opening event that establishes stakes
   - Hours 20-30: First escalation
   - Hours 40-60: Midpoint revelation or betrayal
   - Hours 70-90: Crisis point
   - Hours 100-120: Climax build
   - Hours 130-150: Final confrontation setup
   - Hours 160-168: Resolution pressure

2. NAME SPECIFIC AGENTS in each event. Never "a character" or "someone".

3. EVENTS MUST BE PLAUSIBLE SHOCKS — things that could be news, social media posts, or
   real-world developments. NOT stage directions.
   BAD: "Benjamín discovers the truth"
   GOOD: "A federal warrant is issued for the avocado processing facility"

4. 6–8 EVENTS TOTAL. Each event: {trigger_hour, description, primary_agent, impact_agents[]}

Output JSON array:
[
  {
    "trigger_hour": 1,
    "description": "Event description as if it's a news headline or social post",
    "primary_agent": "Full Name of character most affected",
    "impact_agents": ["Full Name", "Full Name"],
    "narrative_purpose": "Why this event matters to the story"
  }
]"""


EVENT_SEEDS_USER = """Create 6-8 narrative event seeds for this simulation.

SIMULATION DURATION: {duration_hours} hours
MANDATORY AGENTS: {agent_names_list}
STORY MATERIALS: {combined_text}

Space the events through the simulation arc. Map them to the story's natural act breaks.
Each event should create pressure that forces at least 2 agents to react.

Output JSON array only."""

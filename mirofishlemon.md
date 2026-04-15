# MiroFish Lemon -- Oro Verde Simulation Post-Mortem

**Project:** Oro Verde (Pilot Episode Simulation)
**Date:** April 11, 2026
**Simulation ID:** `sim_4324da26ed07`
**VPS:** root@187.124.251.98
**LLM:** Claude Sonnet 4 via OpenRouter through LiteLLM proxy
**Status:** FAILED at round 134/168 (79.8% complete)

---

## 1. What We Were Trying To Do

Run a 168-hour (7-day) multi-agent social media simulation of the Oro Verde pilot storyline using CAMEL/OASIS framework. The simulation uses dual platforms (Twitter + Reddit) with 27 AI agents roleplaying characters and factions from the Oro Verde universe. The goal: let emergent narrative behavior reveal story dynamics that the writers couldn't predict from the outline alone.

**The simulation requirement** was a 2,647-character narrative prompt describing three colliding worlds -- the legitimate business world (Grupo Serrano), the investigation world (Ingrid Cervantes + Emilio Vega), and the criminal world (Don Ezequiel + Javier Cordero) -- and asking MiroFish to simulate how these groups interact, conflict, and collide over 168 simulated hours.

At the end, MiroFish would generate a 4-section report:
1. "The Identity Engine" -- how sibling performances evolved or fractured
2. "The Convergence" -- how external investigation progressed
3. "The Ghost of Carmen" -- how her buried decisions moved through the world
4. "The Asymmetry" -- how Ezequiel's control held or cracked

---

## 2. What Went Well

### 2.1 The Reality Seed Worked
The narrative prompt (simulation requirement) was strong. It gave the AI enough context to understand the three-world collision without over-constraining agent behavior. The report sections it generated (all 4 completed before the crash) demonstrate real narrative intelligence -- the AI understood the thematic structure.

### 2.2 Report Generation Completed
All 4 report sections were generated successfully before the OOM crash killed the simulation process:
- Section 1: "The Identity Engine: The Evolution and Fracture of Performance"
- Section 2: "The Convergence: Breakthroughs and Triggers of External Investigation"
- Section 3: "Carmen's Ghost: How Buried Decisions Detonate the Future"
- Section 4: "The Asymmetry: Maintaining and Cracking Control"

Report completed at `2026-04-11T08:22:20` -- about 8 minutes before the OOM kill at `08:30:44`.

### 2.3 Scale of Output
- **1,380 total actions** generated (661 Twitter + 719 Reddit)
- **134 rounds** completed out of 168 (80%)
- **27 agents** active across both platforms
- Simulation ran for ~2.5 hours of real time (06:11 to 08:30)
- Some agents produced genuinely interesting narrative content -- Lucía Suárez's activist posts, Javier Cordero's corporate doublespeak, the "activism" agent's attacks on Serrano legitimacy

### 2.4 Dual-Platform Architecture
Running Twitter and Reddit in parallel worked. Twitter reached round 116 and Reddit reached round 134 before the crash. The parallel runner script (`run_parallel_simulation.py`) handled both platforms cleanly.

### 2.5 The Character Engine Workaround
When the broken Step 5 interviews couldn't work (wrong agent names, no individual character agents), we built a standalone **Character Engine** (Next.js app at `/Users/quantumcode/CODE/character-social`) that loads hand-crafted character profiles and conducts AI-powered interviews with proper system prompts, memory (via Zep Cloud), and voice consistency. This turned a failure into a permanent tool.

---

## 3. What Failed

### 3.1 CRITICAL: Profile Generator Created Junk Agents

**This was the single biggest failure of the entire run.**

MiroFish Step 2 (AI profile generation) was supposed to read the reality seed and create individual agent profiles for each named character. Instead, it created:

#### Agents That Should NOT Exist
| Agent Name | Type | Why This Is Wrong |
|---|---|---|
| `Walmart` | Organization | A retail corporation is not a character |
| `CEOs` | BusinessExecutive | Generic plural noun, not a person |
| `senators` | GovernmentOfficial | Generic plural noun |
| `governors` | GovernmentOfficial | Generic plural noun |
| `cartels` | CriminalOperator | Generic plural noun |
| `criminal empire` | Organization | Abstract concept, not an agent |
| `narco operation` | Organization | Abstract concept |
| `rival family` | CriminalOperator | Unnamed group |
| `rival cartel family` | CriminalOperator | Duplicate of above |
| `family` | FamilyMember | Which family? |
| `Serrano` | FamilyMember | Last name, not a character |
| `Serrano siblings` | FamilyMember | Group entity, not individual |
| `Serrano family` | FamilyMember | Another group duplicate |
| `Serrano name` | FamilyMember | This is a *concept*, not a person |
| `grandmother` | FamilyMember | Carmen is dead -- she can't post on Twitter |
| `woman` | Person | Completely unidentifiable |
| `fourteen-year-old girl` | Person | Not in the reality seed at all |
| `activism` | Activist | Abstract noun, not a person |
| `Nesto Vega` | Person | Wrong name -- should be Emilio Vega (Ernesto's son) or Ernesto Vega (dead lawyer) |

#### Key Characters That NEVER Got Individual Agents
| Character | Role | What Happened |
|---|---|---|
| **Benjamin Serrano** | CEO, eldest sibling | Merged into "Serrano siblings" group entity |
| **Karla Serrano** | Operations Director | Got a low-activity agent (0.2) but never properly profiled |
| **Isabela Serrano** | Artist / youngest sibling | Never created at all |
| **Don Ezequiel Antona** | Cartel patriarch | Never created -- absorbed into "cartels" or "criminal empire" |
| **Emilio Vega** | Ernesto's son, investigating | Never created -- "Nesto Vega" is a hallucinated corruption |
| **Gabriela Mendoza** | Head housekeeper with secrets | Never created |
| **Valeria Torres** | Social media manager | Never created |
| **Reynaldo** | The unnamed thief | Got an agent but with no proper profile context |

**Result:** The simulation ran with 27 agents but only **2 properly named individuals** (Ingrid Cervantes and Javier Cordero -- and Javier got duplicated as both "Javier" and "Javier Cordero"). The remaining 25 slots were wasted on group entities, abstract concepts, duplicates, and hallucinated characters.

**Root cause:** The profile generator extracted *entity mentions* from the text (nouns, noun phrases, named entities) rather than building a cast list of individual characters. It treated "the Serrano siblings" as an agent instead of creating Benjamin, Karla, and Isabela as three separate agents. It created "Walmart" because Walmart was mentioned in the avocado supply chain context. It created "grandmother" because Carmen was referred to that way, despite Carmen being dead.

### 3.2 CRITICAL: OOM Crash at Round 134

The Linux OOM killer terminated the simulation process (PID 2153) with exit code -9 at round 134 of 168.

**Error:** `进程退出码: -9, 错误: ` (Process exit code: -9)

**Root cause:** The CAMEL framework's agent creation had `message_window_size=None` by default, meaning agent conversation history grew unboundedly. By round 134, each agent's context window contained the full history of all its interactions -- potentially 1M+ tokens per agent. With 27 agents active across two platforms, the VPS ran out of memory.

**Cost impact:** Later rounds cost $3+ per API call to OpenRouter because the full conversation history was sent with every request. Total estimated cost: **~$450+ in OpenRouter credits** for a simulation that didn't even complete.

### 3.3 Step 5 Interviews Broken

MiroFish Step 5 (post-simulation character interviews) relies on the agent names from Step 2 to identify who to interview. Since Step 2 created agents like "Serrano siblings" and "Walmart" instead of individual characters, Step 5 couldn't conduct meaningful interviews with the actual story characters. This is what led to building the Character Engine as a separate tool.

### 3.4 Chinese Language Contamination

The simulation config, initial posts, hot topics, and narrative direction were all generated in Chinese (Mandarin) instead of Spanish or English. Examples:
- Hot topics: `"Serrano家族"`, `"牛油果帝国"`, `"洗钱丑闻"`
- Initial posts: `"Carmen Serrano的突然去世引发了很多疑问..."`
- Narrative direction: `"围绕Serrano牛油果帝国的合法性质疑展开..."`

The agents themselves posted in a mix of English, Spanish, and Chinese. This is a Lemon Studios production for Latin American/US audiences -- the simulation language should have been constrained to Spanish and English.

### 3.5 Carmen Agent Active Despite Being Dead

Agent ID 7 (`Carmen`) was created as an active agent with `influence_weight: 3` (the highest of any agent). Carmen Serrano is dead before the simulation begins. She should not exist as a posting agent. She could exist as a *referenced entity* in the knowledge graph, but not as someone generating social media posts.

### 3.6 Duplicate Agents

Multiple agents represent the same entity:
- `Javier` (agent 9) and `Javier Cordero` (agent 12) -- same person, two agents
- `rival family` (agent 3) and `rival cartel family` (agent 5) -- same concept, two agents
- `Serrano siblings` (agent 4), `Serrano family` (agent 17), `Serrano name` (agent 18), `Serrano` (agent 11), `family` (agent 10) -- five agents for one family

---

## 4. What We Fixed (Already Applied)

### 4.1 Context Window Limits
Added to all simulation scripts:
```python
message_window_size=50,
token_limit=150000,
```

Applied to:
- `backend/scripts/run_parallel_simulation.py` (lines 1142-1143, 1335-1336)
- `backend/scripts/run_twitter_simulation.py` (lines 582-583)
- `backend/scripts/run_reddit_simulation.py` (lines 569-570)

This caps each agent's conversation history at 50 messages and 150K tokens, preventing unbounded memory growth and $3+ API calls.

### 4.2 Character Engine Built
A standalone Next.js application (`/Users/quantumcode/CODE/character-social`) now provides:
- Hand-crafted profiles for all 14 key Oro Verde characters
- Solo interviews with streaming AI responses
- Confrontation mode (1v1 moderated conversations)
- Room mode (2-6 character group chats)
- Persistent memory via Zep Cloud
- Cyberpunk UI designed in Banani

This bypasses MiroFish Step 5 entirely and provides much higher quality character interviews.

---

## 5. What MUST Be Fixed Before Next Run

### 5.1 MANDATORY: Explicit Character Cast List in Step 2

The profile generator MUST receive a mandatory list of individual characters to create as agents. The AI should not be allowed to invent the agent list by extracting entities from the text.

**Required input format:**
```json
{
  "mandatory_agents": [
    { "name": "Benjamin Serrano", "role": "CEO of Grupo Serrano", "stance": "protagonist" },
    { "name": "Karla Serrano", "role": "Operations Director", "stance": "protagonist" },
    { "name": "Isabela Serrano", "role": "Artist / recovery advocate", "stance": "protagonist" },
    { "name": "Don Ezequiel Antona", "role": "Cartel patriarch", "stance": "antagonist" },
    { "name": "Javier Cordero", "role": "CFO / cartel embed", "stance": "antagonist" },
    { "name": "Ingrid Cervantes", "role": "Investigative journalist", "stance": "opposing" },
    { "name": "Emilio Vega", "role": "Ernesto's son", "stance": "opposing" },
    { "name": "Reynaldo", "role": "The unnamed thief", "stance": "neutral" },
    { "name": "Gabriela Mendoza", "role": "Head housekeeper", "stance": "neutral" },
    { "name": "Valeria Torres", "role": "Social media manager", "stance": "supportive" },
    { "name": "Lucia Suarez", "role": "Environmental activist", "stance": "opposing" },
    { "name": "Diego Serrano", "role": "Architect / Carmen's confidant", "stance": "neutral" },
    { "name": "Sofia Paredes", "role": "Isabela's sponsor", "stance": "supportive" },
    { "name": "Padre Ignacio", "role": "Family priest", "stance": "neutral" }
  ],
  "allow_additional_agents": true,
  "max_additional_agents": 6
}
```

The AI can still generate *additional* background agents (journalists, public commenters, investors) to fill out the simulation world, but the 14 core characters MUST each get their own individual agent with a proper profile.

### 5.2 MANDATORY: Character Name Validation

After Step 2 profile generation, run an automated validation:
- Every `mandatory_agents` entry must appear as an individual agent (exact name match)
- No agent name should be a generic noun ("senators", "cartels", "family")
- No agent name should be an organization ("Walmart", "criminal empire")
- No dead characters should be active posting agents
- No duplicate agents for the same character
- Flag any agent whose name doesn't match a known character or reasonable NPC

If validation fails, Step 2 must re-run with explicit corrections before proceeding.

### 5.3 MANDATORY: Language Constraint

The simulation config must specify output language:
```json
{
  "language": "es",
  "allowed_languages": ["es", "en"],
  "ui_language": "en"
}
```

All agent posts should be in Spanish (this is a Mexican drama) with occasional English for international business contexts. The config generation, hot topics, and narrative direction should be in English (for the production team).

### 5.4 Rate Limiting and Cost Controls

- Set a per-round cost ceiling (e.g., $0.50/round max)
- Log token usage per API call
- Alert when cost per call exceeds threshold (e.g., $1.00)
- Kill simulation gracefully if total cost exceeds budget (e.g., $100)
- The $450+ burn on this run was entirely preventable

### 5.5 Checkpoint and Resume

The simulation should checkpoint its state every N rounds (e.g., every 10) so that:
- If the process crashes (OOM, network failure, VPS restart), it can resume from the last checkpoint
- The 134 rounds of data from this run were partially recoverable but the simulation couldn't be resumed
- Checkpoint should save: agent states, conversation histories, action logs, round number

### 5.6 Dead Character Handling

Characters who are dead at simulation start (Carmen Serrano, Ernesto Vega) should be:
- Present in the knowledge graph as referenced entities
- NOT created as active posting agents
- Available for "ghost" narrative influence (other agents reference them) but not as autonomous posters

---

## 6. Simulation Data Inventory

### What Was Saved
```
oro-verde-sim-export/
├── twitter_actions.jsonl         # 661 actions
├── reddit_actions.jsonl          # 719 actions
├── simulation_data/
│   ├── simulation_config.json    # Full config with 27 agent profiles
│   ├── run_state.json            # Final state (failed at round 134)
│   ├── state.json                # Internal state snapshot
│   ├── simulation.log            # Simulation process log
│   ├── twitter_profiles.csv      # Twitter agent profiles
│   ├── reddit_profiles.json      # Reddit agent profiles
│   ├── twitter_simulation.db     # SQLite database for Twitter
│   ├── reddit_simulation.db      # SQLite database for Reddit
│   ├── twitter/actions.jsonl     # Platform-specific action log
│   └── reddit/actions.jsonl      # Platform-specific action log
└── report/
    ├── meta.json                 # Report metadata + simulation requirement
    ├── outline.json              # Report structure outline
    ├── full_report.md            # Complete 4-section report (7,700 chars)
    ├── section_01.md             # The Identity Engine
    ├── section_02.md             # The Convergence
    ├── section_03.md             # The Ghost of Carmen
    ├── section_04.md             # The Asymmetry
    ├── progress.json             # Report generation progress (completed)
    ├── agent_log.jsonl           # Report agent's action log
    └── console_log.txt           # Report generation console output
```

### Key Numbers
| Metric | Value |
|---|---|
| Simulation hours designed | 168 (7 days) |
| Rounds completed | 134 / 168 (79.8%) |
| Twitter rounds | 116 |
| Reddit rounds | 134 |
| Total actions | 1,380 |
| Twitter actions | 661 |
| Reddit actions | 719 |
| Unique agents | 27 |
| Properly named individuals | 2 (Ingrid Cervantes, Lucía Suárez) + partial (Karla, Javier/Javier Cordero, Reynaldo) |
| Junk/group agents | ~19 |
| Report sections completed | 4/4 |
| Real time elapsed | ~2.5 hours (06:11 - 08:30) |
| Estimated cost | ~$450+ |
| Exit code | -9 (OOM killed) |

---

## 7. Lessons for Lemon Studios

### The Profile Generator Is the Weak Link
Everything downstream depends on Step 2 creating the right agents. If it creates "Walmart" instead of "Benjamin Serrano", no amount of simulation runtime can fix it. **Invest the most engineering time here.**

### Context Windows Are Expensive
An unbounded context window in a multi-agent simulation is a money furnace. 27 agents x 134 rounds x growing conversation history = exponential cost growth. Always cap `message_window_size` and `token_limit`.

### Build the Interview Tool Separately
MiroFish Step 5 (in-simulation interviews) depends on agent naming being correct, the simulation completing, and the agent states being preserved. Three failure points. The Character Engine approach (standalone tool, hand-crafted profiles, independent of simulation state) is more reliable for production use. Keep it.

### Validate Before You Burn
A 30-second validation check after Step 2 ("Do all key characters have individual agents? Are there any agents named 'Walmart'?") would have saved $450 and a day of work. Build automated pre-flight checks before committing to a full simulation run.

### The Narrative AI Is Actually Good
Despite all the infrastructure failures, the report it generated captured the thematic structure of Oro Verde accurately. The AI understands narrative dynamics when given a good reality seed. The simulation *framework* is the bottleneck, not the AI's storytelling capability.

---

## 8. Next Run Checklist

Before running the next Oro Verde simulation (or any Lemon Studios simulation):

- [ ] Provide mandatory individual character cast list to Step 2
- [ ] Validate agent names after Step 2 (no generics, no organizations, no dead characters)
- [ ] Set `message_window_size=50` and `token_limit=150000` on all agent creation
- [ ] Set language constraint to Spanish/English
- [ ] Configure cost ceiling and per-call alerts
- [ ] Implement checkpoint/resume every 10 rounds
- [ ] Remove dead characters from active agent pool
- [ ] De-duplicate agent names (one agent per character, no "Javier" + "Javier Cordero")
- [ ] Test with a 10-round mini-run before committing to full 168 rounds
- [ ] Monitor VPS memory usage during first 20 rounds
- [ ] Keep Character Engine updated with latest character profiles regardless of MiroFish status

# MiroFish-Lemon — Agent Context

## What This Workspace Is

MiroFish-Lemon is a fork/local instance of MiroFish, a multi-agent swarm intelligence simulation engine. It ingests real-world "seed" documents, constructs a high-fidelity parallel digital world populated by AI agents with distinct personalities and long-term memory, runs forward social simulation across configurable rounds, and produces a prediction/outcome report.

This workspace is operated by **Lemon Virtual Studios** as an R&D tool for:

1. **Narrative stress-testing** — simulating audience response to TV series arcs before committing to production decisions
2. **Story intelligence** — using the simulation output as a form of AI-in-the-loop "writers' room pressure test"
3. **Market/distribution research** — modeling how specific streaming audiences respond to content choices

---

## Primary Active Project: ORO VERDE

Oro Verde is a premium narco-family drama series currently in development at Lemon Virtual Studios. MiroFish is being used to simulate audience reception and narrative arc outcomes before the show is pitched or produced.

### Logline

Three privileged, emotionally broken siblings lose their inheritance when their dying grandmother cuts them out — and their desperate attempt to steal it back accidentally kills the only man protecting them, leaving them owned by the same criminal empire that built the family fortune in the first place.

### Genre & Tone

Premium narco-family drama. Succession's dynastic power warfare + Ozark's criminal captivity + Narcos Mexico's moral rot + Drops of God's sensory luxury — set inside the global avocado industry in contemporary Michoacán, Mexico. Surface is immaculate (colonial haciendas, Harvard MBAs, Macallan 18). Violence is quiet and methodical. Nobody screams.

**Thesis:** Legitimate power and criminal power are the same thing in different clothes.

### Target Audience

- **Primary:** Mexican and US Latino streaming audiences — Netflix MX / ViX+. Ages 28–48, professional class, bilingual. Both genders, skewing slightly female.
- **Secondary:** International prestige drama audiences (Narcos, Money Heist, Who Killed Sara comp viewers).

### Comparable Shows

- Ozark (Netflix) — structural DNA
- Succession (HBO) — dynastic warfare engine
- Narcos Mexico — moral complexity of the cartel world
- Drops of God (Apple TV+) — luxury commodity as inheritance vehicle

---

## Core Characters (Simulation Persona Seeds)

| Character | Role | Type | Core Wound |
|---|---|---|---|
| **Benjamín Serrano** | Protagonist, Middle sibling (35) | Enneagram 3w2 | Performs competence; doesn't know who he is without an audience |
| **Karla Serrano** | Oldest sibling (40) | Enneagram 8w7 | Confuses armor with strength; will destroy what she needs to prove she doesn't need it |
| **Isabela Serrano** | Youngest sibling (24) | Enneagram 7w6 | The only one actually moving toward the truth; dismissed by everyone |
| **Doña Carmen Serrano** | Matriarch (flashbacks) | Enneagram 8w9 | Made the criminal deal; protected grandchildren from it; didn't foresee they'd fight |
| **Don Ezequiel Antona** | Antagonist (65) | Enneagram 8w9 | Owns the siblings through Carmen's broken agreement; cannot be surprised |
| **Javier Cordero** | CFO / embedded spy (40) | Enneagram 5w6 | Reports to Don Ezequiel while pretending to serve the siblings |
| **Lucía Suárez** | Environmental activist | Enneagram 1w2 | Thermometer for Benjamín's corruption; cannot be bought |
| **Ingrid Cervantes** | Journalist | — | Falling for Karla while investigating the very murder Karla is connected to |
| **Emilio Vega** | Son of Ernesto (36) | Enneagram 9w8 | Came to close his father's estate; cannot close his eyes |
| **Gabriela Ruiz** | Head housekeeper (63) | — | Knows everything; has never been asked |
| **Valeria Luna** | Benjamín's wife (34) | — | Loves him enough to look; smart enough to find things |
| **Padre Mendoza** | Parish priest (72) | — | Heard confession; is praying he never has to testify |

### Secret History

- **1980s:** Carmen allies with Don Ezequiel. He runs criminal operations through her avocado shipping/distribution infrastructure. Nobody inside Grupo Serrano ever knew.
- **2001:** Rival narco family (the Peraltas) brings down the private plane carrying Carmen's daughter and son-in-law. Benjamín is 12. Family told it was an accident. Carmen directs Don Ezequiel to destroy the Peraltas. He does.
- **Present:** Siblings live inside consequences of decisions made before they were adults. Nobody alive has told them the truth.
- **Midseason reveal (Episode 5):** Isabela finds proof the crash was not an accident. Point of no return.

---

## Season Architecture (10 Episodes)

| EP | Title | Function |
|---|---|---|
| 1 | Mundo Normal vs Mundo Nuevo | Hook, establish, status quo permanently broken |
| 2 | Adaptación al Nuevo Mundo | Consequences, subplots surface |
| 3 | Aprendiendo las Reglas | World expands, alliances/rivalries establish |
| 4 | Dominio Aparente | First major turning point |
| **5** | **Punto de No Retorno** | **MIDPOINT — plane crash was murder; everything restructures** |
| 6 | Comienzo del Fin | Alliances reconfigure post-midpoint |
| 7 | Todo se Desmorona | Calm before storm; decisions that cannot be undone |
| 8 | El Último Respiro | Climax begins, all storylines converge |
| 9 | La Caída | Primary confrontations, major losses, truths land |
| 10 | Transformación | Resolution (not clean) + seeds for Season 2 |

---

## MiroFish Configuration Guidance for Oro Verde

### How to Structure the Seed Document

The Reality Seed file for Oro Verde is already drafted and stored at:
```
/Users/quantumcode/.gemini/antigravity/brain/277ad457-04c9-462a-b6dc-c3d1068d9f04/oro-verde-reality-seed.md
```

This document (295 lines) contains: logline, genre, world/setting, full character profiles with Enneagram typing, character relationship map, secret history, pilot synopsis, season thematic spine, 10-episode structure, comparable shows, and target audience. It is ready to be used as a MiroFish seed as-is.

### Recommended Initial Simulations (Start Small — Under 40 Rounds)

| Priority | Question | Seed Input | Agents |
|---|---|---|---|
| 🥇 | How do Mexican streaming audiences track emotionally across Season 1? | Full Reality Seed | 20–30 viewer agents, demographically seeded to primary target |
| 🥈 | Midseason reveal timing — Ep 5 vs Ep 7 — which gets stronger audience response? | Reality Seed + episode structure | 20 viewer agents, run twice |
| 🥉 | Does Benjamín's AI algorithm lie read as clever or contrived to the audience? | Pilot synopsis only | 15 agents |
| 4 | Karla/Ingrid relationship — does the audience root for it given the conflict-of-interest? | Karla + Ingrid profiles | 15 agents |
| 5 | How does social media simulation (Twitter-like) evolve if the plane crash reveal leaks before Ep 5 airs? | Full seed + specific scenario injection | 25 agents |

### Agent Population Seeds (for Simulation Config)

When configuring agent personas, use these demographic anchors for the primary simulation:
- Age range: 28–48
- Education: university-educated, professional class
- Location: Mexico City / Guadalajara / Monterrey (urban centers) + US Latino diaspora
- Streaming habits: Netflix primary, ViX+ secondary
- Cultural references: aware of Narcos, Money Heist, Succession
- Language: bilingual comfort (Spanish primary)

---

## Technical Setup

### Stack
- **Backend:** Python 3.11–3.12 (FastAPI via `uv`)
- **Frontend:** Vue 3 + Vite
- **Frontend port:** 3000
- **Backend API port:** 5001
- **Simulation Engine:** OASIS (CAMEL-AI open source)
- **Agent Memory:** Zep Cloud (GraphRAG-backed long-term memory)
- **LLM:** Any OpenAI-compatible API (default: Alibaba Qwen-plus)

### Deployment

This instance runs on **Hostinger Docker VPS**. The app is containerized and managed via `docker compose`. The local clone at `/Users/quantumcode/CODE/MIROFISH LEMON` is for reference and code inspection only — do not run `npm run dev` or the backend locally.

**Docker deployment:**
```bash
# On the VPS — start the stack
docker compose up -d
# Ports: 3000 (frontend) / 5001 (backend API)
```

### Required Environment Variables (`.env` on VPS)
```env
LLM_API_KEY=           # Primary LLM API key
LLM_BASE_URL=          # e.g. https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=        # e.g. qwen-plus (cheapest per-token for heavy agent workloads)

ZEP_API_KEY=           # Zep Cloud key — free tier sufficient for initial runs

# Optional: faster secondary model for lower-stakes calls
LLM_BOOST_API_KEY=
LLM_BOOST_BASE_URL=
LLM_BOOST_MODEL_NAME=
```

> ⚠️ **Cost warning:** Each simulation round = one LLM call per agent. A 40-round simulation with 30 agents = ~1,200 LLM calls. Start with 10–15 rounds and 15–20 agents until you've calibrated cost.

---

## Workflow Intent

This workspace exists to make MiroFish serve as Lemon Virtual Studios' **simulation intelligence layer** — a tool that agents in the Paperclip infrastructure can invoke to pre-validate story decisions, simulate audience responses, and generate prediction reports that feed back into production planning for Oro Verde and future projects.

**The live instance runs on Hostinger VPS.** This local clone is a read/reference copy for code inspection, agent.md authoring, and seed document preparation.

The next activation milestone is: **running the first Oro Verde simulation** on the VPS instance, using the Reality Seed document, with a focused question about Season 1 audience emotional tracking.

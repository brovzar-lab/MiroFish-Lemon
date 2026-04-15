# PREFLIGHT REPORT — Oro Verde S2 Re-Run
**Generated:** 2026-04-15 01:06:00 CST
**Phase:** 4 PREFLIGHT
**Overall Status:** ✅ PASS — Ready to upload

---

## CAST VALIDATION (validate_cast.py)

| Check | Result | Detail |
|-------|--------|--------|
| AGENT_COUNT | ✅ PASS | 12 mandatory agents |
| NAME_HALLUCINATION | ⚠️ WARN × 10 | All warnings are **false positives** — siblings share `Serrano` surname, validator flags sibling names as corruptions of each other. Structural feature of this cast. `Emilio Vega` flagged vs `Ernesto Vega` — these are different characters (father/son). No real hallucination risk. |

**Failures: 0 / Warnings: 10 (all false positive)**

---

## DOCUMENT SIZE CHECK

| File | Chars | Limit | Status |
|------|-------|-------|--------|
| `upload_document.md` | 34,457 | 50,000 | ✅ Within limit (31% headroom) |
| `reality_seed.md` | 4,086 | 5,000 | ✅ Within limit (18% headroom) |

---

## CONFIGURATION CHECK

| Parameter | Value | Required | Status |
|-----------|-------|----------|--------|
| `message_window_size` | 50 | 50 | ✅ |
| `token_limit` | 150,000 | 150,000 | ✅ |
| `language` | `es` | `es` | ✅ |
| `max_cost_per_round_usd` | $0.50 | ≤ $0.50 | ✅ |
| `agent_configs` count | 12 | 12 | ✅ |
| `initial_posts` count | 8 | ≥ 1/agent | ✅ |
| `hot_topics` count | 12 | ≥ 5 | ✅ |
| `event_seeds` count | 8 | ≥ 4 | ✅ |
| `simulation_hours` | 168 | 168 | ✅ |

---

## POLLUTION CHECK (upload_document.md)

| Pattern | Hits | Status | Notes |
|---------|------|--------|-------|
| Chinese characters | 0 | ✅ CLEAN | |
| `Walmart` | 0 | ✅ CLEAN | |
| `DEA` (org, word-boundary) | 0 | ✅ CLEAN | Substring matches in "death" are false positives — excluded |
| `Harvard` | 0 | ✅ CLEAN | |
| `criminal empire` | 0 | ✅ CLEAN | |
| `the siblings` | 0 | ✅ CLEAN | Fixed in this session |
| `the family` (entity use) | 3 | ⚠️ LOW RISK | Remaining uses are descriptive prose: "the family's expectations", "the family she loves", "The family is the only unit of safety" — none create a new Zep entity |
| `grandmother` | 2 | ⚠️ LOW RISK | Both are descriptive prose references to Carmen Serrano, not entity labels |

**Zero entity-polluting patterns remaining.**

---

## EXCLUDED ENTITIES CHECK

| Character | Status | Risk |
|-----------|--------|------|
| Carmen Serrano | ✅ Marked `[DECEASED]` throughout doc, listed in `excluded_entities` | None |
| Ernesto Vega | ✅ Marked `[DECEASED]` throughout doc, listed in `excluded_entities` | None |

---

## DORMANT AGENT REVIEW

| Agent | Behavior Profile | Risk |
|-------|-----------------|------|
| Reynaldo | `activity_level: 0.15`, `posts_per_hour: 0.05`, 6-hour active window (14-16, 21-23), `response_delay_max: 600s` | ✅ Seeded as dormant — will not initiate unless activated by another agent |
| Padre Mendoza | `activity_level: 0.2`, `posts_per_hour: 0.1`, `response_delay_max: 480s` | ✅ Appropriately quiet |

---

## COST ESTIMATE

| Item | Estimate |
|------|----------|
| Input tokens (avg 3,500/call × 7.5 agents/round × 168 rounds) | ~4.4M tokens → **$13.23** |
| Output tokens (avg 500/call × same) | ~630K tokens → **$9.45** |
| Report generation (InsightForge + PanoramaSearch + QuickSearch) | ~**$7.50** |
| **Total estimated cost** | **~$30.18** |
| S1 actual cost (for comparison) | $450 |
| **Cost reduction vs S1** | **~93%** |

> Cost controls active: `message_window_size=50`, `token_limit=150,000`, `max_cost_per_round_usd=0.50`.

---

## FILE INVENTORY

```
sim-prep/oro-verde/
├── character_cast.json        ✅  12 agents + 2 excluded + 27 rejected patterns
├── upload_document.md         ✅  34,457 chars — ready to upload to MiroFish
├── reality_seed.md            ✅  4,086 chars — paste into Simulation Requirement field
├── simulation_config.json     ✅  Full config with event_config populated
└── event_seeds.json           ✅  8 inflection points across 168-hour arc
```

---

## UPLOAD PROCEDURE

1. Paste the full contents of `upload_document.md` into the **Source Material** upload field
2. Paste the full contents of `reality_seed.md` into the **Simulation Requirement** field
3. Upload `simulation_config.json` as the simulation configuration (or paste agent_configs into the UI)
4. Set simulation to **168 hours**, **Spanish**, **12 mandatory agents**
5. Confirm `message_window_size = 50` and `token_limit = 150,000` before starting

---

## OPEN ITEMS (not blockers)

| # | Item | Priority |
|---|------|----------|
| 1 | Validator NAME_HALLUCINATION rule needs surname-aware logic — siblings sharing `Serrano` will always trigger false positives | Low — cosmetic only |
| 2 | `the family` (3 remaining uses) and `grandmother` (2 uses) are descriptive prose, not entity labels — acceptable as-is | Low — no action needed |
| 3 | MiroFish-generated additional agents (up to 3 allowed per cast) should be reviewed before round 1 to confirm no polluted names | Pre-launch |
| 4 | GUI for sim-prep workflow (upload + config + cast selection + live status) — planned for next session | Post-launch |

---

**VERDICT: READY TO UPLOAD ✅**
All hard blockers from S1 post-mortem addressed. No failures. Zero entity-polluting patterns. Cost controls engaged. Dormant agents correctly profiled. 168-hour arc seeded.

# Upload Checklist — {{PROJECT_NAME}}

Generated: {{GENERATED_AT}}
Estimated cost: {{COST_ESTIMATE}}

## Pre-Upload
- [ ] MiroFish backend running on VPS (root@187.124.251.98)
- [ ] LiteLLM proxy running and connected to OpenRouter
- [ ] OpenRouter balance > {{COST_ESTIMATE}} (check at openrouter.ai/credits)
- [ ] VPS memory > 4GB free (`free -h` on VPS)

## Step 1: Graph Building
- [ ] Create new project in MiroFish UI
- [ ] Upload `upload_document.md` as the Reality Seed document
- [ ] Paste contents of `reality_seed.md` into simulation requirement field
- [ ] Click "Generate Ontology"
- [ ] **VERIFY** entity type names are English PascalCase (Person, Journalist, etc.)
      ⚠️ MiroFish's ontology prompt is Chinese — if types come back in Chinese, re-generate
- [ ] **VERIFY** entity types focus on individual character roles, not organizations
      Ideal types: Person, FamilyMember, Journalist, Activist, BusinessExecutive, CriminalOperator
      Problem types: Organization, Company, Corporation → these create junk agents
- [ ] If Organization type appears: note which characters Zep might classify as orgs.
      In Step 2, verify those didn't become posting agents.
- [ ] Click "Build Graph"
- [ ] Wait for graph building to complete (may take 2-5 minutes)

## Step 2: Profile Generation — CRITICAL CHECKPOINT
- [ ] Click "Generate Profiles"
- [ ] **STOP AND VERIFY** every name in `character_cast.json` appears as an individual agent:
{{MANDATORY_AGENT_CHECKLIST}}
- [ ] **VERIFY** no junk agents appear (Walmart, senators, family, etc.)
- [ ] **VERIFY** no dead characters are active agents
- [ ] If ANY check fails: **DO NOT PROCEED**. Re-run profile generation or manually fix.

## Step 3: Simulation
- [ ] Optional: Run 10-round test first using `test_config.json` (~$2-3)
- [ ] Monitor first 10 rounds — cost should be < $0.50/round
- [ ] Monitor VPS memory — should stay under 80% (`free -h`)
- [ ] If test passes: start full {{DURATION_HOURS}}-hour simulation
- [ ] Simulation will take approximately {{ESTIMATED_RUNTIME}} of real time
- [ ] ⚠️ **NO CHECKPOINT/RESUME**: If the simulation crashes, it CANNOT be resumed.
      Data up to the crash point is saved in action logs, but you must restart from round 0.
      Monitor actively during the first 30 rounds. If memory > 80% or cost > $0.50/round, STOP.
- [ ] Check OpenRouter dashboard periodically for cumulative cost

## Step 4: Report
- [ ] Generate report after simulation completes
- [ ] Verify report sections generated successfully

## Step 5: Post-Simulation
- [ ] Export simulation data to Character Engine:
  ```bash
  cd /Users/quantumcode/CODE/character-social
  ./scripts/sync-from-mirofish.sh
  ```
- [ ] Update character profiles in Character Engine if simulation revealed new dynamics
- [ ] Review report for narrative insights

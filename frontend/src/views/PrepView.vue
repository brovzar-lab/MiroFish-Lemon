<template>
  <div class="prep-workspace">

    <!-- ── HEADER ─────────────────────────────────────────────────── -->
    <header class="prep-header">
      <div class="header-top">
        <div class="brand-block">
          <router-link to="/" class="back-link" title="Back to dashboard">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </router-link>
          <div class="brand-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
          </div>
          <div>
            <div class="brand-title">MIROFISH PREP</div>
            <div class="brand-subtitle">Editorial document studio for AI character simulation packages</div>
          </div>
        </div>
        <div class="session-strip">
          <div class="session-stat">
            <div class="session-label">PROJECT</div>
            <div class="session-value mono">{{ projectName }}</div>
          </div>
          <div class="session-stat">
            <div class="session-label">WORDS INGESTED</div>
            <div class="session-value mono">{{ totalWords.toLocaleString() }}</div>
          </div>
          <div class="session-stat">
            <div class="session-label">CAST AGENTS</div>
            <div class="session-value mono">{{ activeAgentCount }} active</div>
          </div>
          <div class="session-stat">
            <div class="session-label">PACKAGE STATE</div>
            <div class="session-value mono" :style="{ color: packageStateColor }">{{ packageState }}</div>
          </div>
        </div>
      </div>

      <!-- Phase stepper -->
      <div class="stepper">
        <button
          v-for="(phase, i) in phases"
          :key="phase.id"
          class="step-tab"
          :class="{ active: activePhase === phase.id }"
          @click="activePhase = phase.id"
        >
          <div class="step-left">
            <div class="step-index mono">{{ String(i + 1).padStart(2, '0') }}</div>
            <div>
              <div class="step-name">{{ phase.label }}</div>
              <div class="step-meta">{{ phase.meta }}</div>
            </div>
          </div>
          <div class="step-badge mono">{{ phase.badge }}</div>
        </button>
      </div>
    </header>

    <!-- ── BODY ───────────────────────────────────────────────────── -->
    <main class="prep-body">
      <div class="notebook">

        <!-- LEFT PAGE -->
        <div class="page page-left">

          <!-- PHASE 01: INGEST -->
          <section v-show="activePhase === 'ingest'" class="section-card">
            <div class="section-heading-row">
              <div>
                <div class="eyebrow mono">PHASE 01 / INGEST</div>
                <div class="section-title serif">Source documents laid out like working pages.</div>
              </div>
              <div class="doc-state mono" :class="{ ready: allDocsLoaded }">
                <svg v-if="allDocsLoaded" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                {{ allDocsLoaded ? 'all imports clean' : `${loadedDocCount}/5 loaded` }}
              </div>
            </div>
            <p class="section-copy">Drop each source document into its tile. The studio will parse word count, check character limits, and flag any encoding issues before advancing to CAST.</p>

            <div class="doc-grid">
              <div
                v-for="doc in docs"
                :key="doc.id"
                class="doc-card"
                :class="{ wide: doc.wide, loaded: doc.loaded, dragging: doc.dragging }"
                @dragover.prevent="doc.dragging = true"
                @dragleave="doc.dragging = false"
                @drop.prevent="onFileDrop($event, doc)"
                @click="triggerFileInput(doc)"
              >
                <div>
                  <div class="doc-card-top">
                    <div class="doc-icon-wrap">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    <div class="doc-state-pill" :class="{ loaded: doc.loaded }">
                      <svg v-if="doc.loaded" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                      {{ doc.loaded ? 'loaded' : 'empty' }}
                    </div>
                  </div>
                  <div class="doc-title">{{ doc.label }}</div>
                  <div class="drop-zone mono">{{ doc.loaded ? doc.filename : doc.hint }}</div>
                </div>
                <div class="doc-footer">
                  <div class="filename-badge mono" v-if="doc.loaded">{{ doc.filename }}</div>
                  <div class="filename-badge mono empty" v-else>Drop file or click</div>
                  <div class="count-badge mono" v-if="doc.loaded">{{ doc.wordCount.toLocaleString() }} words</div>
                </div>
                <input
                  :ref="'fileInput_' + doc.id"
                  type="file"
                  :accept="doc.accept"
                  style="display:none"
                  @change="onFileInputChange($event, doc)"
                />
              </div>
            </div>

            <button
              class="action-btn primary"
              :disabled="!allDocsLoaded"
              @click="activePhase = 'cast'"
            >
              Advance to CAST →
            </button>
          </section>

          <!-- PHASE 02: CAST -->
          <section v-show="activePhase === 'cast'" class="section-card">
            <div class="section-heading-row">
              <div>
                <div class="eyebrow mono">PHASE 02 / CAST</div>
                <div class="section-title serif">Character cards arranged like casting notes on a desk.</div>
              </div>
              <div class="toolbar-chip mono">{{ activeAgentCount }} agents active</div>
            </div>

            <div v-if="castLoading" class="loading-state mono">Loading cast from character_cast.json…</div>
            <div v-else-if="castError" class="error-state mono">{{ castError }}</div>
            <div v-else class="masonry-grid">
              <div
                v-for="agent in cast"
                :key="agent.name"
                class="profile-card"
                :class="{ 'agent-off': !agent._agentOn }"
              >
                <div class="profile-top">
                  <div class="profile-avatar-placeholder" :data-initials="initials(agent.name)" :style="{ background: stanceAvatarColor(agent.stance) }">
                    {{ initials(agent.name) }}
                  </div>
                  <div>
                    <div class="profile-name">{{ agent.name }}</div>
                    <div class="profile-role">{{ shortRole(agent.role) }}</div>
                  </div>
                </div>
                <div class="enneagram-badge mono" v-if="agent.enneagram">{{ agent.enneagram }}</div>
                <div class="pill-row">
                  <button
                    class="toggle-pill"
                    :class="{ off: !agent._agentOn }"
                    @click="agent._agentOn = !agent._agentOn"
                  >
                    {{ agent._agentOn ? 'AGENT ON' : 'AGENT OFF' }}
                  </button>
                  <button
                    class="toggle-pill stance-pill"
                    :class="agent.stance"
                    @click="cycleStance(agent)"
                  >
                    {{ agent.stance.toUpperCase() }}
                  </button>
                </div>
                <div class="influence-row">
                  <span class="session-label">INFLUENCE</span>
                  <div class="influence-track">
                    <div class="influence-fill" :style="{ width: (agent.influence_weight / 3.0 * 100) + '%' }"></div>
                  </div>
                  <span class="mono" style="font-size:11px;min-width:28px;text-align:right;">{{ agent.influence_weight }}x</span>
                </div>
              </div>
            </div>

            <!-- Excluded entities -->
            <div v-if="excluded.length" class="excluded-section">
              <div class="eyebrow mono" style="margin-bottom:10px;">EXCLUDED — DECEASED / REFERENCED ONLY</div>
              <div class="excluded-list">
                <div v-for="ex in excluded" :key="ex.name" class="excluded-chip mono">
                  {{ ex.name }} [DECEASED]
                </div>
              </div>
            </div>

            <div class="action-row">
              <button class="action-btn secondary" @click="saveCast">Save Cast</button>
              <button class="action-btn primary" @click="activePhase = 'build'">Advance to BUILD →</button>
            </div>
          </section>

        </div><!-- /page-left -->

        <!-- RIGHT PAGE -->
        <div class="page page-right">

          <!-- PHASE 03: BUILD -->
          <section v-show="activePhase === 'build'" class="section-card">
            <div class="section-heading-row">
              <div>
                <div class="eyebrow mono">PHASE 03 / BUILD</div>
                <div class="section-title serif">Live draft on the left, package outputs stacked right.</div>
              </div>
              <div class="toolbar-chip mono">{{ buildRunning ? 'generating…' : 'ready to build' }}</div>
            </div>

            <div class="build-split">
              <!-- markdown preview -->
              <div class="preview-pane">
                <div class="preview-toolbar">
                  <div class="session-value mono">upload_document.md</div>
                  <div class="toolbar-chip mono">{{ uploadDocPreview ? uploadDocPreview.length.toLocaleString() + ' chars' : 'not loaded' }}</div>
                </div>
                <div class="markdown-block mono" v-if="uploadDocPreview">
                  <div v-for="(line, i) in previewLines" :key="i" :class="{ 'markdown-line': line.startsWith('##') || line.startsWith('**') }">{{ line || '&nbsp;' }}</div>
                </div>
                <div class="empty-preview mono" v-else>Run BUILD to generate upload_document.md preview…</div>
              </div>

              <!-- output cards -->
              <div class="output-stack">
                <div
                  v-for="file in outputFiles"
                  :key="file.name"
                  class="output-card"
                  :class="{ ready: file.exists }"
                >
                  <div class="output-head">
                    <div class="session-value mono">{{ file.name }}</div>
                    <a
                      v-if="file.exists"
                      :href="`/api/prep/${slug}/download/${file.name}`"
                      class="download-badge"
                      download
                    >↓ download</a>
                    <div v-else class="download-badge pending">pending</div>
                  </div>
                  <div class="progress-track">
                    <div
                      class="progress-fill"
                      :class="file.colorClass"
                      :style="{ width: file.progress + '%', transition: 'width 0.8s ease' }"
                    ></div>
                  </div>
                  <div class="section-copy">{{ file.description }}</div>
                </div>
              </div>
            </div>

            <div class="action-row">
              <button class="action-btn primary" :disabled="buildRunning" @click="runBuild">
                {{ buildRunning ? 'Building…' : 'Run BUILD' }}
              </button>
              <button class="action-btn secondary" :disabled="!buildComplete" @click="activePhase = 'preflight'">
                Advance to PREFLIGHT →
              </button>
            </div>
          </section>

          <!-- PHASE 04: PREFLIGHT -->
          <section v-show="activePhase === 'preflight'" class="section-card">
            <div class="section-heading-row">
              <div>
                <div class="eyebrow mono">PHASE 04 / PREFLIGHT</div>
                <div class="section-title serif">Checklist left, budget and runtime right.</div>
              </div>
              <div
                class="status-banner mono"
                :class="{ pass: preflightResult?.overall === 'PASS', fail: preflightResult?.overall === 'FAIL' }"
                v-if="preflightResult"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path v-if="preflightResult.overall === 'PASS'" d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline v-if="preflightResult.overall === 'PASS'" points="22 4 12 14.01 9 11.01"/>
                  <circle v-else cx="12" cy="12" r="10"/><line v-if="preflightResult.overall !== 'PASS'" x1="15" y1="9" x2="9" y2="15"/><line v-if="preflightResult.overall !== 'PASS'" x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                PREFLIGHT {{ preflightResult.overall }}
              </div>
            </div>

            <div v-if="preflightLoading" class="loading-state mono">Running validation…</div>
            <div v-else-if="!preflightResult">
              <button class="action-btn primary" @click="runPreflight">Run PREFLIGHT</button>
            </div>
            <div v-else class="preflight-grid">

              <!-- Checklist -->
              <div class="checklist">
                <div class="rule-list">
                  <!-- Cast validation rules -->
                  <div
                    v-for="check in preflightResult.validation?.checks || []"
                    :key="check.rule + check.message"
                    class="rule-row"
                    :class="{ warning: check.status === 'WARN' }"
                  >
                    <div class="rule-main">
                      <svg v-if="check.status === 'PASS'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                      <svg v-else-if="check.status === 'WARN'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--destructive)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                      <div class="rule-text">{{ check.message }}</div>
                    </div>
                    <div class="rule-status mono" :class="check.status.toLowerCase()">{{ check.status }}</div>
                  </div>
                  <!-- Size checks -->
                  <div class="rule-row">
                    <div class="rule-main">
                      <svg :style="{ stroke: preflightResult.size_checks?.upload_under_50k ? 'var(--success)' : 'var(--destructive)' }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                      <div class="rule-text">upload_document.md under 50K chars ({{ preflightResult.size_checks?.upload_document_chars?.toLocaleString() }} / 50,000)</div>
                    </div>
                    <div class="rule-status mono" :class="preflightResult.size_checks?.upload_under_50k ? 'pass' : 'fail'">{{ preflightResult.size_checks?.upload_under_50k ? 'PASS' : 'FAIL' }}</div>
                  </div>
                  <div class="rule-row">
                    <div class="rule-main">
                      <svg :style="{ stroke: preflightResult.size_checks?.seed_under_5k ? 'var(--success)' : 'var(--destructive)' }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                      <div class="rule-text">reality_seed.md under 5K chars ({{ preflightResult.size_checks?.reality_seed_chars?.toLocaleString() }} / 5,000)</div>
                    </div>
                    <div class="rule-status mono" :class="preflightResult.size_checks?.seed_under_5k ? 'pass' : 'fail'">{{ preflightResult.size_checks?.seed_under_5k ? 'PASS' : 'FAIL' }}</div>
                  </div>
                  <!-- Pollution checks -->
                  <div class="rule-row">
                    <div class="rule-main">
                      <svg :style="{ stroke: preflightResult.pollution_clean ? 'var(--success)' : 'var(--destructive)' }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                      <div class="rule-text">
                        {{ preflightResult.pollution_clean ? 'No entity-polluting patterns detected' : 'Pollution patterns found: ' + preflightResult.pollution.map(p => p.pattern).join(', ') }}
                      </div>
                    </div>
                    <div class="rule-status mono" :class="preflightResult.pollution_clean ? 'pass' : 'fail'">{{ preflightResult.pollution_clean ? 'PASS' : 'FAIL' }}</div>
                  </div>
                </div>
              </div>

              <!-- Cost + runtime -->
              <div class="cost-card">
                <div class="eyebrow mono" style="margin-bottom:14px;">COST ESTIMATE</div>
                <div class="cost-table mono">
                  <div class="cost-row"><span>input tokens</span><span>${{ preflightResult.cost_estimate?.input_usd }}</span></div>
                  <div class="cost-row"><span>output tokens</span><span>${{ preflightResult.cost_estimate?.output_usd }}</span></div>
                  <div class="cost-row"><span>report generation</span><span>${{ preflightResult.cost_estimate?.report_usd }}</span></div>
                  <div class="cost-row total"><span>projected total</span><span>${{ preflightResult.cost_estimate?.total_usd }}</span></div>
                </div>
                <div class="runtime-band">
                  <div>
                    <div class="session-label">ESTIMATED SIMULATION COST</div>
                    <div class="session-value mono" style="color:var(--primary);">{{ preflightResult.cost_estimate?.agent_count }} agents × {{ preflightResult.cost_estimate?.duration_hours }}h</div>
                  </div>
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>

                <div class="upload-instructions">
                  <div class="eyebrow mono" style="margin-bottom:8px; margin-top:18px;">NEXT STEP</div>
                  <p class="section-copy">When preflight passes, click <strong>Launch Simulation</strong> to automatically ingest this package into MiroFish and start the simulation.</p>
                </div>
              </div>
            </div>

            <div v-if="preflightResult" class="action-row" style="margin-top:16px;">
              <button class="action-btn secondary" @click="runPreflight">Re-run PREFLIGHT</button>
              <button
                v-if="preflightResult.overall === 'PASS'"
                class="action-btn primary launch-btn"
                @click="goToLaunch"
              >
                🚀 Launch Simulation →
              </button>
            </div>
          </section>

          <!-- Default right-page content when left-page phases are active -->
          <section v-show="activePhase === 'ingest' || activePhase === 'cast'" class="section-card info-pane">
            <div class="eyebrow mono">PACKAGE OVERVIEW</div>
            <div class="section-title serif" style="font-size:22px; margin-top:8px;">What gets generated</div>
            <div class="output-stack" style="margin-top:20px;">
              <div v-for="file in outputFiles" :key="file.name" class="output-card" :class="{ ready: file.exists }">
                <div class="output-head">
                  <div class="session-value mono">{{ file.name }}</div>
                  <a v-if="file.exists" :href="`/api/prep/${slug}/download/${file.name}`" class="download-badge" download>↓</a>
                  <div v-else class="download-badge pending">pending</div>
                </div>
                <div class="section-copy">{{ file.description }}</div>
                <div class="progress-track">
                  <div class="progress-fill" :class="file.colorClass" :style="{ width: file.exists ? '100%' : '0%' }"></div>
                </div>
              </div>
            </div>
          </section>

        </div><!-- /page-right -->
      </div><!-- /notebook -->
    </main>
  </div>
</template>

<script>
export default {
  name: 'PrepView',
  props: {
    slug: { type: String, required: true },
  },

  data() {
    return {
      activePhase: 'ingest',

      phases: [
        { id: 'ingest',    label: 'INGEST',    meta: 'source docs',         badge: '' },
        { id: 'cast',      label: 'CAST',      meta: 'character profiles',  badge: '' },
        { id: 'build',     label: 'BUILD',     meta: 'generate outputs',    badge: '' },
        { id: 'preflight', label: 'PREFLIGHT', meta: 'validate + costs',    badge: '' },
      ],

      projectName: '',

      docs: [
        { id: 'bible',     label: 'Show Bible',              hint: 'Drop show bible, PDF, or fountain export',   accept: '.md,.txt,.pdf,.fountain', wide: false, loaded: false, filename: '', wordCount: 0, content: '', dragging: false },
        { id: 'synopsis',  label: 'Pilot Synopsis',          hint: 'Drop outline, treatment, or synopsis draft', accept: '.md,.txt,.pdf,.docx',     wide: false, loaded: false, filename: '', wordCount: 0, content: '', dragging: false },
        { id: 'protocol',  label: 'Interrogation Protocol',  hint: 'Prompt routines and interviewer constraints', accept: '.md,.txt',                wide: false, loaded: false, filename: '', wordCount: 0, content: '', dragging: false },
        { id: 'seed',      label: 'Seed Prompt',             hint: 'Core world seed, formatting rules, voice bias', accept: '.md,.txt',             wide: false, loaded: false, filename: '', wordCount: 0, content: '', dragging: false },
        { id: 'handoff',   label: 'Handoff Doc',             hint: 'Producer notes, decisions, phase log',       accept: '.md,.txt,.pdf',           wide: true,  loaded: false, filename: '', wordCount: 0, content: '', dragging: false },
      ],

      // Cast
      cast: [],
      excluded: [],
      castLoading: false,
      castError: null,

      // Build
      buildRunning: false,
      buildComplete: false,
      uploadDocPreview: null,
      outputFiles: [
        { name: 'upload_document.md',   description: 'Full character bible and world context for the MiroFish upload field.', exists: false, progress: 0, colorClass: 'success' },
        { name: 'reality_seed.md',      description: 'Concentrated simulation requirement — paste into Simulation Requirement field.', exists: false, progress: 0, colorClass: 'accent' },
        { name: 'simulation_config.json', description: 'Agent behavioral profiles, cost controls, and event configuration.', exists: false, progress: 0, colorClass: 'primary' },
        { name: 'event_seeds.json',     description: 'Eight inflection points seeded across the 168-hour arc.', exists: false, progress: 0, colorClass: 'primary' },
        { name: 'preflight_report.md',  description: 'Full validation report with cost breakdown and upload procedure.', exists: false, progress: 0, colorClass: 'muted' },
      ],

      // Preflight
      preflightLoading: false,
      preflightResult: null,

      stances: ['protagonist', 'antagonist', 'opposing', 'neutral'],
    }
  },

  computed: {
    totalWords() {
      return this.docs.reduce((s, d) => s + d.wordCount, 0)
    },
    loadedDocCount() {
      return this.docs.filter(d => d.loaded).length
    },
    allDocsLoaded() {
      return this.docs.every(d => d.loaded)
    },
    activeAgentCount() {
      return this.cast.filter(a => a._agentOn).length
    },
    packageState() {
      if (this.preflightResult?.overall === 'PASS') return 'Ready for upload'
      if (this.buildComplete) return 'Ready for preflight'
      if (this.cast.length) return 'Cast approved'
      if (this.loadedDocCount > 0) return 'Ingesting docs'
      return 'Awaiting documents'
    },
    packageStateColor() {
      if (this.preflightResult?.overall === 'PASS') return 'var(--success)'
      if (this.buildComplete) return 'var(--accent)'
      return 'var(--foreground)'
    },
    previewLines() {
      if (!this.uploadDocPreview) return []
      return this.uploadDocPreview.split('\n').slice(0, 30)
    },
  },

  mounted() {
    this.loadProjectMeta()
    this.loadCast()
    this.checkOutputFiles()
    this.updateBadges()
  },

  methods: {
    async loadProjectMeta() {
      try {
        const res = await fetch(`/api/prep/${this.slug}/meta`)
        if (res.ok) {
          const meta = await res.json()
          this.projectName = meta.name || this.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        } else {
          this.projectName = this.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        }
      } catch {
        this.projectName = this.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      }
    },

    updateBadges() {
      this.phases[0].badge = this.loadedDocCount ? `${this.loadedDocCount}/5` : ''
      this.phases[1].badge = this.cast.length ? `${this.activeAgentCount} agents` : ''
      this.phases[2].badge = this.buildComplete ? '5 files' : ''
      this.phases[3].badge = this.preflightResult?.overall || ''
    },

    // ── INGEST ─────────────────────────────────────────────────
    triggerFileInput(doc) {
      const input = this.$refs['fileInput_' + doc.id]
      if (input) (Array.isArray(input) ? input[0] : input).click()
    },

    onFileDrop(event, doc) {
      doc.dragging = false
      const file = event.dataTransfer.files[0]
      if (file) this.processFile(file, doc)
    },

    onFileInputChange(event, doc) {
      const file = event.target.files[0]
      if (file) this.processFile(file, doc)
    },

    async processFile(file, doc) {
      doc.filename = file.name
      const text = await file.text()
      doc.content = text
      // Get word count from backend or locally
      try {
        const res = await fetch(`/api/prep/${this.slug}/parse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: text }),
        })
        if (res.ok) {
          const data = await res.json()
          doc.wordCount = data.word_count
        } else {
          doc.wordCount = text.split(/\s+/).filter(Boolean).length
        }
      } catch {
        doc.wordCount = text.split(/\s+/).filter(Boolean).length
      }
      doc.loaded = true
      this.updateBadges()
    },

    // ── CAST ───────────────────────────────────────────────────
    async loadCast() {
      this.castLoading = true
      this.castError = null
      try {
        const res = await fetch(`/api/prep/${this.slug}/cast`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const agents = data.mandatory_agents || []
        this.cast = agents.map(a => ({ ...a, _agentOn: true }))
        this.excluded = data.excluded_entities || []
        this.updateBadges()
      } catch (e) {
        this.castError = `Could not load cast: ${e.message}. Make sure the backend is running.`
      } finally {
        this.castLoading = false
      }
    },

    async saveCast() {
      const payload = {
        mandatory_agents: this.cast.map(a => {
          const { _agentOn, ...rest } = a
          return rest
        }),
        excluded_entities: this.excluded,
      }
      try {
        await fetch(`/api/prep/${this.slug}/cast`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch (e) {
        console.error('Save cast failed:', e)
      }
    },

    cycleStance(agent) {
      const i = this.stances.indexOf(agent.stance)
      agent.stance = this.stances[(i + 1) % this.stances.length]
    },

    initials(name) {
      return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    },

    stanceAvatarColor(stance) {
      const map = {
        protagonist: 'rgba(107,143,113,0.25)',
        antagonist:  'rgba(185,75,75,0.25)',
        opposing:    'rgba(232,200,122,0.35)',
        neutral:     'rgba(110,104,94,0.15)',
      }
      return map[stance] || map.neutral
    },

    shortRole(role) {
      return role.length > 60 ? role.slice(0, 57) + '…' : role
    },

    // ── BUILD ──────────────────────────────────────────────────
    async runBuild() {
      this.buildRunning = true
      // Animate progress bars
      this.outputFiles.forEach((f, i) => {
        setTimeout(() => { f.progress = 30 + Math.random() * 40 }, i * 300)
      })
      try {
        const res = await fetch(`/api/prep/${this.slug}/build`, { method: 'POST' })
        const data = await res.json()
        // Update file statuses
        for (const file of this.outputFiles) {
          const info = data.files?.[file.name]
          if (info?.exists) {
            file.exists = true
            file.progress = 100
          }
        }
        this.buildComplete = true
        // Load preview of upload_document
        await this.loadUploadDocPreview()
        this.updateBadges()
      } catch (e) {
        console.error('Build failed:', e)
      } finally {
        this.buildRunning = false
      }
    },

    async loadUploadDocPreview() {
      try {
        const res = await fetch(`/api/prep/${this.slug}/download/upload_document.md`)
        if (res.ok) {
          this.uploadDocPreview = await res.text()
        }
      } catch {}
    },

    async checkOutputFiles() {
      try {
        const res = await fetch(`/api/prep/${this.slug}/files`)
        if (!res.ok) return
        const data = await res.json()
        let anyExists = false
        for (const file of this.outputFiles) {
          const info = data.files?.[file.name]
          if (info?.exists) {
            file.exists = true
            file.progress = 100
            anyExists = true
          }
        }
        if (anyExists) {
          this.buildComplete = true
          await this.loadUploadDocPreview()
          this.updateBadges()
        }
      } catch {}
    },

    // ── PREFLIGHT ──────────────────────────────────────────────
    async runPreflight() {
      this.preflightLoading = true
      this.preflightResult = null
      try {
        const res = await fetch(`/api/prep/${this.slug}/validate`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        this.preflightResult = await res.json()
        this.updateBadges()
      } catch (e) {
        this.preflightResult = { overall: 'ERROR', error: e.message }
      } finally {
        this.preflightLoading = false
      }
    },

    goToLaunch() {
      this.$router.push(`/project/${this.slug}/launch`)
    },
  },
}
</script>

<style scoped>
/* ── TOKENS ─────────────────────────────────────────────────── */
.prep-workspace {
  --background:  #FAFAF7;
  --foreground:  #1A1A1A;
  --border:      #DDD8CC;
  --primary:     #6B8F71;
  --secondary:   #F3EFE3;
  --muted:       #F6F3EA;
  --muted-fg:    #6E685E;
  --success:     #6B8F71;
  --accent:      #E8C87A;
  --accent-fg:   #1A1A1A;
  --destructive: #B94B4B;
  --card:        #FFFDF8;
  --radius-sm:   4px;
  --radius-md:   6px;
  --radius-lg:   8px;

  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--background);
  color: var(--foreground);
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
}

/* ── TYPOGRAPHY ─────────────────────────────────────────────── */
.mono  { font-family: 'JetBrains Mono', 'Fira Mono', 'Courier New', monospace; }
.serif { font-family: Georgia, 'Times New Roman', serif; }

/* ── HEADER ─────────────────────────────────────────────────── */
.prep-header {
  padding: 24px 36px 18px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(to bottom, var(--card), var(--background));
  flex-shrink: 0;
}

.header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.brand-block { display: flex; align-items: center; gap: 12px; }

.brand-mark {
  width: 36px; height: 36px;
  border-radius: var(--radius-md);
  background: var(--secondary);
  color: var(--primary);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.brand-title  { font-size: 14px; font-weight: 700; letter-spacing: .09em; }
.brand-subtitle { font-size: 12px; color: var(--muted-fg); margin-top: 2px; }

.session-strip { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.session-stat  { display: flex; flex-direction: column; gap: 3px; }
.session-label { font-size: 10px; color: var(--muted-fg); letter-spacing: .09em; }
.session-value { font-size: 13px; font-weight: 600; }

/* stepper */
.stepper {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.step-tab {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  cursor: pointer;
  transition: all 150ms ease;
  text-align: left;
}
.step-tab:hover  { border-color: var(--primary); }
.step-tab.active { background: var(--secondary); border-color: var(--accent); }

.step-left { display: flex; align-items: center; gap: 10px; }
.step-index {
  width: 22px; height: 22px;
  border-radius: 999px;
  background: var(--muted);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; flex-shrink: 0;
}
.step-tab.active .step-index { background: var(--accent); color: var(--accent-fg); }
.step-name { font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.step-meta { font-size: 11px; color: var(--muted-fg); }
.step-badge { font-size: 11px; color: var(--muted-fg); white-space: nowrap; }

/* ── BODY / NOTEBOOK ────────────────────────────────────────── */
.prep-body {
  flex: 1;
  padding: 24px 36px 36px;
  overflow: auto;
}

.notebook {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: calc(100vh - 220px);
  overflow: hidden;
  box-shadow: 0 2px 16px rgba(26,26,26,.06);
}

.page {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: linear-gradient(to bottom, rgba(243,239,227,.4), rgba(255,253,248,.95));
}

.page-left  { border-right: 1px solid var(--border); }

.section-card {
  background: rgba(255,255,255,.55);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow      { font-size: 10px; letter-spacing: .1em; color: var(--muted-fg); }
.section-title { font-size: 22px; line-height: 1.2; font-weight: 600; margin-top: 4px; }
.section-copy  { font-size: 13px; line-height: 1.6; color: var(--muted-fg); }

/* ── DOC GRID (INGEST) ─────────────────────────────────────── */
.doc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.doc-card {
  min-height: 148px;
  background: var(--card);
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  cursor: pointer;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.doc-card:hover   { border-color: var(--primary); box-shadow: 0 4px 12px rgba(107,143,113,.12); }
.doc-card.loaded  { border-style: solid; border-color: var(--primary); }
.doc-card.dragging { border-color: var(--accent); background: rgba(232,200,122,.08); }
.doc-card.wide    { grid-column: 1 / span 2; min-height: 100px; }

.doc-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.doc-icon-wrap {
  width: 32px; height: 32px;
  border-radius: var(--radius-md);
  background: var(--secondary);
  color: var(--primary);
  display: flex; align-items: center; justify-content: center;
}

.doc-state-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--muted);
  color: var(--muted-fg);
  font-size: 11px; font-weight: 600;
}
.doc-state-pill.loaded { background: rgba(107,143,113,.15); color: var(--primary); }

.doc-state {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--muted);
  color: var(--muted-fg);
  font-size: 11px; font-weight: 600;
}
.doc-state.ready { background: rgba(107,143,113,.15); color: var(--primary); }

.doc-title { font-size: 14px; font-weight: 600; margin-top: 10px; }
.drop-zone {
  margin-top: 8px;
  min-height: 40px;
  border-radius: var(--radius-sm);
  background: var(--muted);
  display: flex; align-items: center; justify-content: center;
  padding: 8px;
  font-size: 11px; color: var(--muted-fg); text-align: center;
}

.doc-footer {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; margin-top: 10px;
}

.filename-badge {
  display: inline-flex; align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--secondary);
  font-size: 11px;
  max-width: 140px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.filename-badge.empty { color: var(--muted-fg); }

.count-badge { font-size: 11px; color: var(--primary); white-space: nowrap; }

/* ── CAST ───────────────────────────────────────────────────── */
.masonry-grid { column-count: 2; column-gap: 12px; }

.profile-card {
  break-inside: avoid;
  margin-bottom: 12px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  display: flex; flex-direction: column; gap: 10px;
  transition: opacity 200ms ease;
}
.profile-card.agent-off { opacity: .5; }

.profile-top { display: flex; align-items: center; gap: 10px; }

.profile-avatar-placeholder {
  width: 38px; height: 38px;
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; flex-shrink: 0;
  color: var(--foreground);
}

.profile-name { font-size: 14px; font-weight: 600; line-height: 1.2; }
.profile-role { font-size: 12px; color: var(--muted-fg); line-height: 1.4; margin-top: 2px; }

.enneagram-badge {
  display: inline-flex;
  width: fit-content;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--muted);
  font-size: 11px;
}

.pill-row { display: flex; flex-wrap: wrap; gap: 6px; }

.toggle-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--secondary);
  font-size: 11px; font-weight: 600;
  cursor: pointer;
  transition: all 150ms ease;
  font-family: inherit;
}
.toggle-pill:hover { border-color: var(--primary); }
.toggle-pill.off   { background: var(--muted); color: var(--muted-fg); }

.stance-pill.protagonist { background: rgba(107,143,113,.18); color: var(--primary);     border-color: rgba(107,143,113,.3); }
.stance-pill.antagonist  { background: rgba(185,75,75,.12);   color: var(--destructive); border-color: rgba(185,75,75,.3);   }
.stance-pill.opposing    { background: rgba(232,200,122,.28); color: #8B6914;             border-color: rgba(232,200,122,.5); }
.stance-pill.neutral     { background: var(--muted);           color: var(--muted-fg);    border-color: var(--border);        }

.influence-row {
  display: flex; align-items: center; gap: 8px;
}
.influence-track {
  flex: 1; height: 5px;
  border-radius: 999px;
  background: var(--muted);
  overflow: hidden;
}
.influence-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 999px;
  transition: width 400ms ease;
}

.excluded-section { margin-top: 4px; }
.excluded-list    { display: flex; flex-wrap: wrap; gap: 8px; }
.excluded-chip {
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(185,75,75,.1);
  color: var(--destructive);
  font-size: 11px;
  border: 1px solid rgba(185,75,75,.2);
}

/* ── BUILD ──────────────────────────────────────────────────── */
.build-split {
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: 14px;
  flex: 1;
}

.preview-pane {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex; flex-direction: column; gap: 10px;
  overflow: hidden;
}
.preview-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.toolbar-chip {
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--secondary);
  font-size: 10px; color: var(--muted-fg);
}

.markdown-block {
  display: flex; flex-direction: column; gap: 6px;
  font-size: 11px; line-height: 1.6; overflow: hidden;
  max-height: 280px;
}
.markdown-line {
  padding-left: 8px;
  border-left: 2px solid var(--accent);
}
.empty-preview { font-size: 12px; color: var(--muted-fg); padding: 20px 0; text-align: center; }

.output-stack { display: flex; flex-direction: column; gap: 10px; }

.output-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex; flex-direction: column; gap: 8px;
  transition: border-color 200ms ease;
}
.output-card.ready { border-color: rgba(107,143,113,.4); }

.output-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }

.download-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--secondary);
  color: var(--primary);
  text-decoration: none;
  white-space: nowrap;
  font-family: 'JetBrains Mono', monospace;
}
.download-badge.pending { color: var(--muted-fg); }
.download-badge:hover:not(.pending) { background: rgba(107,143,113,.2); }

.progress-track {
  height: 5px;
  border-radius: 999px;
  background: var(--muted);
  overflow: hidden;
}
.progress-fill              { height: 100%; border-radius: 999px; background: var(--primary); }
.progress-fill.success      { background: var(--success); }
.progress-fill.accent       { background: var(--accent); }
.progress-fill.primary      { background: var(--primary); }
.progress-fill.muted        { background: var(--muted-fg); }

/* ── PREFLIGHT ──────────────────────────────────────────────── */
.preflight-grid {
  display: grid;
  grid-template-columns: 1fr 200px;
  gap: 14px;
}

.checklist, .cost-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
}

.rule-list  { display: flex; flex-direction: column; gap: 10px; }
.rule-row {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.rule-row:last-child           { padding-bottom: 0; border-bottom: none; }
.rule-row.warning .rule-text   { color: var(--muted-fg); font-size: 12px; }
.rule-main  { display: flex; align-items: flex-start; gap: 8px; overflow: hidden; flex: 1; }
.rule-text  { font-size: 12px; line-height: 1.4; }
.rule-status { font-size: 11px; font-weight: 700; white-space: nowrap; flex-shrink: 0; }
.rule-status.pass { color: var(--success); }
.rule-status.fail { color: var(--destructive); }
.rule-status.warn { color: #8B6914; }

.cost-table { display: flex; flex-direction: column; gap: 10px; }
.cost-row   { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 12px; }
.cost-row.total { padding-top: 10px; border-top: 1px solid var(--border); font-weight: 700; }

.runtime-band {
  margin-top: 14px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--secondary);
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px;
}

.status-banner {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(107,143,113,.16);
  color: var(--primary);
  font-size: 11px; font-weight: 700;
  white-space: nowrap;
}
.status-banner.fail {
  background: rgba(185,75,75,.12);
  color: var(--destructive);
}

.upload-instructions { border-top: 1px solid var(--border); padding-top: 14px; }
.instructions-list   { padding-left: 16px; display: flex; flex-direction: column; gap: 6px; font-size: 11px; color: var(--muted-fg); }
.instructions-list code { background: var(--muted); padding: 1px 4px; border-radius: 3px; font-size: 10px; }

/* ── SHARED CONTROLS ────────────────────────────────────────── */
.action-btn {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 13px; font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 150ms ease;
  font-family: inherit;
}
.action-btn.primary {
  background: var(--primary);
  color: white;
}
.action-btn.primary:hover:not(:disabled) { background: #5a7a60; transform: translateY(-1px); }
.action-btn.primary:disabled             { opacity: .45; cursor: not-allowed; }

.action-btn.secondary {
  background: var(--secondary);
  color: var(--foreground);
  border: 1px solid var(--border);
}
.action-btn.secondary:hover { border-color: var(--primary); }

.action-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.loading-state { font-size: 13px; color: var(--muted-fg); padding: 20px 0; text-align: center; animation: pulse 1.5s ease-in-out infinite; }
.error-state   { font-size: 13px; color: var(--destructive); padding: 16px; background: rgba(185,75,75,.08); border-radius: var(--radius-md); }

.info-pane { opacity: .9; }

@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .5; } }
</style>

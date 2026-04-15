<template>
  <div class="prep-workspace">

    <!-- ── HEADER ─────────────────────────────────────────────────── -->
    <header class="prep-header">
      <div class="header-top">
        <div class="brand-block">
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
            <div class="session-value mono">{{ activeProject || '—' }}</div>
          </div>
          <div class="session-stat">
            <div class="session-label">SOURCES</div>
            <div class="session-value mono">{{ loadedDocCount }}/3</div>
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
          <div class="step-badge mono">{{ phaseBadges[phase.id] }}</div>
        </button>
      </div>
    </header>

    <!-- ── BODY ───────────────────────────────────────────────────── -->
    <main class="prep-body">
      <div class="notebook">

        <!-- LEFT PAGE -->
        <div class="page page-left">

          <!-- PHASE 00: PROJECT -->
          <section v-show="activePhase === 'project'" class="section-card">
            <div class="section-heading-row">
              <div>
                <div class="eyebrow mono">PHASE 00 / PROJECT</div>
                <div class="section-title serif">Pick an existing project or create a new one.</div>
              </div>
              <div class="doc-state mono" :class="{ ready: !!activeProject }">
                {{ activeProject ? `active: ${activeProject}` : 'no project selected' }}
              </div>
            </div>
            <p class="section-copy">Each project gets its own folder under <code>sim-prep/&lt;slug&gt;/</code> with separate sources, drafts, and promoted artifacts.</p>

            <div v-if="projectsLoading" class="loading-state mono">Loading projects…</div>
            <div v-else-if="projectError" class="error-state mono">{{ projectError }}</div>
            <div v-else>
              <div class="project-grid">
                <div
                  v-for="p in projects"
                  :key="p.slug"
                  class="project-card"
                  :class="{ active: activeProject === p.slug }"
                  @click="selectProject(p.slug)"
                >
                  <div class="project-name serif">{{ p.name }}</div>
                  <div class="project-slug mono">{{ p.slug }}</div>
                  <div class="project-meta mono">
                    <span v-if="p.has_cast" class="pm-pill pm-on">cast</span>
                    <span v-if="p.has_upload_doc" class="pm-pill pm-on">upload</span>
                    <span v-if="p.has_reality_seed" class="pm-pill pm-on">seed</span>
                    <span v-if="p.has_config" class="pm-pill pm-on">config</span>
                    <span v-if="p.has_event_seeds" class="pm-pill pm-on">events</span>
                    <span v-if="p.source_count" class="pm-pill">{{ p.source_count }} src</span>
                  </div>
                </div>
                <div class="project-card new" @click="$refs.newProjectInput.focus()">
                  <div class="project-new-label mono">+ New project</div>
                  <input
                    ref="newProjectInput"
                    v-model="newProjectName"
                    class="project-new-input mono"
                    placeholder="e.g. Oro Verde S2"
                    @keyup.enter="createProject"
                    @click.stop
                  />
                  <button
                    class="action-btn secondary sm"
                    :disabled="!newProjectName.trim() || creatingProject"
                    @click.stop="createProject"
                  >
                    {{ creatingProject ? 'creating…' : 'create' }}
                  </button>
                </div>
              </div>
            </div>

            <button
              class="action-btn primary"
              :disabled="!activeProject"
              @click="activePhase = 'ingest'"
            >
              Advance to INGEST →
            </button>
          </section>

          <!-- PHASE 01: INGEST -->
          <section v-show="activePhase === 'ingest'" class="section-card">
            <div class="section-heading-row">
              <div>
                <div class="eyebrow mono">PHASE 01 / INGEST</div>
                <div class="section-title serif">Source documents for AI to read.</div>
              </div>
              <div class="doc-state mono" :class="{ ready: anyDocLoaded }">
                <svg v-if="anyDocLoaded" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                {{ loadedDocCount }}/3 loaded
              </div>
            </div>
            <p class="section-copy">Drop 1-3 raw source documents (script, bible, treatment — PDF, MD, or TXT). Server-side text extraction handles PDFs. AI will read these in the next phase to extract the character cast.</p>

            <div v-if="!activeProject" class="error-state mono">
              Select a project first (Phase 00).
            </div>

            <div class="doc-grid three-col" v-else>
              <div
                v-for="doc in docs"
                :key="doc.id"
                class="doc-card"
                :class="{ loaded: doc.loaded, dragging: doc.dragging, uploading: doc.uploading, errored: !!doc.error }"
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
                      <svg v-if="doc.uploading" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="spin"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/></svg>
                      <svg v-else-if="doc.loaded" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                      {{ doc.uploading ? 'uploading' : (doc.loaded ? 'loaded' : 'empty') }}
                    </div>
                  </div>
                  <div class="doc-title">{{ doc.label }}</div>
                  <div class="drop-zone mono">{{ doc.loaded ? doc.filename : doc.hint }}</div>
                  <div v-if="doc.error" class="doc-error mono">{{ doc.error }}</div>
                </div>
                <div class="doc-footer">
                  <div class="filename-badge mono" v-if="doc.loaded">{{ doc.filename }}</div>
                  <div class="filename-badge mono empty" v-else>Drop file or click</div>
                  <div class="count-badge mono" v-if="doc.loaded">{{ doc.charCount.toLocaleString() }} chars</div>
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

            <div v-if="analyzeResult" class="analyze-panel mono">
              <div class="eyebrow mono">DOCUMENT ANALYSIS</div>
              <pre class="analyze-json">{{ JSON.stringify(analyzeResult, null, 2).slice(0, 2000) }}</pre>
            </div>

            <div class="action-row">
              <button
                class="action-btn secondary"
                :disabled="!anyDocLoaded || analyzing"
                @click="analyzeSources"
              >
                {{ analyzing ? 'Analyzing…' : 'Analyze documents' }}
              </button>
              <button
                class="action-btn primary"
                :disabled="!anyDocLoaded"
                @click="activePhase = 'cast'"
              >
                Advance to CAST →
              </button>
            </div>
          </section>

          <!-- PHASE 02: CAST -->
          <section v-show="activePhase === 'cast'" class="section-card">
            <div class="section-heading-row">
              <div>
                <div class="eyebrow mono">PHASE 02 / CAST</div>
                <div class="section-title serif">AI extracts characters from your sources.</div>
              </div>
              <div class="toolbar-chip mono">{{ activeAgentCount }} agents active</div>
            </div>

            <!-- AI extraction panel -->
            <div class="ai-panel">
              <div class="ai-panel-top">
                <div>
                  <div class="eyebrow mono">AI CHARACTER EXTRACTION</div>
                  <p class="section-copy" style="margin-top:4px;">
                    Reads your source documents, extracts every named character, applies validation-in-loop
                    (blocks generic nouns, organizations, dead-as-active, group agents), retries up to 2× on failure.
                  </p>
                </div>
                <button
                  class="action-btn primary"
                  :disabled="aiCastExtracting || !activeProject"
                  @click="extractCastViaAI"
                >
                  {{ aiCastExtracting ? 'Extracting…' : (cast.length ? 'Re-extract' : 'Extract characters') }}
                </button>
              </div>

              <div v-if="aiCastExtracting" class="loading-state mono">
                AI is reading your materials and extracting characters…
              </div>

              <div v-if="aiCastResult" class="ai-result mono">
                <div class="ai-result-row">
                  <span class="session-label">AGENTS EXTRACTED</span>
                  <span class="session-value">{{ aiCastResult.agent_count }}</span>
                </div>
                <div class="ai-result-row" v-if="aiCastResult.validation">
                  <span class="session-label">VALIDATION</span>
                  <span class="session-value" :style="{ color: aiCastResult.validation.failures === 0 ? 'var(--success)' : 'var(--destructive)' }">
                    {{ aiCastResult.validation.failures }} failures · {{ aiCastResult.validation.warnings }} warnings
                  </span>
                </div>
                <div v-if="aiCastResult.cast?._validation_warnings" class="ai-warning mono">
                  ⚠ {{ aiCastResult.cast._validation_warnings }}
                </div>
                <div v-if="aiCastResult.validation?.checks?.length" class="ai-checks">
                  <div
                    v-for="(chk, i) in aiCastResult.validation.checks.filter(c => c.status !== 'PASS')"
                    :key="i"
                    class="ai-check-row"
                    :class="chk.status.toLowerCase()"
                  >
                    [{{ chk.status }}] {{ chk.rule }}: {{ chk.message }}
                  </div>
                </div>
                <button
                  v-if="aiCastResult.ready_to_promote"
                  class="action-btn primary sm"
                  :disabled="castPromoting"
                  style="margin-top:10px;"
                  @click="promoteCast"
                >
                  {{ castPromoting ? 'promoting…' : 'Promote to canonical character_cast.json' }}
                </button>
              </div>
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
                <div class="section-title serif">AI generates each artifact. Promote when ready.</div>
              </div>
              <div class="toolbar-chip mono">{{ allArtifactsPromoted ? 'all promoted' : 'in progress' }}</div>
            </div>

            <p class="section-copy">
              Each artifact is generated by AI into a <code>_draft/</code> file, then reviewed and promoted to canonical.
              Canonical files are what MiroFish receives. <strong>character_cast.json must be promoted first</strong>
              (it's the input to the other generators).
            </p>

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
                <div class="empty-preview mono" v-else>Generate upload_document.md to preview…</div>
              </div>

              <!-- per-artifact generate/promote cards -->
              <div class="output-stack">
                <div
                  v-for="art in artifactKinds"
                  :key="art.kind"
                  class="output-card"
                  :class="{ ready: artifactStatus[art.kind]?.hasCanonical }"
                >
                  <div class="output-head">
                    <div class="session-value mono">{{ art.filename }}</div>
                    <span class="status-chip mono" :class="artifactStatusClass(art.kind)">
                      {{ artifactStatusLabel(art.kind) }}
                    </span>
                  </div>
                  <div class="section-copy">{{ art.description }}</div>
                  <div class="artifact-actions">
                    <button
                      class="action-btn secondary sm"
                      :disabled="artifactStatus[art.kind]?.generating || !activeProject"
                      @click="generateArtifact(art.kind)"
                    >
                      {{ artifactStatus[art.kind]?.generating ? 'generating…' : (artifactStatus[art.kind]?.hasDraft ? 'regenerate' : 'generate') }}
                    </button>
                    <button
                      v-if="art.kind !== 'config'"
                      class="action-btn primary sm"
                      :disabled="!artifactStatus[art.kind]?.hasDraft || artifactStatus[art.kind]?.promoting"
                      @click="promoteArtifact(art.kind)"
                    >
                      {{ artifactStatus[art.kind]?.promoting ? 'promoting…' : 'promote' }}
                    </button>
                    <a
                      v-if="artifactStatus[art.kind]?.hasCanonical"
                      :href="`${apiBase}/download/${art.filename}`"
                      class="download-badge"
                      download
                    >↓</a>
                  </div>
                  <div v-if="artifactStatus[art.kind]?.error" class="artifact-error mono">
                    {{ artifactStatus[art.kind].error }}
                  </div>
                </div>
              </div>
            </div>

            <div class="action-row">
              <button class="action-btn secondary" @click="activePhase = 'preflight'">
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
                    <div class="session-label">VS SEASON 1 ACTUAL ($450)</div>
                    <div class="session-value mono" style="color:var(--primary);">{{ preflightResult.cost_estimate?.vs_s1_pct }}% of S1 cost</div>
                  </div>
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>

                <div class="upload-instructions">
                  <div class="eyebrow mono" style="margin-bottom:8px; margin-top:18px;">UPLOAD PROCEDURE</div>
                  <ol class="instructions-list mono">
                    <li>Paste <strong>upload_document.md</strong> → Source Material field</li>
                    <li>Paste <strong>reality_seed.md</strong> → Simulation Requirement field</li>
                    <li>Upload <strong>simulation_config.json</strong> as configuration</li>
                    <li>Set 168 hours · Spanish · 12 mandatory agents</li>
                    <li>Confirm <code>message_window_size=50</code>, <code>token_limit=150000</code></li>
                  </ol>
                </div>
              </div>
            </div>

            <div v-if="preflightResult" class="action-row" style="margin-top:16px;">
              <button class="action-btn secondary" @click="runPreflight">Re-run PREFLIGHT</button>
            </div>
          </section>

          <!-- Default right-page content when left-page phases are active -->
          <section v-show="activePhase === 'project' || activePhase === 'ingest' || activePhase === 'cast'" class="section-card info-pane">
            <div class="eyebrow mono">PACKAGE OVERVIEW</div>
            <div class="section-title serif" style="font-size:22px; margin-top:8px;">What gets generated</div>
            <div class="output-stack" style="margin-top:20px;">
              <div v-for="art in artifactKinds" :key="art.kind" class="output-card" :class="{ ready: artifactStatus[art.kind]?.hasCanonical }">
                <div class="output-head">
                  <div class="session-value mono">{{ art.filename }}</div>
                  <a v-if="artifactStatus[art.kind]?.hasCanonical" :href="`${apiBase}/download/${art.filename}`" class="download-badge" download>↓</a>
                  <div v-else class="download-badge pending">pending</div>
                </div>
                <div class="section-copy">{{ art.description }}</div>
                <div class="progress-track">
                  <div class="progress-fill" :class="art.colorClass" :style="{ width: artifactStatus[art.kind]?.hasCanonical ? '100%' : (artifactStatus[art.kind]?.hasDraft ? '60%' : '0%') }"></div>
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

  data() {
    return {
      activePhase: 'project',

      phases: [
        { id: 'project',   label: 'PROJECT',   meta: 'pick or create' },
        { id: 'ingest',    label: 'INGEST',    meta: 'source docs' },
        { id: 'cast',      label: 'CAST',      meta: 'AI extraction' },
        { id: 'build',     label: 'BUILD',     meta: 'AI generation' },
        { id: 'preflight', label: 'PREFLIGHT', meta: 'validate + costs' },
      ],

      // Project picker (Phase 0)
      activeProject: null,          // slug string once selected
      projects: [],
      projectsLoading: false,
      newProjectName: '',
      creatingProject: false,
      projectError: null,

      // Ingest — 3 dynamic upload slots (was 5 hardcoded)
      docs: [
        { id: 'source1', label: 'Source Document 1', hint: 'Drop a script, bible, treatment — PDF, MD, or TXT', accept: '.pdf,.md,.markdown,.txt', loaded: false, filename: '', charCount: 0, wordCount: 0, uploading: false, dragging: false, error: null },
        { id: 'source2', label: 'Source Document 2', hint: 'Optional: second source document',                  accept: '.pdf,.md,.markdown,.txt', loaded: false, filename: '', charCount: 0, wordCount: 0, uploading: false, dragging: false, error: null },
        { id: 'source3', label: 'Source Document 3', hint: 'Optional: third source document',                   accept: '.pdf,.md,.markdown,.txt', loaded: false, filename: '', charCount: 0, wordCount: 0, uploading: false, dragging: false, error: null },
      ],
      analyzeResult: null,
      analyzing: false,

      // Cast
      cast: [],
      excluded: [],
      castLoading: false,
      castError: null,
      aiCastExtracting: false,
      aiCastResult: null,           // { cast, agent_count, validation, ready_to_promote }
      castPromoting: false,

      // Build — per-artifact status
      uploadDocPreview: null,
      artifactKinds: [
        { kind: 'upload-document', filename: 'upload_document.md',    description: 'Curated document for MiroFish Source Material field. Starts with CHARACTER INDEX.', colorClass: 'success' },
        { kind: 'reality-seed',    filename: 'reality_seed.md',       description: 'Focused simulation prompt — pasted into Simulation Requirement field.',           colorClass: 'accent'  },
        { kind: 'event-seeds',     filename: 'event_seeds.json',      description: '6-8 narrative shocks mapped to simulation hours.',                                colorClass: 'primary' },
        { kind: 'config',          filename: 'simulation_config.json', description: 'Behavioral profiles + cost controls (message_window_size=50, token_limit=150000).', colorClass: 'primary' },
      ],
      artifactStatus: {},           // keyed by kind: { generating, promoting, preview, charCount, hasCanonical, hasDraft, error }

      // Preflight
      preflightLoading: false,
      preflightResult: null,

      stances: ['protagonist', 'antagonist', 'opposing', 'neutral', 'supporting'],
    }
  },

  computed: {
    loadedDocCount() {
      return this.docs.filter(d => d.loaded).length
    },
    anyDocLoaded() {
      return this.docs.some(d => d.loaded)
    },
    activeAgentCount() {
      return this.cast.filter(a => a._agentOn !== false).length
    },
    allArtifactsPromoted() {
      return this.artifactKinds.every(a => this.artifactStatus[a.kind]?.hasCanonical)
    },
    phaseBadges() {
      const promoted = this.artifactKinds.filter(a => this.artifactStatus[a.kind]?.hasCanonical).length
      return {
        project:   this.activeProject || '',
        ingest:    this.loadedDocCount ? `${this.loadedDocCount}/3` : '',
        cast:      this.cast.length ? `${this.activeAgentCount} agents` : '',
        build:     promoted ? `${promoted}/${this.artifactKinds.length}` : '',
        preflight: this.preflightResult?.overall || '',
      }
    },
    packageState() {
      if (!this.activeProject) return 'No project selected'
      if (this.preflightResult?.overall === 'PASS') return 'Ready for upload'
      if (this.allArtifactsPromoted) return 'Ready for preflight'
      if (this.cast.length) return 'Cast approved'
      if (this.anyDocLoaded) return 'Ingesting docs'
      return 'Awaiting documents'
    },
    packageStateColor() {
      if (this.preflightResult?.overall === 'PASS') return 'var(--success)'
      if (this.allArtifactsPromoted) return 'var(--accent)'
      return 'var(--foreground)'
    },
    previewLines() {
      if (!this.uploadDocPreview) return []
      return this.uploadDocPreview.split('\n').slice(0, 30)
    },
    apiBase() {
      return this.activeProject ? `/api/prep/${this.activeProject}` : '/api/prep'
    },
  },

  mounted() {
    this.loadProjects()
    const saved = localStorage.getItem('prepActiveProject')
    if (saved) {
      this.activeProject = saved
    }
  },

  watch: {
    activeProject(slug) {
      if (slug) {
        localStorage.setItem('prepActiveProject', slug)
        // When a project is selected, load its state
        this.loadProjectState()
      } else {
        localStorage.removeItem('prepActiveProject')
      }
    },
  },

  methods: {
    // ── PROJECT PICKER ─────────────────────────────────────────
    async loadProjects() {
      this.projectsLoading = true
      this.projectError = null
      try {
        const res = await fetch('/api/prep/projects')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        this.projects = data.projects || []
      } catch (e) {
        this.projectError = `Could not load projects: ${e.message}`
      } finally {
        this.projectsLoading = false
      }
    },

    async createProject() {
      const name = this.newProjectName.trim()
      if (!name) return
      this.creatingProject = true
      this.projectError = null
      try {
        const res = await fetch('/api/prep/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        this.newProjectName = ''
        await this.loadProjects()
        this.activeProject = data.slug
        const proj = this.projects.find(p => p.slug === data.slug)
      } catch (e) {
        this.projectError = `Could not create project: ${e.message}`
      } finally {
        this.creatingProject = false
      }
    },

    selectProject(slug) {
      this.activeProject = slug
      const proj = this.projects.find(p => p.slug === slug)
      this.activePhase = 'ingest'
    },

    async loadProjectState() {
      // Reset transient state
      this.cast = []
      this.excluded = []
      this.aiCastResult = null
      this.analyzeResult = null
      this.preflightResult = null
      this.uploadDocPreview = null
      this.artifactStatus = {}
      for (const d of this.docs) {
        d.loaded = false
        d.filename = ''
        d.charCount = 0
        d.wordCount = 0
        d.error = null
      }

      // Load everything for this project
      await Promise.all([
        this.loadSources(),
        this.loadCast(),
        this.loadFileStatus(),
      ])
    },

    async loadSources() {
      if (!this.activeProject) return
      try {
        const res = await fetch(`${this.apiBase}/sources`)
        if (!res.ok) return
        const data = await res.json()
        const sources = data.sources || []
        // Fill docs array with loaded sources
        sources.slice(0, this.docs.length).forEach((s, i) => {
          this.docs[i].loaded = true
          this.docs[i].filename = s.filename
          this.docs[i].charCount = s.char_count
          this.docs[i].wordCount = Math.round(s.char_count / 5.5)  // rough estimate
        })
      } catch {}
    },

    async loadFileStatus() {
      if (!this.activeProject) return
      try {
        const res = await fetch(`${this.apiBase}/files`)
        if (!res.ok) return
        const data = await res.json()
        for (const art of this.artifactKinds) {
          const info = data.files?.[art.filename] || {}
          this.artifactStatus = {
            ...this.artifactStatus,
            [art.kind]: {
              hasCanonical: !!info.exists,
              hasDraft: !!info.has_draft,
              charCount: info.size_bytes || 0,
              generating: false,
              promoting: false,
              preview: null,
              error: null,
            },
          }
        }
      } catch {}
    },

    // ── INGEST ─────────────────────────────────────────────────
    triggerFileInput(doc) {
      if (!this.activeProject) {
        doc.error = 'Select a project first'
        return
      }
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
      if (!this.activeProject) {
        doc.error = 'Select a project first'
        return
      }
      doc.uploading = true
      doc.error = null
      doc.filename = file.name

      // Build FormData — server-side extracts text (handles PDFs correctly)
      const formData = new FormData()
      formData.append('file', file)

      try {
        const res = await fetch(`${this.apiBase}/upload`, {
          method: 'POST',
          body: formData,
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.error || `HTTP ${res.status}`)
        }
        const data = await res.json()
        doc.charCount = data.char_count
        doc.wordCount = data.word_count
        doc.loaded = true
      } catch (e) {
        doc.error = e.message
        doc.loaded = false
      } finally {
        doc.uploading = false
      }
    },

    async analyzeSources() {
      if (!this.activeProject) return
      this.analyzing = true
      try {
        const res = await fetch(`${this.apiBase}/analyze`, { method: 'POST' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        this.analyzeResult = data.analysis || data
      } catch (e) {
        this.analyzeResult = { error: e.message }
      } finally {
        this.analyzing = false
      }
    },

    // ── CAST ───────────────────────────────────────────────────
    async loadCast() {
      if (!this.activeProject) return
      this.castLoading = true
      this.castError = null
      try {
        const res = await fetch(`${this.apiBase}/cast`)
        if (res.status === 404) {
          // No cast yet — not an error, just empty state
          this.cast = []
          this.excluded = []
          return
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const agents = data.mandatory_agents || []
        this.cast = agents.map(a => ({ ...a, _agentOn: true }))
        this.excluded = data.excluded_entities || []
      } catch (e) {
        this.castError = `Could not load cast: ${e.message}`
      } finally {
        this.castLoading = false
      }
    },

    async saveCast() {
      if (!this.activeProject) return
      const payload = {
        mandatory_agents: this.cast.map(a => {
          const { _agentOn, ...rest } = a
          return rest
        }),
        excluded_entities: this.excluded,
      }
      try {
        await fetch(`${this.apiBase}/cast`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch (e) {
        console.error('Save cast failed:', e)
      }
    },

    async extractCastViaAI() {
      if (!this.activeProject) return
      this.aiCastExtracting = true
      this.aiCastResult = null
      this.castError = null
      try {
        const res = await fetch(`${this.apiBase}/extract-cast`, { method: 'POST' })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.error || `HTTP ${res.status}`)
        }
        this.aiCastResult = await res.json()
        // Preview the extracted cast immediately
        const draftCast = this.aiCastResult.cast || {}
        this.cast = (draftCast.mandatory_agents || []).map(a => ({ ...a, _agentOn: true }))
        this.excluded = draftCast.excluded_entities || []
      } catch (e) {
        this.castError = `AI extraction failed: ${e.message}`
      } finally {
        this.aiCastExtracting = false
      }
    },

    async promoteCast() {
      if (!this.activeProject) return
      this.castPromoting = true
      try {
        const res = await fetch(`${this.apiBase}/promote/cast`, { method: 'POST' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        await this.loadFileStatus()
      } catch (e) {
        this.castError = `Promote failed: ${e.message}`
      } finally {
        this.castPromoting = false
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
    _setArtifactStatus(kind, partial) {
      this.artifactStatus = {
        ...this.artifactStatus,
        [kind]: { ...(this.artifactStatus[kind] || {}), ...partial },
      }
    },

    async generateArtifact(kind) {
      if (!this.activeProject) return
      // 'config' artifact uses the existing /build endpoint (non-LLM)
      if (kind === 'config') return this.generateConfig()

      this._setArtifactStatus(kind, { generating: true, error: null })
      try {
        const res = await fetch(`${this.apiBase}/generate/${kind}`, { method: 'POST' })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.error || `HTTP ${res.status}`)
        }
        const data = await res.json()
        this._setArtifactStatus(kind, {
          hasDraft: true,
          preview: data.preview,
          charCount: data.char_count,
          overLimit: data.over_limit,
        })
        // For upload-document, update the visible preview
        if (kind === 'upload-document') {
          this.uploadDocPreview = data.preview
        }
      } catch (e) {
        this._setArtifactStatus(kind, { error: e.message })
      } finally {
        this._setArtifactStatus(kind, { generating: false })
      }
    },

    async generateConfig() {
      if (!this.activeProject) return
      this._setArtifactStatus('config', { generating: true, error: null })
      try {
        const res = await fetch(`${this.apiBase}/build`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ duration: 168, language: 'es' }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        await this.loadFileStatus()
      } catch (e) {
        this._setArtifactStatus('config', { error: e.message })
      } finally {
        this._setArtifactStatus('config', { generating: false })
      }
    },

    async promoteArtifact(kind) {
      if (!this.activeProject) return
      if (kind === 'config') return  // config is written directly by /build
      this._setArtifactStatus(kind, { promoting: true, error: null })
      try {
        const res = await fetch(`${this.apiBase}/promote/${kind}`, { method: 'POST' })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.error || `HTTP ${res.status}`)
        }
        this._setArtifactStatus(kind, { hasCanonical: true })
        await this.loadFileStatus()
        if (kind === 'upload-document') {
          await this.loadUploadDocPreview()
        }
      } catch (e) {
        this._setArtifactStatus(kind, { error: e.message })
      } finally {
        this._setArtifactStatus(kind, { promoting: false })
      }
    },

    async loadUploadDocPreview() {
      if (!this.activeProject) return
      try {
        const res = await fetch(`${this.apiBase}/download/upload_document.md`)
        if (res.ok) {
          this.uploadDocPreview = await res.text()
        }
      } catch {}
    },

    artifactStatusLabel(kind) {
      const s = this.artifactStatus[kind] || {}
      if (s.hasCanonical) return 'PROMOTED'
      if (s.hasDraft) return 'DRAFT'
      return 'NO DRAFT'
    },

    artifactStatusClass(kind) {
      const s = this.artifactStatus[kind] || {}
      if (s.hasCanonical) return 'status-promoted'
      if (s.hasDraft) return 'status-draft'
      return 'status-empty'
    },

    // ── PREFLIGHT ──────────────────────────────────────────────
    async runPreflight() {
      if (!this.activeProject) return
      this.preflightLoading = true
      this.preflightResult = null
      try {
        const res = await fetch(`${this.apiBase}/validate`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        this.preflightResult = await res.json()
      } catch (e) {
        this.preflightResult = { overall: 'ERROR', error: e.message }
      } finally {
        this.preflightLoading = false
      }
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
  grid-template-columns: repeat(5, 1fr);
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

/* ── PROJECT PICKER (PHASE 0) ──────────────────────────────── */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.project-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  cursor: pointer;
  transition: all 150ms ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 110px;
}
.project-card:hover  { border-color: var(--primary); box-shadow: 0 4px 12px rgba(107,143,113,.12); }
.project-card.active { background: var(--secondary); border-color: var(--accent); }
.project-card.new    { border-style: dashed; cursor: default; justify-content: center; align-items: center; gap: 8px; }

.project-name { font-size: 15px; font-weight: 600; }
.project-slug { font-size: 11px; color: var(--muted-fg); }
.project-meta { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }

.pm-pill {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--muted);
  color: var(--muted-fg);
  font-size: 10px;
}
.pm-pill.pm-on { background: rgba(107,143,113,.15); color: var(--primary); }

.project-new-label { font-size: 12px; color: var(--muted-fg); }
.project-new-input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  font-size: 12px;
  background: var(--card);
}
.project-new-input:focus { outline: none; border-color: var(--primary); }

/* ── DOC GRID (INGEST) ─────────────────────────────────────── */
.doc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.doc-grid.three-col {
  grid-template-columns: repeat(3, 1fr);
}

.doc-card.uploading { border-color: var(--accent); }
.doc-card.errored   { border-color: var(--destructive); }
.doc-error {
  margin-top: 6px;
  font-size: 11px;
  color: var(--destructive);
  font-family: 'JetBrains Mono', monospace;
}

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

.analyze-panel {
  margin-top: 14px;
  padding: 12px;
  background: var(--muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}
.analyze-json {
  font-size: 10px;
  white-space: pre-wrap;
  margin: 8px 0 0;
  max-height: 200px;
  overflow: auto;
  color: var(--muted-fg);
}

/* ── AI PANEL (PHASE 2) ────────────────────────────────────── */
.ai-panel {
  background: linear-gradient(135deg, rgba(232,200,122,.08), rgba(107,143,113,.05));
  border: 1px solid var(--accent);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 16px;
}
.ai-panel-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}
.ai-result {
  margin-top: 12px;
  padding: 12px;
  background: var(--card);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
.ai-result-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  padding: 4px 0;
}
.ai-warning {
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(232,200,122,.15);
  border-left: 3px solid var(--accent);
  font-size: 11px;
  color: #8B6914;
}
.ai-checks {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ai-check-row {
  font-size: 10px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--muted);
}
.ai-check-row.fail { background: rgba(185,75,75,.1); color: var(--destructive); }
.ai-check-row.warn { background: rgba(232,200,122,.15); color: #8B6914; }

/* ── BUILD STATUS CHIPS ────────────────────────────────────── */
.status-chip {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .05em;
}
.status-promoted { background: rgba(107,143,113,.18); color: var(--primary); }
.status-draft    { background: rgba(232,200,122,.25); color: #8B6914; }
.status-empty    { background: var(--muted); color: var(--muted-fg); }

.artifact-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  align-items: center;
}
.artifact-error {
  margin-top: 6px;
  font-size: 11px;
  color: var(--destructive);
  padding: 6px 8px;
  background: rgba(185,75,75,.08);
  border-radius: var(--radius-sm);
}

/* Small action button variant */
.action-btn.sm {
  padding: 6px 12px;
  font-size: 11px;
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

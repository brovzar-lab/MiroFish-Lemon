<template>
  <div class="dashboard">

    <!-- ── HEADER ─────────────────────────────────────────── -->
    <header class="dash-header">
      <div class="header-left">
        <div class="brand-mark">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
        </div>
        <div>
          <div class="brand-title">MIROFISH</div>
          <div class="brand-subtitle">TV & Film Character Simulation Platform</div>
        </div>
      </div>
      <button class="new-btn" @click="showNewModal = true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Project
      </button>
    </header>

    <!-- ── HERO ───────────────────────────────────────────── -->
    <div class="hero">
      <div class="hero-inner">
        <div class="hero-left">
          <h1 class="hero-title serif">Your simulation pipeline.</h1>
          <p class="hero-copy">Upload source documents, generate character casts, run AI simulations, and chat with characters — all in one place.</p>
        </div>
        <div class="hero-stats">
          <div class="stat-card">
            <div class="stat-value mono">{{ projects.length }}</div>
            <div class="stat-label">Projects</div>
          </div>
          <div class="stat-card">
            <div class="stat-value mono">{{ totalAgents }}</div>
            <div class="stat-label">Agents</div>
          </div>
          <div class="stat-card">
            <div class="stat-value mono">{{ completedCount }}</div>
            <div class="stat-label">Complete</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── PROJECT LIST ───────────────────────────────────── -->
    <main class="project-list">
      <div v-if="loading" class="loading-msg mono">Loading projects…</div>

      <div v-else-if="projects.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--muted-fg)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
        </div>
        <div class="empty-title serif">No projects yet</div>
        <p class="empty-copy">Create your first project to begin the simulation pipeline.</p>
        <button class="action-btn primary" @click="showNewModal = true">Create First Project</button>
      </div>

      <div v-else class="cards-grid">
        <div
          v-for="proj in projects"
          :key="proj.slug"
          class="project-card"
          @click="openProject(proj)"
        >
          <div class="card-header">
            <div class="card-slug mono">{{ proj.slug.toUpperCase().replace(/-/g, '_') }}</div>
            <div class="card-status-dot" :class="projectStage(proj).stageClass"></div>
          </div>

          <div class="card-name">{{ projectName(proj) }}</div>

          <!-- Pipeline progress -->
          <div class="pipeline-steps">
            <div class="pipe-step" :class="{ done: proj.has_cast }">
              <div class="pipe-dot"></div>
              <span class="pipe-label mono">PREPARE</span>
            </div>
            <div class="pipe-line" :class="{ done: proj.has_cast }"></div>
            <div class="pipe-step" :class="{ done: proj.has_preflight }">
              <div class="pipe-dot"></div>
              <span class="pipe-label mono">SIMULATE</span>
            </div>
            <div class="pipe-line" :class="{ done: proj.has_preflight }"></div>
            <div class="pipe-step" :class="{ done: false }">
              <div class="pipe-dot"></div>
              <span class="pipe-label mono">INTERACT</span>
            </div>
          </div>

          <div class="card-meta">
            <span class="meta-chip mono" v-if="proj.agent_count">{{ proj.agent_count }} agents</span>
            <span class="meta-chip mono" v-if="proj.total_chars">{{ Math.round(proj.total_chars / 1000) }}K chars</span>
          </div>

          <div class="card-footer">
            <div class="stage-label mono">{{ projectStage(proj).label }}</div>
            <div class="card-arrow">→</div>
          </div>
        </div>
      </div>
    </main>

    <!-- ── NEW PROJECT MODAL ──────────────────────────────── -->
    <div v-if="showNewModal" class="modal-overlay" @click.self="showNewModal = false">
      <div class="modal-card">
        <div class="eyebrow mono">NEW PROJECT</div>
        <div class="modal-title serif">Create a new simulation project</div>

        <div class="form-group">
          <label class="form-label mono">PROJECT NAME</label>
          <input
            v-model="newProject.name"
            class="form-input"
            placeholder="e.g. La Casa de la Lluvia"
            @input="autoSlug"
          />
        </div>

        <div class="form-group">
          <label class="form-label mono">SLUG</label>
          <input v-model="newProject.slug" class="form-input mono" placeholder="la-casa-de-la-lluvia" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label mono">LANGUAGE</label>
            <select v-model="newProject.language" class="form-input">
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="pt">Portuguese</option>
              <option value="zh">Chinese</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label mono">DURATION (hours)</label>
            <input v-model.number="newProject.duration_hours" type="number" min="24" max="720" class="form-input mono" />
          </div>
        </div>

        <div class="modal-actions">
          <button class="action-btn secondary" @click="showNewModal = false">Cancel</button>
          <button class="action-btn primary" :disabled="!newProject.slug" @click="createProject">Create Project</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PipelineDashboard',

  data() {
    return {
      loading: true,
      projects: [],
      showNewModal: false,
      newProject: {
        name: '',
        slug: '',
        language: 'en',
        duration_hours: 168,
      },
    }
  },

  computed: {
    totalAgents() {
      return this.projects.reduce((s, p) => s + (p.agent_count || 0), 0)
    },
    completedCount() {
      return this.projects.filter(p => p.has_preflight).length
    },
  },

  async mounted() {
    await this.loadProjects()
  },

  methods: {
    async loadProjects() {
      this.loading = true
      try {
        const res = await fetch('/api/prep/projects')
        if (res.ok) {
          const data = await res.json()
          this.projects = data.projects || []
        }
      } catch (e) {
        console.error('Failed to load projects:', e)
      } finally {
        this.loading = false
      }
    },

    projectName(proj) {
      return proj.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    },

    projectStage(proj) {
      if (proj.has_preflight) return { label: 'READY TO LAUNCH', stageClass: 'complete' }
      if (proj.has_config) return { label: 'BUILD COMPLETE', stageClass: 'building' }
      if (proj.has_cast) return { label: 'CAST APPROVED', stageClass: 'casting' }
      if (proj.has_upload_doc) return { label: 'INGESTING', stageClass: 'ingesting' }
      return { label: 'AWAITING DOCS', stageClass: 'empty' }
    },

    openProject(proj) {
      this.$router.push(`/project/${proj.slug}/prepare`)
    },

    autoSlug() {
      this.newProject.slug = this.newProject.name
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .slice(0, 40)
    },

    async createProject() {
      if (!this.newProject.slug) return
      try {
        const res = await fetch('/api/prep/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.newProject),
        })
        if (res.ok) {
          const data = await res.json()
          this.$router.push(`/project/${data.slug}/prepare`)
        }
      } catch (e) {
        console.error('Create failed:', e)
      }
    },
  },
}
</script>

<style scoped>
.dashboard {
  --background:  #FAFAF7;
  --foreground:  #1A1A1A;
  --border:      #DDD8CC;
  --primary:     #6B8F71;
  --secondary:   #F3EFE3;
  --muted:       #F6F3EA;
  --muted-fg:    #6E685E;
  --accent:      #E8C87A;
  --card:        #FFFDF8;
  --destructive: #B94B4B;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  min-height: 100vh;
  background: var(--background);
  color: var(--foreground);
  font-family: 'Inter', system-ui, sans-serif;
}

.mono  { font-family: 'JetBrains Mono', 'Fira Mono', monospace; }
.serif { font-family: Georgia, 'Times New Roman', serif; }

/* ── HEADER ──────────────────────────────────── */
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 36px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(to bottom, var(--card), var(--background));
}

.header-left { display: flex; align-items: center; gap: 12px; }

.brand-mark {
  width: 40px; height: 40px;
  border-radius: var(--radius-md);
  background: var(--secondary);
  color: var(--primary);
  display: flex; align-items: center; justify-content: center;
}

.brand-title { font-size: 15px; font-weight: 700; letter-spacing: .09em; }
.brand-subtitle { font-size: 12px; color: var(--muted-fg); margin-top: 2px; }

.new-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 18px;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: white;
  font-size: 13px; font-weight: 600;
  border: none; cursor: pointer;
  font-family: inherit;
  transition: all 150ms ease;
}
.new-btn:hover { background: #5a7a60; transform: translateY(-1px); }

/* ── HERO ────────────────────────────────────── */
.hero {
  padding: 40px 36px 32px;
  background: linear-gradient(135deg, rgba(107,143,113,.06), rgba(232,200,122,.08));
  border-bottom: 1px solid var(--border);
}

.hero-inner {
  max-width: 960px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 40px;
}

.hero-title { font-size: 32px; line-height: 1.1; font-weight: 600; margin: 0; }
.hero-copy  { font-size: 14px; color: var(--muted-fg); line-height: 1.6; margin-top: 10px; max-width: 440px; }

.hero-stats { display: flex; gap: 16px; }

.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  text-align: center;
  min-width: 80px;
}
.stat-value { font-size: 24px; font-weight: 700; color: var(--primary); }
.stat-label { font-size: 11px; color: var(--muted-fg); margin-top: 4px; letter-spacing: .06em; }

/* ── PROJECT LIST ────────────────────────────── */
.project-list { padding: 28px 36px 48px; }

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.project-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all 200ms ease;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.project-card:hover { border-color: var(--primary); box-shadow: 0 8px 24px rgba(107,143,113,.12); transform: translateY(-2px); }

.card-header { display: flex; align-items: center; justify-content: space-between; }
.card-slug { font-size: 11px; color: var(--muted-fg); letter-spacing: .08em; }

.card-status-dot {
  width: 8px; height: 8px;
  border-radius: 999px;
  background: var(--muted-fg);
}
.card-status-dot.complete  { background: var(--primary); box-shadow: 0 0 8px rgba(107,143,113,.5); }
.card-status-dot.building  { background: var(--accent);  box-shadow: 0 0 8px rgba(232,200,122,.5); }
.card-status-dot.casting   { background: var(--accent);  }
.card-status-dot.ingesting { background: var(--border);  }
.card-status-dot.empty     { background: var(--border);  }

.card-name { font-size: 20px; font-weight: 600; line-height: 1.2; }

/* ── PIPELINE STEPS ──────────────────────────── */
.pipeline-steps {
  display: flex;
  align-items: center;
  gap: 0;
}

.pipe-step {
  display: flex; align-items: center; gap: 6px;
  flex-shrink: 0;
}

.pipe-dot {
  width: 10px; height: 10px;
  border-radius: 999px;
  border: 2px solid var(--border);
  background: var(--background);
  transition: all 200ms ease;
}
.pipe-step.done .pipe-dot {
  background: var(--primary);
  border-color: var(--primary);
}

.pipe-label { font-size: 10px; color: var(--muted-fg); letter-spacing: .08em; }
.pipe-step.done .pipe-label { color: var(--primary); font-weight: 600; }

.pipe-line {
  flex: 1;
  height: 2px;
  background: var(--border);
  margin: 0 4px;
  min-width: 20px;
  transition: background 200ms ease;
}
.pipe-line.done { background: var(--primary); }

.card-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-chip {
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--secondary);
  font-size: 11px;
  color: var(--muted-fg);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.stage-label { font-size: 11px; color: var(--primary); letter-spacing: .08em; font-weight: 600; }
.card-arrow  { font-size: 18px; color: var(--muted-fg); transition: transform 200ms; }
.project-card:hover .card-arrow { transform: translateX(4px); color: var(--primary); }

/* ── EMPTY STATE ─────────────────────────────── */
.empty-state { text-align: center; padding: 60px 20px; }
.empty-icon  { margin-bottom: 16px; }
.empty-title { font-size: 22px; margin-bottom: 8px; }
.empty-copy  { font-size: 14px; color: var(--muted-fg); margin-bottom: 20px; }

.loading-msg { text-align: center; padding: 40px; color: var(--muted-fg); animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .5; } }

/* ── MODAL ───────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(26,26,26,.4);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}

.modal-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 28px;
  width: 440px;
  max-width: 90vw;
  display: flex; flex-direction: column; gap: 16px;
  box-shadow: 0 24px 48px rgba(26,26,26,.15);
}

.eyebrow { font-size: 11px; letter-spacing: .1em; color: var(--muted-fg); }
.modal-title { font-size: 22px; font-weight: 600; line-height: 1.2; }

.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: 10px; color: var(--muted-fg); letter-spacing: .09em; }
.form-input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--background);
  font-size: 14px;
  font-family: inherit;
  color: var(--foreground);
  outline: none;
  transition: border-color 150ms;
}
.form-input:focus { border-color: var(--primary); }
.form-input.mono  { font-family: 'JetBrains Mono', monospace; font-size: 13px; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 4px; }

.action-btn {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 13px; font-weight: 600;
  cursor: pointer; border: none;
  font-family: inherit;
  transition: all 150ms ease;
}
.action-btn.primary { background: var(--primary); color: white; }
.action-btn.primary:hover:not(:disabled) { background: #5a7a60; }
.action-btn.primary:disabled { opacity: .45; cursor: not-allowed; }
.action-btn.secondary { background: var(--secondary); color: var(--foreground); border: 1px solid var(--border); }
.action-btn.secondary:hover { border-color: var(--primary); }
</style>

<template>
  <div class="launch-view">
    <header class="launch-header">
      <router-link :to="`/project/${slug}/prepare`" class="back-link">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        Back to Prep Studio
      </router-link>
    </header>

    <main class="launch-body">
      <div class="confirm-card">
        <div class="eyebrow mono">STEP 2 / SIMULATE</div>
        <h1 class="confirm-title serif">Launch Confirmation</h1>
        <p class="confirm-copy">
          Review the simulation parameters below. Once you confirm, the prep package will be
          automatically ingested into MiroFish and the simulation will begin.
        </p>

        <!-- Summary table -->
        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-label mono">PROJECT</div>
            <div class="summary-value">{{ projectName }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label mono">AGENTS</div>
            <div class="summary-value mono">{{ agentCount }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label mono">DURATION</div>
            <div class="summary-value mono">{{ durationHours }}h</div>
          </div>
          <div class="summary-item">
            <div class="summary-label mono">LANGUAGE</div>
            <div class="summary-value mono">{{ language.toUpperCase() }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label mono">EST. COST</div>
            <div class="summary-value mono cost">${{ totalCost }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label mono">PREFLIGHT</div>
            <div class="summary-value mono pass">PASS ✓</div>
          </div>
        </div>

        <!-- Files being ingested -->
        <div class="files-section">
          <div class="eyebrow mono" style="margin-bottom:12px;">FILES TO INGEST</div>
          <div class="file-row" v-for="f in files" :key="f">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            <span class="mono">{{ f }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="launch-actions">
          <router-link :to="`/project/${slug}/prepare`" class="action-btn secondary">
            ← Back to Prep
          </router-link>
          <button
            class="action-btn primary launch-btn"
            :disabled="launching"
            @click="launch"
          >
            <span v-if="!launching">🚀 Confirm & Launch Simulation</span>
            <span v-else class="launching-text">Ingesting package… {{ launchProgress }}%</span>
          </button>
        </div>

        <!-- Progress overlay -->
        <div v-if="launching" class="progress-section">
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: launchProgress + '%' }"></div>
          </div>
          <div class="progress-label mono">{{ launchStatus }}</div>
        </div>

        <!-- Error -->
        <div v-if="launchError" class="error-banner mono">
          {{ launchError }}
        </div>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'LaunchConfirmView',
  props: {
    slug: { type: String, required: true },
  },

  data() {
    return {
      projectName: '',
      agentCount: 0,
      durationHours: 168,
      language: 'en',
      totalCost: '0.00',
      files: [
        'upload_document.md',
        'reality_seed.md',
        'simulation_config.json',
        'event_seeds.json',
        'character_cast.json',
      ],
      launching: false,
      launchProgress: 0,
      launchStatus: '',
      launchError: null,
    }
  },

  async mounted() {
    await this.loadSummary()
  },

  methods: {
    async loadSummary() {
      try {
        // Load meta
        const metaRes = await fetch(`/api/prep/${this.slug}/meta`)
        if (metaRes.ok) {
          const meta = await metaRes.json()
          this.projectName = meta.name || this.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
          this.durationHours = meta.duration_hours || 168
          this.language = meta.language || 'en'
        }

        // Load validation for cost/agent count
        const valRes = await fetch(`/api/prep/${this.slug}/validate`)
        if (valRes.ok) {
          const val = await valRes.json()
          this.agentCount = val.cost_estimate?.agent_count || 0
          this.totalCost = val.cost_estimate?.total_usd?.toFixed(2) || '0.00'
        }
      } catch (e) {
        console.error('Failed to load summary:', e)
      }
    },

    async launch() {
      this.launching = true
      this.launchError = null
      this.launchProgress = 10
      this.launchStatus = 'Creating MiroFish project…'

      try {
        // The auto-ingest endpoint will be created in Phase B
        const res = await fetch(`/api/launch/${this.slug}`, { method: 'POST' })
        this.launchProgress = 50
        this.launchStatus = 'Uploading source material…'

        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.error || `Launch failed (HTTP ${res.status})`)
        }

        const data = await res.json()
        this.launchProgress = 100
        this.launchStatus = 'Simulation started!'

        // Redirect to simulation monitor
        setTimeout(() => {
          if (data.simulation_id) {
            this.$router.push(`/simulation/${data.simulation_id}/start`)
          } else {
            this.launchStatus = 'Package ingested. Navigate to MiroFish to start simulation.'
          }
        }, 1500)
      } catch (e) {
        this.launchError = e.message
        this.launching = false
      }
    },
  },
}
</script>

<style scoped>
.launch-view {
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
  --radius-md: 6px;
  --radius-lg: 8px;

  min-height: 100vh;
  background: var(--background);
  color: var(--foreground);
  font-family: 'Inter', system-ui, sans-serif;
  display: flex;
  flex-direction: column;
}

.mono  { font-family: 'JetBrains Mono', 'Fira Mono', monospace; }
.serif { font-family: Georgia, 'Times New Roman', serif; }

.launch-header {
  padding: 20px 36px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(to bottom, var(--card), var(--background));
}

.back-link {
  display: inline-flex; align-items: center; gap: 8px;
  color: var(--muted-fg);
  text-decoration: none;
  font-size: 13px;
  transition: color 150ms;
}
.back-link:hover { color: var(--primary); }

.launch-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.confirm-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 36px;
  max-width: 600px;
  width: 100%;
  display: flex; flex-direction: column; gap: 20px;
  box-shadow: 0 12px 40px rgba(26,26,26,.08);
}

.eyebrow { font-size: 11px; letter-spacing: .1em; color: var(--muted-fg); }
.confirm-title { font-size: 28px; font-weight: 600; margin: 0; line-height: 1.1; }
.confirm-copy { font-size: 14px; color: var(--muted-fg); line-height: 1.6; margin: 0; }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.summary-item {
  background: var(--muted);
  border-radius: var(--radius-md);
  padding: 14px;
  display: flex; flex-direction: column; gap: 6px;
}
.summary-label { font-size: 10px; color: var(--muted-fg); letter-spacing: .09em; }
.summary-value { font-size: 16px; font-weight: 600; }
.summary-value.cost { color: var(--accent); }
.summary-value.pass { color: var(--primary); }

.files-section {
  padding: 16px;
  background: var(--secondary);
  border-radius: var(--radius-md);
}

.file-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}

.launch-actions {
  display: flex; justify-content: space-between; gap: 12px;
  margin-top: 4px;
}

.action-btn {
  padding: 12px 24px;
  border-radius: var(--radius-md);
  font-size: 14px; font-weight: 600;
  cursor: pointer; border: none;
  font-family: inherit;
  transition: all 150ms ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.action-btn.primary { background: var(--primary); color: white; flex: 1; justify-content: center; }
.action-btn.primary:hover:not(:disabled) { background: #5a7a60; transform: translateY(-1px); }
.action-btn.primary:disabled { opacity: .5; cursor: not-allowed; }
.action-btn.secondary { background: var(--secondary); color: var(--foreground); border: 1px solid var(--border); }

.launch-btn { font-size: 15px; padding: 14px 28px; }

.progress-section { display: flex; flex-direction: column; gap: 10px; }
.progress-track {
  height: 8px;
  border-radius: 999px;
  background: var(--muted);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 999px;
  transition: width 600ms ease;
}
.progress-label { font-size: 12px; color: var(--muted-fg); animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .5; } }

.error-banner {
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(185,75,75,.1);
  color: var(--destructive);
  font-size: 12px;
  border: 1px solid rgba(185,75,75,.2);
}
</style>

<template>
  <div class="social-view">
    <header class="social-header">
      <div class="header-left">
        <router-link :to="`/project/${slug}/prepare`" class="back-link">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          Back to Pipeline
        </router-link>
      </div>
      <div class="header-center">
        <div class="social-title mono">CHARACTER ENGINE</div>
        <div class="social-subtitle mono">{{ slug.toUpperCase().replace(/-/g, '_') }}</div>
      </div>
      <div class="header-right">
        <a :href="socialUrl" target="_blank" class="open-btn mono">
          Open in new tab ↗
        </a>
      </div>
    </header>

    <div class="iframe-container">
      <iframe
        v-if="socialUrl"
        :src="socialUrl"
        class="social-frame"
        allow="clipboard-write"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      ></iframe>
      <div v-else class="not-running">
        <div class="not-running-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--muted-fg)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        </div>
        <div class="not-running-title serif">Character Social not running</div>
        <p class="not-running-copy">
          Start the Character Social server:<br/>
          <code class="mono">cd /Users/quantumcode/CODE/character-social && npm run dev</code>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SocialView',
  props: {
    slug: { type: String, required: true },
  },

  data() {
    return {
      socialAvailable: false,
    }
  },

  computed: {
    socialUrl() {
      return this.socialAvailable ? `http://localhost:3200/${this.slug}` : null
    },
  },

  async mounted() {
    await this.checkSocialServer()
  },

  methods: {
    async checkSocialServer() {
      try {
        // Try to reach the Character Social server
        const res = await fetch('http://localhost:3200/', { mode: 'no-cors', signal: AbortSignal.timeout(3000) })
        this.socialAvailable = true
      } catch {
        this.socialAvailable = false
      }
    },
  },
}
</script>

<style scoped>
.social-view {
  --background: #05050a;
  --foreground: #e0e0e0;
  --border: rgba(0, 255, 255, 0.12);
  --accent: #00ffff;
  --muted-fg: rgba(255,255,255,0.4);
  --card: rgba(10, 12, 18, 0.95);

  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--background);
  color: var(--foreground);
  font-family: 'Inter', system-ui, sans-serif;
}

.mono { font-family: 'JetBrains Mono', 'Fira Mono', monospace; }
.serif { font-family: Georgia, 'Times New Roman', serif; }

.social-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--card);
  flex-shrink: 0;
}

.header-left, .header-right { flex: 1; }
.header-right { text-align: right; }
.header-center { text-align: center; }

.back-link {
  display: inline-flex; align-items: center; gap: 6px;
  color: var(--muted-fg);
  text-decoration: none;
  font-size: 12px;
  transition: color 150ms;
}
.back-link:hover { color: var(--accent); }

.social-title { font-size: 12px; font-weight: 700; letter-spacing: .15em; color: var(--accent); }
.social-subtitle { font-size: 10px; color: var(--muted-fg); letter-spacing: .1em; margin-top: 2px; }

.open-btn {
  display: inline-flex; align-items: center;
  padding: 6px 12px;
  border-radius: 4px;
  background: rgba(0, 255, 255, 0.08);
  border: 1px solid var(--border);
  color: var(--accent);
  font-size: 11px;
  text-decoration: none;
  transition: all 150ms;
}
.open-btn:hover { background: rgba(0, 255, 255, 0.15); }

.iframe-container {
  flex: 1;
  display: flex;
}

.social-frame {
  flex: 1;
  border: none;
  width: 100%;
  min-height: calc(100vh - 54px);
}

.not-running {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  text-align: center;
  padding: 40px;
}

.not-running-title { font-size: 22px; color: var(--foreground); }
.not-running-copy { font-size: 13px; color: var(--muted-fg); line-height: 1.8; }
.not-running-copy code {
  display: inline-block;
  margin-top: 8px;
  padding: 6px 12px;
  background: rgba(0, 255, 255, 0.06);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 11px;
  color: var(--accent);
}
</style>

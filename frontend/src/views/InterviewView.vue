<template>
  <div class="prep-workspace">

    <!-- ── HEADER ─────────────────────────────────────────────────── -->
    <header class="prep-header">
      <div class="header-top">
        <div class="brand-block">
          <router-link :to="`/project/${slug}/prepare`" class="back-link" title="Back to the studio">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </router-link>
          <div class="brand-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
          </div>
          <div>
            <div class="brand-title">DOCUMENT WIZARD</div>
            <div class="brand-subtitle">Answer questions out loud or in writing — the studio writes the documents</div>
          </div>
        </div>
        <div class="session-strip">
          <div class="session-stat">
            <div class="session-label">PROJECT</div>
            <div class="session-value mono">{{ slug }}</div>
          </div>
          <div class="session-stat">
            <div class="session-label">ANSWERED</div>
            <div class="session-value mono">{{ answeredCount }} / {{ totalCount }}</div>
          </div>
          <div class="session-stat">
            <div class="session-label">DOCS APPROVED</div>
            <div class="session-value mono">{{ approvedCount }} / {{ requiredDocCount }}</div>
          </div>
        </div>
      </div>
    </header>

    <!-- ── BODY ───────────────────────────────────────────────────── -->
    <main class="wizard-body">

      <!-- Not started -->
      <div v-if="phase === 'loading'" class="center-note mono">Loading interview…</div>

      <div v-else-if="phase === 'intro'" class="intro-panel">
        <div class="phase-label mono">START</div>
        <h2 class="display serif">Where is your story right now?</h2>
        <p class="lede">
          The interview asks film-development questions (want, wound, flaw — the
          interrogation method) and turns your answers into the five source documents.
          Anything already uploaded in the studio is skipped and never asked about.
        </p>
        <div class="uploaded-note mono" v-if="uploadedDocs.length">
          ALREADY UPLOADED, WILL BE SKIPPED: {{ uploadedDocs.join(', ') }}
        </div>
        <button class="btn-primary" @click="startInterview">🎙️ START THE INTERVIEW →</button>
        <p class="hint mono">TIP: use macOS dictation (press the mic key) to answer by voice.</p>
      </div>

      <!-- Interview + review -->
      <div v-else class="duo">

        <!-- LEFT: conversation -->
        <div class="chat-col">

          <!-- Review mode -->
          <div v-if="reviewDoc" class="review-panel">
            <div class="q-meta mono">DRAFT REVIEW · {{ docLabel(reviewDoc) }} · AUTHORED VIA INTERVIEW</div>
            <textarea v-if="editingDraft" v-model="draftEdit" class="draft-edit mono"></textarea>
            <div v-else class="draft-page serif" v-text="draftTexts[reviewDoc]"></div>
            <div class="answer-actions">
              <button class="btn-approve" @click="approveDoc(reviewDoc)" :disabled="busy">✓ APPROVE DOCUMENT</button>
              <button class="btn-plain" @click="toggleEdit">{{ editingDraft ? 'DONE EDITING' : '✎ EDIT TEXT' }}</button>
              <button class="btn-plain" @click="regenerate(reviewDoc)" :disabled="busy">↻ REGENERATE</button>
              <button class="btn-ghost" @click="reviewDoc = null">BACK TO QUESTIONS</button>
            </div>
          </div>

          <!-- Question mode -->
          <template v-else>
            <div class="trail" ref="trail">
              <div v-for="q in answeredTrail" :key="q.id" class="trail-pair">
                <div class="bubble ai"><span class="who mono">WIZARD</span>{{ q.text }}</div>
                <div class="bubble us"><span class="who mono">YOU</span>{{ q.answer || '(skipped)' }}</div>
              </div>
            </div>

            <div v-if="nextQuestion" class="q-card">
              <div class="q-meta mono">
                QUESTION {{ answeredCount + 1 }} OF ~{{ totalCount }} ·
                {{ docLabel(nextQuestion.doc) }}
                <span v-if="nextQuestion.doc === 'protocol'"> · FROM THE INTERROGATION PROTOCOL</span>
              </div>
              <div class="q-text serif">{{ nextQuestion.text }}</div>
              <textarea
                v-model="answerText"
                class="answer-input"
                rows="5"
                :placeholder="nextQuestion.example ? 'Example shape: ' + nextQuestion.example : 'Answer in your own words…'"
                @keydown.meta.enter="submitAnswer"
              ></textarea>
              <div class="answer-actions">
                <button class="btn-primary" @click="submitAnswer" :disabled="busy || !answerText.trim()">SUBMIT ANSWER</button>
                <button class="btn-plain" @click="skipQuestion" :disabled="busy">SKIP FOR NOW</button>
                <router-link class="btn-ghost" :to="`/project/${slug}/prepare`">I HAVE A DOCUMENT FOR THIS</router-link>
              </div>
              <div class="hint mono">⌘+ENTER to submit · dictate with the macOS mic key</div>
            </div>

            <div v-else class="q-card done-card">
              <div class="q-meta mono">INTERVIEW COMPLETE</div>
              <div class="q-text serif">All questions answered. Generate and approve each document on the right.</div>
            </div>
          </template>

          <div v-if="errorMsg" class="error-strip mono">{{ errorMsg }}</div>
        </div>

        <!-- RIGHT: document progress rail -->
        <div class="rail">
          <div class="rail-title mono">DOCUMENTS BUILDING LIVE</div>
          <div v-for="[id, doc] in orderedProgress" :key="id" class="docp" :class="{ approved: doc.approved, uploaded: doc.uploaded }">
            <div class="docp-row">
              <span class="docp-name">
                {{ doc.label }}
                <span v-if="doc.uploaded" class="src-pill up mono">UPLOADED</span>
                <span v-else-if="doc.approved" class="src-pill ok mono">APPROVED ✓</span>
                <span v-else-if="doc.draft" class="src-pill au mono">DRAFT READY</span>
              </span>
              <span class="docp-pct mono">{{ doc.uploaded ? '100' : doc.percent }}%</span>
            </div>
            <div class="meter" :class="{ full: doc.percent === 100 || doc.uploaded }">
              <i :style="{ width: (doc.uploaded ? 100 : doc.percent) + '%' }"></i>
            </div>
            <div class="docp-foot mono">
              <span v-if="doc.uploaded">Your file. Never asked about.</span>
              <span v-else>{{ doc.answered }}/{{ doc.questions }} answered</span>
              <button
                v-if="!doc.uploaded && doc.draft"
                class="mini-btn review"
                @click="openReview(id)"
              >REVIEW DRAFT</button>
              <button
                v-else-if="!doc.uploaded && doc.percent >= 60 && doc.questions > 0"
                class="mini-btn"
                :disabled="busy"
                @click="synthesize(id)"
              >{{ busy && busyDoc === id ? 'WRITING…' : 'GENERATE DRAFT' }}</button>
            </div>
          </div>

          <router-link
            v-if="allRequiredApproved"
            class="btn-approve wide"
            :to="`/project/${slug}/prepare`"
          >DOCUMENTS READY → BACK TO INGEST</router-link>
          <div v-else class="rail-note mono">
            Approve every required document to finish. Handoff is optional.
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
export default {
  name: 'InterviewView',
  props: { slug: { type: String, required: true } },
  data() {
    return {
      phase: 'loading',        // loading | intro | active
      uploadedDocs: [],
      questions: [],
      nextQuestion: null,
      progress: {},
      draftTexts: {},
      approved: {},
      answeredCount: 0,
      totalCount: 0,
      answerText: '',
      reviewDoc: null,
      editingDraft: false,
      draftEdit: '',
      busy: false,
      busyDoc: null,
      errorMsg: '',
      docLabels: {
        bible: 'Show Bible', synopsis: 'Pilot Synopsis',
        protocol: 'Interrogation Protocol', seed: 'Seed Prompt', handoff: 'Handoff Doc',
      },
    }
  },
  computed: {
    orderedProgress() {
      // jsonify sorts keys alphabetically; restore document order
      return ['bible', 'synopsis', 'protocol', 'seed', 'handoff']
        .filter(id => this.progress[id])
        .map(id => [id, this.progress[id]])
    },
    answeredTrail() {
      return this.questions.filter(q => q.answer !== null || q.skipped).slice(-6)
    },
    approvedCount() {
      return Object.entries(this.approved).filter(([, v]) => v).length
    },
    requiredDocCount() {
      // handoff is optional; uploaded docs don't need approval
      return ['bible', 'synopsis', 'protocol', 'seed']
        .filter(d => !this.uploadedDocs.includes(d)).length
    },
    allRequiredApproved() {
      return ['bible', 'synopsis', 'protocol', 'seed']
        .filter(d => !this.uploadedDocs.includes(d))
        .every(d => this.approved[d])
    },
  },
  async mounted() {
    await this.loadState()
  },
  methods: {
    docLabel(id) { return this.docLabels[id] || id },
    api(path) { return `/api/prep/${this.slug}${path}` },

    async loadState() {
      try {
        // Which docs are already uploaded? (skipped by the interview)
        const srcRes = await fetch(this.api('/sources')).then(r => r.json())
        this.uploadedDocs = (srcRes.sources || [])
          .filter(s => s.mode === 'uploaded').map(s => s.id)

        const res = await fetch(this.api('/interview')).then(r => r.json())
        if (res.status === 'not_started') {
          this.phase = 'intro'
        } else {
          this.applyState(res)
          this.phase = 'active'
        }
      } catch (e) {
        this.errorMsg = 'Failed to load interview state: ' + e.message
        this.phase = 'intro'
      }
    },

    applyState(res) {
      this.questions = res.questions || []
      this.nextQuestion = res.next_question
      this.progress = res.progress || {}
      this.draftTexts = res.draft_texts || {}
      this.approved = res.approved || {}
      this.answeredCount = res.answered_count || 0
      this.totalCount = res.total_count || 0
    },

    async startInterview() {
      this.busy = true
      try {
        const res = await fetch(this.api('/interview/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ uploaded_docs: this.uploadedDocs }),
        }).then(r => r.json())
        this.applyState(res)
        this.phase = 'active'
      } catch (e) {
        this.errorMsg = 'Could not start: ' + e.message
      } finally { this.busy = false }
    },

    async submitAnswer() {
      if (!this.answerText.trim() || !this.nextQuestion) return
      await this.postAnswer({ question_id: this.nextQuestion.id, answer: this.answerText })
      this.answerText = ''
    },

    async skipQuestion() {
      if (!this.nextQuestion) return
      await this.postAnswer({ question_id: this.nextQuestion.id, skip: true })
    },

    async postAnswer(body) {
      this.busy = true
      this.errorMsg = ''
      try {
        const res = await fetch(this.api('/interview/answer'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        const data = await res.json()
        if (!res.ok) { this.errorMsg = data.error || 'Failed to save answer'; return }
        this.applyState(data)
        this.$nextTick(() => {
          const t = this.$refs.trail
          if (t) t.scrollTop = t.scrollHeight
        })
      } catch (e) {
        this.errorMsg = 'Network error: ' + e.message
      } finally { this.busy = false }
    },

    async synthesize(docId) {
      this.busy = true; this.busyDoc = docId; this.errorMsg = ''
      try {
        const res = await fetch(this.api('/interview/synthesize'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ doc_id: docId }),
        })
        const data = await res.json()
        if (!res.ok) {
          this.errorMsg = data.error_type === 'credits_exhausted'
            ? 'API credits exhausted — top up OpenRouter, then retry.'
            : (data.error || 'Draft generation failed')
          return
        }
        this.draftTexts[docId] = data.draft
        this.progress = data.progress
        this.openReview(docId)
      } catch (e) {
        this.errorMsg = 'Network error: ' + e.message
      } finally { this.busy = false; this.busyDoc = null }
    },

    async regenerate(docId) {
      this.reviewDoc = null
      await this.synthesize(docId)
    },

    openReview(docId) {
      this.reviewDoc = docId
      this.editingDraft = false
      this.draftEdit = this.draftTexts[docId] || ''
    },

    toggleEdit() {
      if (this.editingDraft) {
        this.draftTexts[this.reviewDoc] = this.draftEdit
      } else {
        this.draftEdit = this.draftTexts[this.reviewDoc] || ''
      }
      this.editingDraft = !this.editingDraft
    },

    async approveDoc(docId) {
      this.busy = true; this.errorMsg = ''
      try {
        const content = this.editingDraft ? this.draftEdit : this.draftTexts[docId]
        const res = await fetch(this.api('/interview/approve'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ doc_id: docId, content }),
        })
        const data = await res.json()
        if (!res.ok) { this.errorMsg = data.error || 'Approve failed'; return }
        this.approved[docId] = true
        this.progress = data.progress
        this.reviewDoc = null
      } catch (e) {
        this.errorMsg = 'Network error: ' + e.message
      } finally { this.busy = false }
    },
  },
}
</script>

<style scoped>
.prep-workspace {
  --background:  #FAFAF7;
  --foreground:  #1A1A1A;
  --border:      #DDD8CC;
  --primary:     #6B8F71;
  --secondary:   #F3EFE3;
  --muted:       #F6F3EA;
  --muted-fg:    #6E685E;
  --accent:      #E8C87A;
  --accent-deep: #8A6D2A;
  --emerald:     #10B981;
  --emerald-bg:  #E9F9F1;
  --destructive: #B94B4B;
  --card:        #FFFDF8;

  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--background);
  color: var(--foreground);
  font-family: 'Inter', system-ui, sans-serif;
}

.mono  { font-family: 'JetBrains Mono', 'Fira Mono', 'Courier New', monospace; }
.serif { font-family: Georgia, 'Times New Roman', serif; }

/* header (mirrors PrepView) */
.prep-header { padding: 24px 36px 18px; border-bottom: 1px solid var(--border); background: linear-gradient(to bottom, var(--card), var(--background)); }
.header-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; flex-wrap: wrap; }
.brand-block { display: flex; align-items: center; gap: 12px; }
.back-link { display: flex; align-items: center; color: var(--muted-fg); }
.brand-mark { width: 36px; height: 36px; border-radius: 6px; background: var(--secondary); display: flex; align-items: center; justify-content: center; }
.brand-title { font-weight: 700; letter-spacing: .12em; font-size: 14px; }
.brand-subtitle { font-size: 12.5px; color: var(--muted-fg); }
.session-strip { display: flex; gap: 26px; }
.session-label { font-size: 10px; letter-spacing: .14em; color: var(--muted-fg); }
.session-value { font-size: 13px; margin-top: 3px; }

/* body */
.wizard-body { flex: 1; padding: 30px 36px 60px; max-width: 1280px; width: 100%; margin: 0 auto; }
.center-note { text-align: center; padding: 80px 0; color: var(--muted-fg); }

/* intro */
.intro-panel { max-width: 640px; margin: 40px auto; text-align: center; }
.phase-label { font-size: 11px; letter-spacing: .18em; color: var(--muted-fg); margin-bottom: 12px; }
.display { font-size: 30px; font-weight: 600; margin-bottom: 12px; }
.lede { color: #5c554a; font-size: 14.5px; margin-bottom: 20px; }
.uploaded-note { font-size: 11px; background: var(--emerald-bg); border: 1px solid #bfe8d4; border-radius: 8px; padding: 10px 14px; margin-bottom: 20px; color: #0b7d59; }
.hint { font-size: 10.5px; color: var(--muted-fg); margin-top: 14px; }

/* duo layout */
.duo { display: grid; grid-template-columns: 1.5fr 1fr; gap: 28px; }
@media (max-width: 900px) { .duo { grid-template-columns: 1fr; } }
.chat-col { display: flex; flex-direction: column; gap: 14px; min-width: 0; }

/* trail */
.trail { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-right: 6px; }
.trail-pair { display: flex; flex-direction: column; gap: 8px; }
.bubble { border: 1px solid var(--border); border-radius: 10px; padding: 11px 14px; font-size: 13px; max-width: 90%; background: var(--card); color: #5c554a; white-space: pre-wrap; }
.bubble.us { background: var(--secondary); align-self: flex-end; color: #3d382e; }
.bubble .who { display: block; font-size: 9px; letter-spacing: .14em; color: #b5ad9c; margin-bottom: 4px; }

/* question card */
.q-card { border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 10px; background: var(--card); padding: 20px 22px; }
.q-card.done-card { border-left-color: var(--emerald); }
.q-meta { font-size: 10.5px; letter-spacing: .14em; color: var(--accent-deep); text-transform: uppercase; margin-bottom: 10px; }
.q-text { font-size: 20px; line-height: 1.45; margin-bottom: 14px; }
.answer-input { width: 100%; border: 1.5px dashed var(--border); border-radius: 10px; background: #fffefb; padding: 13px 15px; font-size: 14px; font-family: inherit; resize: vertical; box-sizing: border-box; }
.answer-input:focus { outline: none; border-color: var(--accent); border-style: solid; }
.answer-actions { display: flex; gap: 10px; margin-top: 14px; align-items: center; flex-wrap: wrap; }

/* buttons */
.btn-primary, .btn-plain, .btn-ghost, .btn-approve, .mini-btn {
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; letter-spacing: .06em;
  border-radius: 8px; padding: 10px 17px; cursor: pointer; border: 1px solid var(--border);
  background: #fff; color: var(--foreground); text-decoration: none; display: inline-block;
}
.btn-primary { background: var(--primary); border-color: var(--primary); color: #fff; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-ghost { border: none; background: transparent; color: var(--muted-fg); }
.btn-approve { background: var(--emerald); border-color: var(--emerald); color: #fff; }
.btn-approve.wide { display: block; text-align: center; margin-top: 16px; }
.mini-btn { padding: 5px 11px; font-size: 9.5px; }
.mini-btn.review { background: var(--accent); border-color: var(--accent); color: #1A1A1A; }
.mini-btn:disabled { opacity: .5; cursor: wait; }

/* review */
.review-panel { border: 1px solid var(--border); border-radius: 10px; background: var(--card); padding: 22px 26px; }
.draft-page { border: 1px solid var(--border); border-radius: 4px; background: #fffef9; padding: 26px 30px; font-size: 15px; line-height: 1.75; color: #33302a; white-space: pre-wrap; max-height: 480px; overflow-y: auto; margin-top: 12px; }
.draft-edit { width: 100%; min-height: 380px; border: 1.5px solid var(--accent); border-radius: 8px; padding: 16px; font-size: 12.5px; line-height: 1.6; box-sizing: border-box; margin-top: 12px; }

/* rail */
.rail { display: flex; flex-direction: column; gap: 12px; }
.rail-title { font-size: 11px; letter-spacing: .18em; color: var(--muted-fg); }
.docp { border: 1px solid var(--border); border-radius: 10px; background: var(--card); padding: 14px 16px; }
.docp.approved { background: var(--emerald-bg); border-color: #bfe8d4; }
.docp.uploaded { border-left: 3px solid var(--emerald); }
.docp-row { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
.docp-name { font-size: 13.5px; font-weight: 600; }
.docp-pct { font-size: 11px; color: var(--muted-fg); }
.meter { height: 6px; border-radius: 999px; background: #efe9db; overflow: hidden; }
.meter i { display: block; height: 100%; border-radius: 999px; background: var(--primary); transition: width .3s ease; }
.meter.full i { background: var(--emerald); }
.docp-foot { margin-top: 9px; font-size: 10.5px; color: var(--muted-fg); display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.src-pill { font-size: 9px; letter-spacing: .1em; border-radius: 999px; padding: 2px 8px; margin-left: 7px; vertical-align: 1px; }
.src-pill.up { background: var(--emerald-bg); color: #0b7d59; border: 1px solid #bfe8d4; }
.src-pill.ok { background: var(--emerald); color: #fff; }
.src-pill.au { background: #faf3df; color: var(--accent-deep); border: 1px solid var(--accent); }
.rail-note { font-size: 10.5px; color: var(--muted-fg); text-align: center; padding: 10px; }
.error-strip { background: #fbeeea; border: 1px solid var(--destructive); color: var(--destructive); border-radius: 8px; padding: 10px 14px; font-size: 11.5px; }
</style>

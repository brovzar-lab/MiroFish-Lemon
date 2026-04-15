<template>
  <div class="projects-view">
    <header class="projects-header">
      <div class="brand" @click="router.push('/')">MIROFISH</div>
      <h1 class="page-title">Project History</h1>
      <button class="new-project-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        New Project
      </button>
    </header>

    <main class="projects-main">
      <!-- Loading -->
      <div v-if="loading" class="state-center">
        <div class="spinner"></div>
        <span>Loading projects...</span>
      </div>

      <!-- Empty -->
      <div v-else-if="projects.length === 0" class="state-center">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="#CCC" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
        <p>No projects yet. <span class="link" @click="router.push('/')">Start your first analysis →</span></p>
      </div>

      <!-- Project Grid -->
      <div v-else class="project-grid">
        <div
          v-for="proj in projects"
          :key="proj.project_id"
          class="project-card"
          @click="openProject(proj)"
        >
          <div class="card-header">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"></path>
              </svg>
            </div>
            <div class="card-badges">
              <span class="badge" :class="`badge--${getReportBadgeClass(proj)}`">
                {{ getReportBadgeLabel(proj) }}
              </span>
            </div>
          </div>

          <div class="card-body">
            <h2 class="card-title">{{ proj.project_name || proj.project_id }}</h2>
            <p class="card-req">{{ proj.simulation_requirement }}</p>
          </div>

          <div class="card-footer">
            <span class="card-date">{{ formatDate(proj.created_at) }}</span>
            <div class="card-actions">
              <button
                v-if="proj._report && proj._report.status === 'completed'"
                class="action-link"
                @click.stop="openReport(proj._report.report_id)"
              >View Report →</button>
              <button
                v-else-if="proj._report && proj._report.status === 'failed'"
                class="action-link action-link--warn"
                @click.stop="openReport(proj._report.report_id)"
              >Resume →</button>
              <button
                v-else-if="proj._simulation"
                class="action-link"
                @click.stop="openSimulation(proj._simulation.simulation_id)"
              >Open →</button>
              <button
                v-else
                class="action-link"
                @click.stop="openProcess(proj)"
              >Continue →</button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import service from '../api/index'

const router = useRouter()
const projects = ref([])
const loading = ref(true)

const loadProjects = async () => {
  try {
    loading.value = true
    // Load all projects
    const projRes = await service.get('/api/graph/projects')
    if (!projRes.success) return
    const rawProjects = projRes.data || []

    // Enrich with simulation + report data (parallel per project)
    const enriched = await Promise.all(rawProjects.map(async (proj) => {
      try {
        const simRes = await service.get('/api/simulation/list', { params: { project_id: proj.project_id, limit: 1 } })
        const sim = simRes.success && simRes.data?.length ? simRes.data[0] : null
        proj._simulation = sim

        if (sim) {
          const reportRes = await service.get(`/api/report/by-simulation/${sim.simulation_id}`)
          proj._report = reportRes.success ? reportRes.data : null
        } else {
          proj._report = null
        }
      } catch {
        proj._simulation = null
        proj._report = null
      }
      return proj
    }))

    projects.value = enriched.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  } catch (err) {
    console.error('Failed to load projects:', err)
  } finally {
    loading.value = false
  }
}

const getReportBadgeClass = (proj) => {
  if (!proj._simulation) return 'pending'
  if (!proj._report) return 'sim'
  if (proj._report.status === 'completed') return 'done'
  if (proj._report.status === 'failed') return 'error'
  return 'generating'
}

const getReportBadgeLabel = (proj) => {
  if (!proj._simulation) return 'Graph Only'
  if (!proj._report) return 'Simulated'
  if (proj._report.status === 'completed') return 'Report Ready'
  if (proj._report.status === 'failed') return 'Paused'
  return 'Generating'
}

const formatDate = (isoStr) => {
  if (!isoStr) return '—'
  try {
    return new Date(isoStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch { return isoStr }
}

const openProject = (proj) => {
  if (proj._report) {
    router.push({ name: 'Report', params: { reportId: proj._report.report_id } })
  } else if (proj._simulation) {
    router.push({ name: 'Simulation', params: { simulationId: proj._simulation.simulation_id } })
  } else {
    router.push({ name: 'Process', params: { projectId: proj.project_id } })
  }
}

const openReport = (id) => router.push({ name: 'Report', params: { reportId: id } })
const openSimulation = (id) => router.push({ name: 'Simulation', params: { simulationId: id } })
const openProcess = (proj) => router.push({ name: 'Process', params: { projectId: proj.project_id } })

onMounted(loadProjects)
</script>

<style scoped>
.projects-view {
  min-height: 100vh;
  background: #FAFAFA;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

/* Header */
.projects-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 32px;
  height: 60px;
  background: #FFF;
  border-bottom: 1px solid #EAEAEA;
  position: sticky;
  top: 0;
  z-index: 10;
}

.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 1px;
  cursor: pointer;
  color: #000;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #111;
  margin: 0;
  flex: 1;
}

.new-project-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  background: #111;
  color: #FFF;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.new-project-btn:hover { background: #333; }

/* Main */
.projects-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px;
}

/* States */
.state-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 0;
  color: #999;
  font-size: 14px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid #E5E7EB;
  border-top-color: #111;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.link { color: #111; font-weight: 600; cursor: pointer; text-decoration: underline; }

/* Grid */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

/* Card */
.project-card {
  background: #FFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-card:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  border-color: #D1D5DB;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-icon {
  width: 36px;
  height: 36px;
  background: #F3F4F6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
}

/* Badges */
.badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}
.badge--done    { background: #D1FAE5; color: #065F46; }
.badge--error   { background: #FEE2E2; color: #991B1B; }
.badge--generating { background: #DBEAFE; color: #1E40AF; }
.badge--sim     { background: #EDE9FE; color: #5B21B6; }
.badge--pending { background: #F3F4F6; color: #6B7280; }

/* Card body */
.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #111;
  margin: 0;
  line-height: 1.3;
}

.card-req {
  font-size: 12px;
  color: #6B7280;
  margin: 4px 0 0 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Footer */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid #F3F4F6;
}

.card-date { font-size: 11px; color: #9CA3AF; font-family: 'JetBrains Mono', monospace; }

.action-link {
  font-size: 12px;
  font-weight: 600;
  color: #111;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}

.action-link:hover { color: #374151; }
.action-link--warn { color: #D97706; }
.action-link--warn:hover { color: #B45309; }
</style>

import { createRouter, createWebHistory } from 'vue-router'

// Existing views
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'

// Pipeline views
import PipelineDashboard from '../views/PipelineDashboard.vue'
import PrepView from '../views/PrepView.vue'
import LaunchConfirmView from '../views/LaunchConfirmView.vue'
import SocialView from '../views/SocialView.vue'

const routes = [
  // ── Pipeline Dashboard (new home) ──────────────────────
  {
    path: '/',
    name: 'Dashboard',
    component: PipelineDashboard
  },

  // ── Project pipeline routes ────────────────────────────
  {
    path: '/project/:slug/prepare',
    name: 'Prepare',
    component: PrepView,
    props: true
  },
  {
    path: '/project/:slug/launch',
    name: 'Launch',
    component: LaunchConfirmView,
    props: true
  },
  {
    path: '/project/:slug/interact',
    name: 'Interact',
    component: SocialView,
    props: true
  },

  // ── Legacy MiroFish routes (simulation engine) ─────────
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  },

  // ── Backwards compat redirect ──────────────────────────
  {
    path: '/prep',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

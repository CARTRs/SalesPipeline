import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import MainLayout from '../layouts/MainLayout.vue'
import OpportunityList from '../views/OpportunityList.vue'
import OpportunityDetail from '../views/OpportunityDetail.vue'
import OpportunityForm from '../views/OpportunityForm.vue'
import Dashboard from '../views/Dashboard.vue'
import Settings from '../views/Settings.vue'
import OperationLogs from '../views/OperationLogs.vue'
import PublicDashboard from '../views/PublicDashboard.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login, meta: { noAuth: true } },
  { path: '/public-dashboard/:user_key', name: 'PublicDashboard', component: PublicDashboard, meta: { noAuth: true } },
  {
    path: '/',
    component: MainLayout,
    redirect: '/opportunities',
    children: [
      { path: 'opportunities', name: 'OpportunityList', component: OpportunityList },
      { path: 'opportunities/create', name: 'OpportunityCreate', component: OpportunityForm },
      { path: 'opportunities/:id/edit', name: 'OpportunityEdit', component: OpportunityForm },
      { path: 'opportunities/:id', name: 'OpportunityDetail', component: OpportunityDetail },
      { path: 'dashboard', name: 'Dashboard', component: Dashboard, meta: { fullscreen: true } },
      { path: 'settings', name: 'Settings', component: Settings },
      { path: 'logs', name: 'OperationLogs', component: OperationLogs },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.noAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router

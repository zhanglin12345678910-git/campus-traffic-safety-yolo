import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from './components/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: () => import('./pages/DashboardPage.vue'), meta: { title: '态势总览' } },
        { path: 'inspection/new', component: () => import('./pages/NewInspectionPage.vue'), meta: { title: '新建智能巡检' } },
        { path: 'inspection/:id', component: () => import('./pages/InspectionDetailPage.vue'), meta: { title: '巡检详情' } },
        { path: 'inspections', component: () => import('./pages/InspectionsPage.vue'), meta: { title: '巡检档案' } },
        { path: 'reviews', component: () => import('./pages/ReviewsPage.vue'), meta: { title: '人工复核' } },
        { path: 'analytics', component: () => import('./pages/AnalyticsPage.vue'), meta: { title: '数据分析' } },
        { path: 'knowledge', component: () => import('./pages/KnowledgePage.vue'), meta: { title: '安全知识库' } },
        { path: 'settings', component: () => import('./pages/SettingsPage.vue'), meta: { title: '系统设置' } },
      ],
    },
  ],
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title || '管理平台')} · 安巡智脑`
})

export default router

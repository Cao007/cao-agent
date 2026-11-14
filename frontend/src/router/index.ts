import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/login', component: () => import('../views/auth/index.vue') },
    { path: '/', redirect: '/support' },
    { path: '/support', component: () => import('../views/customer-service/index.vue') },
    { path: '/operations', component: () => import('../views/customer-service/operations/index.vue') },
    { path: '/chat', component: () => import('../views/chat/index.vue') },
    { path: '/analysis', component: () => import('../views/document-analysis/index.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/support' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  try {
    if (!auth.isLoaded) await auth.load()
  } catch {
    // 后端恢复后登录页仍可重新尝试；不把网络失败当作已认证。
    if (to.path !== '/login') return '/login'
  }
  if (!auth.user && to.path !== '/login') return '/login'
  if (auth.user && to.path === '/login') return '/support'
})

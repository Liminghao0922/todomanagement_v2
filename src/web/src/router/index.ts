import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/pages/TodosPage.vue'),
    meta: { title: 'Todos', requiresAuth: true },
  },
  {
    path: '/projects',
    component: () => import('@/pages/ProjectsPage.vue'),
    meta: { title: 'Projects', requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 认证路由守卫
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || 'Page'} | Todo Management`
  
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth as boolean
  
  // 如果路由需要认证但用户未登录，则显示提示
  if (requiresAuth && !authStore.isAuthenticated) {
    // 显示登录提示，但不跳转
    console.warn('Please login first to access this page')
  }
  
  next()
})

export default router

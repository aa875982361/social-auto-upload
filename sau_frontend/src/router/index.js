import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import Dashboard from '../views/Dashboard.vue'
import AccountManagement from '../views/AccountManagement.vue'
import MaterialManagement from '../views/MaterialManagement.vue'
import PublishCenter from '../views/PublishCenter.vue'
import About from '../views/About.vue'
import Login from '../views/Login.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/account-management',
    name: 'AccountManagement',
    component: AccountManagement,
    meta: { requiresAuth: true }
  },
  {
    path: '/material-management',
    name: 'MaterialManagement',
    component: MaterialManagement,
    meta: { requiresAuth: true }
  },
  {
    path: '/publish-center',
    name: 'PublishCenter',
    component: PublishCenter,
    meta: { requiresAuth: true }
  },
  {
    path: '/about',
    name: 'About',
    component: About,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  // 如果路由需要认证
  if (to.meta.requiresAuth !== false) {
    if (!userStore.isLoggedIn) {
      // 未登录，跳转到登录页
      next('/login')
      return
    }
    
    // 如果已登录但用户信息为空，尝试获取用户信息
    if (!userStore.user) {
      userStore.fetchUserInfo().catch(() => {
        // 获取用户信息失败，跳转到登录页
        next('/login')
        return
      })
    }
  }
  
  // 如果已登录且访问登录页，跳转到首页
  if (to.name === 'Login' && userStore.isLoggedIn) {
    next('/')
    return
  }
  
  next()
})

export default router
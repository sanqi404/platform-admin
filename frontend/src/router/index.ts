import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { APP_BRAND } from '@/config/app'
import type { MenuNode } from '@/types'

const Layout = () => import('@/components/AppLayout.vue')

/**
 * 动态路由：页面文件全部由 src/views 自动扫描，路由表由后端菜单驱动。
 * 新增一个页面 = 建 src/views/<component>/index.vue + 菜单表填 component，无需改本文件。
 */
const viewMap = import.meta.glob('/src/views/**/*.vue')

function resolveView(component: string) {
  const clean = component.replace(/^\/+/, '').replace(/\.vue$/, '')
  return viewMap[`/src/views/${clean}.vue`] || viewMap[`/src/views/${clean}/index.vue`]
}

/**
 * 静态路由：登录、布局壳、错误页。
 * 业务页面一律通过 registerMenuRoutes 按菜单注册。
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    name: 'Layout',
    component: Layout,
    redirect: APP_BRAND.homePath,
    children: [
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/index.vue'),
        meta: { title: '个人中心' },
      },
    ],
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/403.vue'),
    meta: { title: '无访问权限', public: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '页面不存在', public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

/** 已注册的动态路由名，登出或切换账号时统一摘除，避免残留 */
let dynamicNames: string[] = []
let dynamicReady = false

function buildRoutes(menus: MenuNode[]): RouteRecordRaw[] {
  const out: RouteRecordRaw[] = []
  const walk = (list: MenuNode[]) => {
    for (const m of list) {
      const isPage = m.type === 'menu' && m.path && m.component
      if (isPage) {
        const comp = resolveView(m.component)
        if (comp) {
          out.push({
            path: m.path,
            name: m.name || `Menu${m.id}`,
            component: comp,
            meta: { title: m.title, perm: m.perm_code || undefined },
          })
        }
      }
      if (m.children && m.children.length) walk(m.children)
    }
  }
  walk(menus)
  return out
}

export function resetDynamicRoutes(): void {
  dynamicNames.forEach((name) => {
    if (router.hasRoute(name)) router.removeRoute(name)
  })
  dynamicNames = []
  dynamicReady = false
}

/**
 * 预热菜单页面组件：注册路由后立刻并发拉取各页 chunk。
 * 否则首次切换到某菜单时要等懒加载完成，router-view 区域会空白一闪。
 */
function prefetchViews(menus: MenuNode[]): void {
  const loaders = new Set<() => Promise<unknown>>()
  const walk = (list: MenuNode[]) => {
    for (const m of list) {
      if (m.type === 'menu' && m.component) {
        const loader = resolveView(m.component)
        if (loader) loaders.add(loader as () => Promise<unknown>)
      }
      if (m.children && m.children.length) walk(m.children)
    }
  }
  walk(menus)
  // fire-and-forget：不阻塞导航，失败也不影响路由可用性
  loaders.forEach((load) => {
    void load().catch(() => {})
  })
}

/** 按当前账号可见菜单注册路由；重复调用安全 */
export function registerMenuRoutes(menus: MenuNode[]): void {
  for (const r of buildRoutes(menus)) {
    const name = r.name as string
    if (router.hasRoute(name)) continue
    router.addRoute('Layout', r)
    dynamicNames.push(name)
  }
  prefetchViews(menus)
}

router.beforeEach(async (to) => {
  const user = useUserStore()

  document.title = to.meta.title ? `${to.meta.title} · ${APP_BRAND.title}` : APP_BRAND.title

  if (!user.isLogin) {
    resetDynamicRoutes()
    // 只放行登录页与无权限页。404 兜底路由虽然是 public，但未登录时
    // 访问未注册路径（如 /dashboard）会先匹配到它，若按 meta.public 放行
    // 就会停在 404、永远进不了登录页；因此这里用路由名白名单。
    if (to.name === 'Login' || to.name === 'Forbidden') return true
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 登录后（含刷新页面）先建好动态路由，再重走一次匹配
  if (!dynamicReady) {
    if (!user.loaded) {
      try {
        await user.fetchProfile()
      } catch {
        user.clear()
        resetDynamicRoutes()
        return { path: '/login', query: { redirect: to.fullPath } }
      }
    }
    resetDynamicRoutes()
    registerMenuRoutes(user.menus)
    dynamicReady = true
    return { path: to.path, query: to.query, hash: to.hash, replace: true }
  }

  if (to.path === '/login') return { path: APP_BRAND.homePath }

  const perm = to.meta.perm as string | undefined
  if (perm && !user.hasPerm(perm)) {
    return { path: '/403', query: { from: to.fullPath, perm } }
  }
  return true
})

export default router
